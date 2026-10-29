from collections import Counter
import pandas as pd
import networkx as nx

def transaction_analysis_agent(df):
    findings = []
    evidence = []
    inbound = df.groupby("destination_account")["amount"].agg(["sum", "count"])
    for account, row in inbound.iterrows():
        incoming = df[df.destination_account == account].copy()
        incoming["timestamp"] = pd.to_datetime(incoming["timestamp"])
        if len(incoming) >= 3:
            span = (incoming.timestamp.max() - incoming.timestamp.min()).total_seconds() / 60
            if span <= 60 and row["sum"] >= 300000:
                ids = incoming.transaction_id.astype(str).tolist()
                findings.append({
                    "agent": "Transaction Analysis Agent",
                    "type": "Observed pattern",
                    "finding": f"{int(row['count'])} incoming transfers totaling {row['sum']:,.0f} to {account} within {span:.0f} minutes.",
                    "interpretation": "Short-window inbound concentration may merit review.",
                    "evidence_ids": ids,
                    "severity": "High"
                })
                evidence.extend(ids)
    # Rapid pass-through: outgoing transfer soon after inbound funds.
    for _, out in df.iterrows():
        out_time = pd.to_datetime(out.timestamp)
        prior = df[(df.destination_account == out.source_account)].copy()
        if prior.empty:
            continue
        prior["timestamp"] = pd.to_datetime(prior["timestamp"])
        prior = prior[(prior.timestamp <= out_time) & ((out_time - prior.timestamp).dt.total_seconds() <= 60*60)]
        if not prior.empty:
            incoming_total = prior.amount.sum()
            if out.amount >= 0.70 * incoming_total and out.amount >= 100000:
                ids = prior.transaction_id.astype(str).tolist() + [str(out.transaction_id)]
                findings.append({
                    "agent": "Transaction Analysis Agent",
                    "type": "Observed pattern",
                    "finding": f"{out.source_account} sent {out.amount:,.0f} to {out.destination_account} within 60 minutes of linked incoming funds totaling {incoming_total:,.0f}.",
                    "interpretation": "Rapid movement may be consistent with pass-through activity; legitimate explanations are possible.",
                    "evidence_ids": ids,
                    "severity": "High"
                })
                evidence.extend(ids)
    # Deduplicate similar findings while preserving order.
    seen, unique = set(), []
    for f in findings:
        key = (f["finding"], tuple(f["evidence_ids"]))
        if key not in seen:
            seen.add(key); unique.append(f)
    return {"agent": "Transaction Analysis Agent", "status": "complete",
            "findings": unique, "evidence_ids": sorted(set(evidence))}

def network_investigation_agent(df):
    graph = nx.DiGraph()
    for _, r in df.iterrows():
        graph.add_edge(str(r.source_account), str(r.destination_account),
                       transaction_id=str(r.transaction_id), amount=float(r.amount),
                       timestamp=str(r.timestamp))
    findings = []
    # Detect a short path of two or more edges in the observed graph.
    nodes = list(graph.nodes)
    paths = []
    for source in nodes:
        for target in nodes:
            if source != target:
                try:
                    p = nx.shortest_path(graph, source, target)
                    if len(p) >= 3:
                        paths.append(p)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass
    if paths:
        # Pick the longest short path for a concise demo narrative.
        path = max(paths, key=len)
        path_edges = list(zip(path[:-1], path[1:]))
        txids = [graph[u][v]["transaction_id"] for u, v in path_edges]
        findings.append({
            "agent": "Network Investigation Agent",
            "type": "Network observation",
            "finding": "Connected transfer path: " + " → ".join(path),
            "interpretation": "A connected path helps trace movement; connectivity alone is not evidence of wrongdoing.",
            "evidence_ids": txids,
            "severity": "Medium"
        })
    degrees = dict(graph.degree())
    if degrees:
        hub = max(degrees, key=degrees.get)
        if degrees[hub] >= 3:
            txids = [str(r.transaction_id) for _, r in df.iterrows()
                     if str(r.source_account) == hub or str(r.destination_account) == hub]
            findings.append({
                "agent": "Network Investigation Agent",
                "type": "Network observation",
                "finding": f"{hub} is a connection hub with degree {degrees[hub]} in this dataset.",
                "interpretation": "A hub can be a normal business or collection account; validate expected behavior.",
                "evidence_ids": txids,
                "severity": "Medium"
            })
    return {"agent": "Network Investigation Agent", "status": "complete",
            "findings": findings, "graph": graph,
            "evidence_ids": sorted({x for f in findings for x in f["evidence_ids"]})}

def evidence_correlation_agent(df, transaction_result, network_result):
    valid_ids = set(df.transaction_id.astype(str))
    all_findings = transaction_result["findings"] + network_result["findings"]
    correlated = []
    for f in all_findings:
        linked = [x for x in f.get("evidence_ids", []) if x in valid_ids]
        correlated.append({**f, "evidence_ids": linked,
                           "evidence_valid": bool(linked) and len(linked) == len(f.get("evidence_ids", []))})
    missing = []
    if "customer_id" not in df.columns or df["customer_id"].isna().all():
        missing.append("Customer due-diligence/profile context is not present.")
    missing.extend([
        "Payment purpose and expected account activity are not available in this demo dataset.",
        "Source-of-funds documentation and customer relationships have not been verified."
    ])
    return {"agent": "Evidence Correlation Agent", "status": "complete",
            "findings": correlated, "evidence_ids": sorted({x for f in correlated for x in f["evidence_ids"]}),
            "missing_context": missing,
            "facts_vs_hypotheses": {
                "observed_facts": ["Amounts, timestamps, source/destination accounts and transaction IDs in the uploaded dataset."],
                "hypotheses": ["Rapid consolidation or pass-through activity may warrant investigation; this is not a conclusion of misconduct."]
            }}

def report_generation_agent(case_id, df, correlation_result, score, triggered_rules):
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    timeline = df.sort_values("timestamp")
    evidence = correlation_result["evidence_ids"]
    evidence_rows = timeline[timeline.transaction_id.astype(str).isin(evidence)]
    lines = [
        f"# FinPro AI Investigation Draft — {case_id}",
        "",
        f"**Triage priority:** {'High' if score >= 60 else 'Medium' if score >= 30 else 'Low'} (illustrative score {score}/100)",
        "",
        "## Alert rationale",
        "The rule engine identified the following review triggers:",
    ]
    lines += [f"- {rule}" for rule in triggered_rules] if triggered_rules else ["- No configured threshold rule triggered."]
    lines += ["", "## Observed evidence", f"- {len(evidence_rows)} transaction rows are linked to agent findings."]
    for _, r in evidence_rows.sort_values("timestamp").iterrows():
        lines.append(f"- `{r.transaction_id}`: {r.source_account} → {r.destination_account}, {r.amount:,.0f} {r.currency}, {r.timestamp.strftime('%Y-%m-%d %H:%M')}.")
    lines += [
        "", "## Interpretation and uncertainty",
        "The observed sequence may be consistent with rapid consolidation or pass-through movement. This is a hypothesis for review, not proof of fraud or money laundering.",
        "", "## Alternative explanations",
        "- Legitimate pooled payments, business settlement, family transfers, or expected account activity.",
        "- A known collection/disbursement account or other documented operational reason.",
        "", "## Missing context",
    ]
    lines += [f"- {x}" for x in correlation_result["missing_context"]]
    lines += [
        "", "## Recommended human-review steps",
        "1. Compare the pattern with the customer's expected activity and historical baseline.",
        "2. Verify payment purpose, source of funds, beneficiaries, and account relationships.",
        "3. Check relevant customer due-diligence records and internal policy.",
        "4. Document rationale and decide whether further investigation is warranted.",
        "", "**Governance note:** Synthetic-data demo only. An authorized human must make all case decisions. This draft is not a regulatory filing."
    ]
    return "\n".join(lines)
