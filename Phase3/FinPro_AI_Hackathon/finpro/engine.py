import pandas as pd
from finpro.agents import (transaction_analysis_agent, network_investigation_agent,
                             evidence_correlation_agent, report_generation_agent)

REQUIRED = ["transaction_id", "timestamp", "source_account", "destination_account", "amount", "currency"]

def validate_transactions(df):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    out = df.copy()
    out["transaction_id"] = out["transaction_id"].astype(str)
    if out["transaction_id"].duplicated().any():
        raise ValueError("transaction_id values must be unique.")
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    if out["timestamp"].isna().any():
        raise ValueError("One or more timestamps could not be parsed.")
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")
    if out["amount"].isna().any() or (out["amount"] <= 0).any():
        raise ValueError("Amounts must be numeric and greater than zero.")
    for c in ["source_account", "destination_account", "currency"]:
        out[c] = out[c].astype(str)
    return out

def detect_alerts(df):
    """Demo heuristics, NOT regulatory thresholds or calibrated fraud probabilities."""
    import networkx as nx
    from itertools import combinations
    rules, hits = [], []
    score = 0
    df = df.sort_values("timestamp").copy()

    def add(code, description, points, ids):
        nonlocal score
        ids = list(dict.fromkeys(str(x) for x in ids))
        if not ids:
            return
        rules.append(f"{code} — {description}")
        hits.append({"rule_id": code, "description": description,
                     "points": points, "evidence_ids": ids})
        score += points

    # R1: windowed inbound concentration (not lifetime total).
    for account, incoming in df.groupby("destination_account"):
        incoming = incoming.sort_values("timestamp")
        for _, endrow in incoming.iterrows():
            window = incoming[(incoming.timestamp >= endrow.timestamp - pd.Timedelta(minutes=60)) &
                              (incoming.timestamp <= endrow.timestamp)]
            if len(window) >= 3 and window.amount.sum() >= 300000:
                add("R1", f"inbound concentration to {account}: {len(window)} transfers totaling {window.amount.sum():,.0f} within 60 minutes", 40, window.transaction_id)
                break

    # R2: single rapid outgoing transfer relative to prior inbound funds.
    for _, out in df.iterrows():
        prior = df[(df.destination_account == out.source_account) &
                   (df.timestamp <= out.timestamp) &
                   (df.timestamp >= out.timestamp - pd.Timedelta(minutes=60))]
        if len(prior) and out.amount >= 100000 and out.amount >= .70 * prior.amount.sum():
            add("R2", f"rapid outflow from {out.source_account}: {out.amount:,.0f} after incoming {prior.amount.sum():,.0f}", 35,
                list(prior.transaction_id) + [out.transaction_id])
            break

    # R3: rapid payment velocity: >= 5 distinct payments in 10 minutes.
    for account, outgoing in df.groupby("source_account"):
        outgoing = outgoing.sort_values("timestamp")
        for _, endrow in outgoing.iterrows():
            window = outgoing[(outgoing.timestamp >= endrow.timestamp - pd.Timedelta(minutes=10)) &
                              (outgoing.timestamp <= endrow.timestamp)]
            if len(window) >= 5 and window.destination_account.nunique() >= 3:
                add("R3", f"outbound velocity from {account}: {len(window)} transfers to {window.destination_account.nunique()} recipients in 10 minutes", 20, window.transaction_id)
                break

    # R4: time-ordered A -> B -> C -> A, without repeating a transaction.
    for _, a in df.iterrows():
        for _, b in df[(df.source_account == a.destination_account) &
                       (df.timestamp >= a.timestamp) &
                       (df.timestamp <= a.timestamp + pd.Timedelta(hours=24))].iterrows():
            if b.destination_account == a.source_account:
                continue
            cands = df[(df.source_account == b.destination_account) &
                       (df.destination_account == a.source_account) &
                       (df.timestamp >= b.timestamp) &
                       (df.timestamp <= a.timestamp + pd.Timedelta(hours=24))]
            for _, c in cands.iterrows():
                if len({a.transaction_id,b.transaction_id,c.transaction_id}) == 3:
                    add("R4", f"circular flow observed: {a.source_account} → {a.destination_account} → {b.destination_account} → {a.source_account} within 24 hours", 25,
                        [a.transaction_id,b.transaction_id,c.transaction_id])
                    break
            if any(h["rule_id"] == "R4" for h in hits):
                break
        if any(h["rule_id"] == "R4" for h in hits):
            break

    # R5: near an explicitly configured INTERNAL monitoring threshold.
    # Do not interpret as a legal CTR/SAR threshold.
    threshold = 100000
    for account, outgoing in df.groupby("source_account"):
        outgoing = outgoing.sort_values("timestamp")
        for _, endrow in outgoing.iterrows():
            window = outgoing[(outgoing.timestamp >= endrow.timestamp - pd.Timedelta(hours=24)) &
                              (outgoing.timestamp <= endrow.timestamp)]
            near = window[(window.amount >= .90 * threshold) & (window.amount < threshold)]
            if len(near) >= 3:
                add("R5", f"repeated payments just below illustrative internal threshold {threshold:,.0f} from {account}: {len(near)} transfers in 24 hours", 20, near.transaction_id)
                break

    # R6: new-beneficiary high-value transfer (requires explicit enrichment).
    if "is_new_beneficiary" in df.columns:
        new = df["is_new_beneficiary"].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
        matching = df[new & (df.amount >= 150000)]
        if len(matching):
            r = matching.iloc[0]
            add("R6", f"high-value transfer to explicitly flagged new beneficiary: {r.source_account} → {r.destination_account}, {r.amount:,.0f}", 15, [r.transaction_id])

    return {"score": min(score, 100), "triggered_rules": rules, "rule_hits": hits,
            "priority": "High" if score >= 60 else "Medium" if score >= 30 else "Low"}

def run_investigation(raw_df, case_id="CASE-DEMO-001"):
    df = validate_transactions(raw_df)
    alert = detect_alerts(df)
    tx = transaction_analysis_agent(df)
    network = network_investigation_agent(df)
    evidence = evidence_correlation_agent(df, tx, network)
    for hit in alert.get("rule_hits", []):
        evidence["findings"].append({
            "agent": "Triage Rule Engine", "type": "Rule trigger",
            "finding": hit["description"], "interpretation": "Monitoring signal only.",
            "evidence_ids": hit["evidence_ids"], "evidence_valid": True,
            "severity": "High" if hit["points"] >= 30 else "Medium",
            "rule_id": hit["rule_id"]
        })
    evidence["evidence_ids"] = sorted(set(evidence["evidence_ids"]) |
                                      {x for hit in alert.get("rule_hits", []) for x in hit["evidence_ids"]})
    # Evidence integrity check: all referenced IDs must exist in source data.
    valid = set(df.transaction_id.astype(str))
    for finding in evidence["findings"]:
        if not all(x in valid for x in finding["evidence_ids"]):
            raise ValueError("Evidence validation failed: finding references unknown transaction IDs.")
    report = report_generation_agent(case_id, df, evidence, alert["score"], alert["triggered_rules"])
    return {"case_id": case_id, "transactions": df, "alert": alert,
            "transaction_agent": tx, "network_agent": network,
            "evidence_agent": evidence, "report": report}
