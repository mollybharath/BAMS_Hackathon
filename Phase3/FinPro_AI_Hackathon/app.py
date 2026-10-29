import io
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from finpro.demo_data import demo_transactions
from finpro.engine import run_investigation

st.set_page_config(page_title="FinPro AI", page_icon="🛡️", layout="wide")
st.title("🛡️ FinPro AI")
st.caption("Multi-Agent Fraud & AML Investigation Copilot · Synthetic-data demonstration")
st.warning("Prototype only. Suspicious patterns are review signals, not proof of wrongdoing. Do not upload real customer data.")

if "raw_df" not in st.session_state:
    st.session_state.raw_df = demo_transactions()
if "result" not in st.session_state:
    st.session_state.result = None
if "review_status" not in st.session_state:
    st.session_state.review_status = "Not reviewed"
if "review_reason" not in st.session_state:
    st.session_state.review_reason = ""

with st.sidebar:
    st.header("Case controls")
    if st.button("Load demo case", use_container_width=True):
        st.session_state.raw_df = demo_transactions()
        st.session_state.result = None
        st.session_state.review_status = "Not reviewed"
        st.session_state.review_reason = ""
    upload = st.file_uploader("Upload transaction CSV", type=["csv"])
    if upload is not None:
        try:
            st.session_state.raw_df = pd.read_csv(upload)
            st.session_state.result = None
            st.success("CSV loaded. Run investigation to validate it.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
    st.caption("Required: transaction_id, timestamp, source_account, destination_account, amount, currency")
    if st.button("Run investigation", type="primary", use_container_width=True):
        try:
            st.session_state.result = run_investigation(st.session_state.raw_df)
            st.session_state.review_status = "Not reviewed"
            st.session_state.review_reason = ""
        except Exception as e:
            st.session_state.result = None
            st.error(str(e))

raw = st.session_state.raw_df
st.subheader("Transaction input")
st.dataframe(raw, use_container_width=True, hide_index=True)
st.caption(f"{len(raw)} rows loaded")

r = st.session_state.result
if r:
    alert = r["alert"]
    st.divider()
    st.subheader("Triage overview")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Triage score", f'{alert["score"]}/100')
    c2.metric("Priority", alert["priority"])
    c3.metric("Transactions", len(r["transactions"]))
    c4.metric("Linked evidence IDs", len(r["evidence_agent"]["evidence_ids"]))
    st.markdown("**Rules triggered**")
    if alert["triggered_rules"]:
        for rule in alert["triggered_rules"]: st.write("• " + rule)
    else:
        st.info("No configured threshold rules triggered.")
    st.divider()
    st.subheader("Agent collaboration")
    tabs = st.tabs(["1 · Transaction analysis", "2 · Network investigation", "3 · Evidence correlation", "4 · Report generation"])
    with tabs[0]:
        st.write("Checks transaction concentration and rapid movement using explicit, inspectable rules.")
        findings = r["transaction_agent"]["findings"]
        if findings:
            for f in findings:
                with st.expander(f'[{f["severity"]}] {f["finding"]}', expanded=True):
                    st.write(f["interpretation"])
                    st.write("Evidence IDs:", ", ".join(f["evidence_ids"]))
        else: st.info("No transaction-agent findings.")
    with tabs[1]:
        st.write("Creates a directed graph of source and destination accounts.")
        g = r["network_agent"]["graph"]
        if g.number_of_edges():
            fig, ax = plt.subplots(figsize=(10,5))
            pos = nx.spring_layout(g, seed=12)
            nx.draw_networkx(g, pos=pos, ax=ax, node_size=1800, font_size=9,
                             arrows=True, with_labels=True)
            edge_labels = {(u,v): f'{d["amount"]:,.0f}' for u,v,d in g.edges(data=True)}
            nx.draw_networkx_edge_labels(g, pos=pos, edge_labels=edge_labels, font_size=8, ax=ax)
            ax.axis("off")
            st.pyplot(fig, clear_figure=True)
        for f in r["network_agent"]["findings"]:
            st.write("• " + f["finding"])
            st.caption(f["interpretation"] + " Evidence: " + ", ".join(f["evidence_ids"]))
    with tabs[2]:
        st.write("Every agent claim is linked to transaction IDs; missing context is explicitly surfaced.")
        for f in r["evidence_agent"]["findings"]:
            icon = "✅" if f["evidence_valid"] else "⚠️"
            st.write(f'{icon} **{f["agent"]} — {f["type"]}:** {f["finding"]}')
            st.caption("Evidence IDs: " + (", ".join(f["evidence_ids"]) or "None"))
        st.markdown("**Missing context**")
        for item in r["evidence_agent"]["missing_context"]: st.write("• " + item)
        st.markdown("**Facts vs. hypotheses**")
        st.write("Observed facts:", "; ".join(r["evidence_agent"]["facts_vs_hypotheses"]["observed_facts"]))
        st.write("Hypotheses:", "; ".join(r["evidence_agent"]["facts_vs_hypotheses"]["hypotheses"]))
    with tabs[3]:
        st.markdown(r["report"])
        st.download_button("Download report (.md)", data=r["report"], file_name=f'{r["case_id"]}_report.md', mime="text/markdown")
        csv_bytes = r["transactions"].to_csv(index=False).encode("utf-8")
        st.download_button("Download validated transactions (.csv)", data=csv_bytes, file_name=f'{r["case_id"]}_transactions.csv', mime="text/csv")
    st.divider()
    st.subheader("Human review gate")
    st.write("The system drafts evidence and recommendations; the investigator retains the decision.")
    col1,col2 = st.columns(2)
    with col1:
        reason = st.text_input("Review note / dismissal reason", value=st.session_state.review_reason,
                               placeholder="e.g., Escalating for customer-profile review")
        st.session_state.review_reason = reason
    with col2:
        st.write("Current status:", f'**{st.session_state.review_status}**')
        st.write("Choose one action:")
    a,b,c = st.columns(3)
    if a.button("Escalate for human review", use_container_width=True):
        st.session_state.review_status = "Escalated for human review"
        st.session_state.review_reason = reason or "Escalated; add review rationale."
    if b.button("Approve draft", use_container_width=True):
        st.session_state.review_status = "Draft approved by demo reviewer"
        st.session_state.review_reason = reason or "Draft reviewed in hackathon demo."
    if c.button("Dismiss with reason", use_container_width=True):
        if reason.strip():
            st.session_state.review_status = "Dismissed by demo reviewer"
            st.session_state.review_reason = reason
        else:
            st.error("Enter a reason before dismissing.")
    st.info(f'Review status: {st.session_state.review_status} · Note: {st.session_state.review_reason or "No note"}')
else:
    st.info("Load the demo case and click **Run investigation** to start the multi-agent workflow.")

with st.expander("How this qualifies as an agentic workflow"):
    st.markdown("""
- **Task decomposition:** the orchestrator assigns separate analysis tasks to specialized agents.
- **Shared state:** agents consume the same validated transaction set and hand findings forward.
- **Tool use:** pandas rules and NetworkX graph analysis provide deterministic tools.
- **Handoffs:** transaction/network findings flow into evidence correlation, then report generation.
- **Guardrail:** the orchestrator validates that evidence IDs exist; a human review action is required.

This MVP is a transparent, deterministic multi-agent workflow. It does not use an LLM autonomously. An optional model can later improve narrative phrasing, but should not invent facts or control case outcomes.
""")
