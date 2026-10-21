import pandas as pd
from finguard.agents import (transaction_analysis_agent, network_investigation_agent,
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
    rules = []
    score = 0
    inbound = df.groupby("destination_account").agg(total=("amount", "sum"), count=("amount", "count"))
    for account, row in inbound.iterrows():
        incoming = df[df.destination_account == account]
        if len(incoming) >= 3 and row.total >= 300000:
            times = pd.to_datetime(incoming.timestamp)
            mins = (times.max() - times.min()).total_seconds()/60
            if mins <= 60:
                rules.append(f"R1 — inbound concentration: {int(row['count'])} transfers totaling {row.total:,.0f} to {account} in {mins:.0f} minutes")
                score += 40
    for _, out in df.iterrows():
        prior = df[(df.destination_account == out.source_account)].copy()
        prior["timestamp"] = pd.to_datetime(prior.timestamp)
        t = pd.to_datetime(out.timestamp)
        prior = prior[(prior.timestamp <= t) & ((t-prior.timestamp).dt.total_seconds() <= 3600)]
        if len(prior) and out.amount >= 100000 and out.amount >= .70*prior.amount.sum():
            rules.append(f"R2 — rapid outflow: {out.source_account} sent {out.amount:,.0f} shortly after incoming funds of {prior.amount.sum():,.0f}")
            score += 35
    score = min(score, 100)
    return {"score": score, "triggered_rules": list(dict.fromkeys(rules)),
            "priority": "High" if score >= 60 else "Medium" if score >= 30 else "Low"}

def run_investigation(raw_df, case_id="CASE-DEMO-001"):
    df = validate_transactions(raw_df)
    alert = detect_alerts(df)
    tx = transaction_analysis_agent(df)
    network = network_investigation_agent(df)
    evidence = evidence_correlation_agent(df, tx, network)
    # Evidence integrity check: all referenced IDs must exist in source data.
    valid = set(df.transaction_id.astype(str))
    for finding in evidence["findings"]:
        if not all(x in valid for x in finding["evidence_ids"]):
            raise ValueError("Evidence validation failed: finding references unknown transaction IDs.")
    report = report_generation_agent(case_id, df, evidence, alert["score"], alert["triggered_rules"])
    return {"case_id": case_id, "transactions": df, "alert": alert,
            "transaction_agent": tx, "network_agent": network,
            "evidence_agent": evidence, "report": report}
