# FinGuard AI — Multi-Agent Fraud & AML Investigation Copilot

A runnable hackathon MVP based on the supplied FinGuard AI proposal. It uses synthetic transactions, transparent rules, four specialized agent modules, a shared case state, evidence references, a transaction network, a report draft, and a human review action.

> **Important:** This is a demonstration prototype, not a production AML system. It does not determine that a crime occurred, file a regulatory report, freeze accounts, or replace an authorized investigator. Use synthetic data only.

## Quick start

Python 3.10+ recommended.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. Choose **Load demo case** to use the bundled synthetic scenario, or upload a CSV.

## CSV schema

Required columns:

| Column | Meaning | Example |
|---|---|---|
| transaction_id | Unique transaction identifier | TXN-1001 |
| timestamp | ISO timestamp | 2026-10-20 09:00:00 |
| source_account | Sending account | A-101 |
| destination_account | Receiving account | A-201 |
| amount | Numeric amount, in one consistent currency | 120000 |
| currency | Currency code | INR |
| channel | Optional transfer channel | IMPS |
| customer_id | Optional customer identifier | C-101 |

Amounts must be positive. Timestamps must be parseable. The demo data is fictional and denominated in INR.

## How the agents work

1. **Transaction Analysis Agent** — evaluates short-window inbound concentration and rapid outflow rules.
2. **Network Investigation Agent** — constructs a directed account graph and identifies connected accounts and paths.
3. **Evidence Correlation Agent** — joins agent findings to transaction IDs and distinguishes observed facts from hypotheses and missing context.
4. **Report Generation Agent** — drafts a case narrative, timeline, evidence list, alternative explanations, and human-review next steps.
5. **Orchestrator** — runs the agents in order against shared case state and validates that evidence references exist.

The MVP is agentic in its task decomposition, shared state, specialized tools, and sequential hand-offs. The current implementation is deliberately deterministic so the demo is repeatable and needs no paid LLM API. It is **not** claiming autonomous LLM reasoning. A local model can be added later for wording only, while keeping calculations and evidence references deterministic.

## Demo flow (5 minutes)

1. Start app and click **Load demo case**.
2. Click **Run investigation**.
3. Show the alert score and exact rules that triggered.
4. Show agent outputs and account network.
5. Open evidence table and point to transaction IDs.
6. Review the report draft, alternative explanations, and recommended checks.
7. Choose **Escalate for human review**, **Approve draft**, or **Dismiss with reason**.
8. Download the report and/or CSV evidence.

## Project layout

- `app.py` — Streamlit investigator UI
- `finguard/engine.py` — data validation, alert rules, orchestration, evidence validation
- `finguard/agents.py` — specialized agents and report writer
- `finguard/demo_data.py` — predictable synthetic scenario
- `tests/test_engine.py` — basic tests

## Design choices and limitations

- Rules are illustrative thresholds, not a calibrated financial-institution policy.
- A high score means “prioritize for review,” not “confirmed fraud/AML.”
- No real customer data, account actions, external APIs, or regulatory filing.
- The SQLite-free MVP stores review state in Streamlit session state; for production, use authenticated persistent storage, audit logging, access controls, model governance, monitoring, and approved policy thresholds.
- For a live hackathon demo, test dependencies and run the app before presenting. Keep the sample CSV locally available as a fallback.
