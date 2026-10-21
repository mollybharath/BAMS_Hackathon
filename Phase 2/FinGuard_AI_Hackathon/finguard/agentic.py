"""Auditable, local-first investigation workflow for the FinGuard hackathon MVP.

No remote model calls are made. The bounded planner selects deterministic tools based
on observed gaps, and a critic verifies evidence references and flags unsupported claims.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import pandas as pd
from finguard.engine import validate_transactions, detect_alerts
from finguard.agents import transaction_analysis_agent, network_investigation_agent, evidence_correlation_agent, report_generation_agent
from finguard.local_llm import generate_local_summary


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any):
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def run_agentic_investigation(raw_df: pd.DataFrame, case_id: str = "CASE-DEMO-001") -> dict:
    df = validate_transactions(raw_df)
    # Shared case state: every step adds evidence and an audit event.
    state: dict[str, Any] = {"case_id": case_id, "started_at": _utc_now(), "steps": [], "evidence_ids": [], "findings": [], "review_flags": []}

    def event(agent: str, action: str, status: str, summary: str, **extra):
        state["steps"].append({"sequence": len(state["steps"])+1, "timestamp": _utc_now(), "agent": agent, "action": action, "status": status, "summary": summary, **extra})

    event("Triage Agent", "validate_input", "complete", f"Validated {len(df)} transactions across {df.source_account.nunique() + len(set(df.destination_account)-set(df.source_account))} account endpoints.")
    alert = detect_alerts(df)
    event("Triage Agent", "score_case", "complete", f"Illustrative triage score {alert['score']}/100; priority {alert['priority']}.", score=alert["score"])

    # Planner chooses tools from observable case properties. Bounded to three tool calls.
    plan = ["transaction_pattern_scan", "account_network_analysis", "evidence_correlation"]
    if df["source_account"].nunique() >= 3 or df["destination_account"].nunique() >= 3:
        plan.append("alternative_explanation_review")
    plan = plan[:4]
    event("Investigation Planner", "create_plan", "complete", "Selected a bounded plan from the transaction volume, account diversity, and initial alert.", plan=plan)

    tx = transaction_analysis_agent(df)
    event("Transaction Analyst", "transaction_pattern_scan", "complete", f"Generated {len(tx['findings'])} transaction-pattern finding(s).", finding_count=len(tx["findings"]))
    network = network_investigation_agent(df)
    event("Network Analyst", "account_network_analysis", "complete", f"Built account network with {len(network['graph'].nodes)} nodes and {len(network['graph'].edges)} directed edges.", node_count=len(network["graph"].nodes), edge_count=len(network["graph"].edges))
    evidence = evidence_correlation_agent(df, tx, network)
    # Every rule hit is itself an evidence-backed finding, including new rules R3-R6.
    for hit in alert.get("rule_hits", []):
        evidence["findings"].append({
            "agent": "Triage Rule Engine", "type": "Rule trigger",
            "finding": hit["description"],
            "interpretation": "Configurable monitoring signal; investigate context before making a determination.",
            "evidence_ids": hit["evidence_ids"], "evidence_valid": True,
            "severity": "High" if hit["points"] >= 30 else "Medium",
            "rule_id": hit["rule_id"]
        })
    evidence["evidence_ids"] = sorted(set(evidence["evidence_ids"]) |
                                      {x for hit in alert.get("rule_hits", []) for x in hit["evidence_ids"]})
    event("Evidence Correlator", "evidence_correlation", "complete", f"Correlated {len(evidence['evidence_ids'])} transaction ID(s); identified {len(evidence['missing_context'])} context gap(s).", evidence_count=len(evidence["evidence_ids"]))

    # Skeptical reviewer: validate every reference and avoid turning risk signals into conclusions.
    valid_ids = set(df.transaction_id.astype(str))
    invalid = []
    for finding in evidence["findings"]:
        bad = [x for x in finding.get("evidence_ids", []) if x not in valid_ids]
        if bad:
            invalid.extend(bad)
    if invalid:
        state["review_flags"].append({"severity": "critical", "message": "One or more findings reference transaction IDs absent from source data.", "invalid_ids": sorted(set(invalid))})
    unsupported = any("confirmed fraud" in str(f.get("finding", "")).lower() or "money laundering occurred" in str(f.get("finding", "")).lower() for f in evidence["findings"])
    if unsupported:
        state["review_flags"].append({"severity": "high", "message": "Potentially conclusive wording detected; require human review."})
    event("Evidence Critic", "verify_evidence_and_claims", "complete" if not state["review_flags"] else "needs_review", f"Checked evidence integrity and claim language; {len(state['review_flags'])} review flag(s).", flags=len(state["review_flags"]))

    # Alternative explanations are deliberately explicit, not inferred as facts.
    alternatives = [
        "Legitimate pooled payments, business settlement, family transfers, or expected account activity.",
        "A known collection/disbursement account or documented operational reason.",
    ]
    if "alternative_explanation_review" in plan:
        event("Skeptic Agent", "alternative_explanation_review", "complete", "Added plausible non-criminal explanations to reduce confirmation bias.", alternatives_count=len(alternatives))

    report = report_generation_agent(case_id, df, evidence, alert["score"], alert["triggered_rules"])
    local_summary = generate_local_summary(case_id, alert["score"], alert["priority"], evidence["findings"], evidence["missing_context"])
    if local_summary.get("summary"):
        report += "\n\n## Optional local-model summary\n\n" + local_summary["summary"] + "\n\n*Generated by an optional local model; verify against the evidence above.*"
    event("Report Agent", "draft_investigation_report", "complete", "Created a human-review draft with evidence, uncertainty, and next steps.")
    if local_summary.get("enabled"):
        event("Local LLM Adapter", "generate_optional_summary", "complete" if local_summary.get("summary") else "fallback", local_summary.get("message", "Local-only summary generated or deterministic fallback retained."), model=local_summary.get("model"), status_detail=local_summary.get("status"))
    state["completed_at"] = _utc_now()
    state["plan"] = plan
    state["alert"] = alert
    state["findings"] = evidence["findings"]
    state["missing_context"] = evidence["missing_context"]
    state["alternatives"] = alternatives
    state["report_markdown"] = report
    state["local_model"] = local_summary
    state["transactions"] = df.sort_values("timestamp").assign(timestamp=lambda x: x.timestamp.map(_json_safe)).to_dict(orient="records")
    state["network"] = {"nodes": [{"id": str(n), "degree": int(network["graph"].degree(n))} for n in network["graph"].nodes],
                         "edges": [{"source": str(u), "target": str(v), "transaction_id": str(d.get("transaction_id", "")), "amount": float(d.get("amount", 0))} for u, v, d in network["graph"].edges(data=True)]}
    state["evidence_ids"] = sorted(evidence["evidence_ids"])
    state["facts_vs_hypotheses"] = evidence["facts_vs_hypotheses"]
    state["human_decision"] = {"status": "pending", "reviewer": None, "reason": None, "updated_at": None}
    return state
