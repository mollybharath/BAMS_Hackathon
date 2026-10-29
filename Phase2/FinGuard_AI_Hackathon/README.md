# FinGuard AI 2.0 — Local-first Agentic Fraud & AML Investigation Workspace

FinGuard is a hackathon prototype for evidence-led triage of synthetic financial transactions. This upgrade preserves the original Streamlit MVP and adds a **React + FastAPI investigation workspace** with a bounded planner, specialized tools, evidence critic, directed account network, context gaps, audit timeline, report draft, and explicit human review.

> **Safety / scope:** Synthetic data only. The score is illustrative and is not a calibrated risk model. A finding is not proof of fraud or money laundering. The prototype does not freeze accounts, file regulatory reports, or replace an authorized investigator. Do not upload real customer or financial data.

## What's new

- **Planner:** produces a short, bounded tool plan from the input shape and case signals.
- **Specialist agents:** transaction pattern analysis, account-network analysis, evidence correlation, and report drafting reuse the existing implementation.
- **Evidence Critic:** verifies transaction references and flags potentially overconfident claims.
- **Shared case state and audit timeline:** each tool/agent handoff has a sequence, timestamp, action, status, and summary.
- **React investigator UI:** triage metrics, agent timeline, findings with transaction IDs, network edge list, context gaps, alternatives, and human-review capture.
- **Local-only by default:** no remote LLM calls or API keys. The workflow is deterministic and reproducible. Optional Ollama integration can generate a cautious narrative summary using a model running on your machine; scoring, rules, evidence IDs, and validation remain deterministic.
- **CSV import + REST API:** validate and investigate a CSV through the UI or `/api/investigate/upload`.

## Run it locally

Requires Python 3.10+ and Node.js 18+.

### 1. Python API (terminal 1)

From this directory:

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

API health: http://localhost:8000/api/health  
Interactive API docs: http://localhost:8000/docs

### 2. React UI (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally http://localhost:5173). The frontend calls the local API at `http://localhost:8000`; override with `VITE_API_URL` if needed.

### Optional: enable a local LLM via Ollama

The application runs without a model. If Ollama is already installed and a model is pulled locally, set `FINGUARD_LOCAL_MODEL` to that model name before starting the API. Example in PowerShell:

```powershell
$env:FINGUARD_LOCAL_MODEL="llama3.2"
$env:FINGUARD_OLLAMA_URL="http://127.0.0.1:11434"
python -m uvicorn api.main:app --reload --port 8000
```

This adapter calls only the local Ollama endpoint. If it is unavailable, FinGuard retains the deterministic report. Do not expose the Ollama port publicly. The local model only writes an optional summary; it cannot change the risk score or evidence references.

### 3. Run tests

```bash
python -m pip install pytest
python -m pytest -q
```

### Legacy Streamlit app

The original MVP is preserved in `app.py`. To run it instead of React:

```bash
streamlit run app.py
```

## CSV schema

Required: `transaction_id`, `timestamp`, `source_account`, `destination_account`, `amount`, `currency`. Optional: `channel`, `customer_id`. Transaction IDs must be unique, timestamps parseable, and amounts positive. Use a consistent currency per case.

## Demo script (3 minutes)

1. Open the React app and point out **Local-first mode**.
2. Click **Run investigation**. Show the plan, specialist steps, evidence critic, and report generation.
3. Show the illustrative risk score and the exact rules that triggered.
4. Open findings and read transaction IDs; cross-check the network transfer list.
5. Point out missing customer context and plausible legitimate explanations.
6. Enter reviewer/rationale and record a human decision.
7. Explain that the score is triage support, not a fraud verdict; no external LLM or data-sharing is used.

## Architecture

```text
React UI (Vite) ──REST──> FastAPI
                              │
                     Input validation
                              │
                      Triage / rules
                              │
                    Bounded investigation plan
                              │
           ┌──────────────────┼─────────────────┐
           ▼                  ▼                 ▼
   Transaction tools    Network tools    Evidence correlation
           └──────────────────┼─────────────────┘
                              ▼
                  Evidence Critic / verifier
                              ▼
                  Report + context gaps
                              ▼
                    Human review capture
```

## Known limitations / honest positioning

- The default planner and specialist tools are deterministic Python logic. With the optional local Ollama adapter enabled, a local model may write a summary, but it does not control tool execution, risk scoring, or evidence integrity.
- Review decisions and cases are held in process memory; restarting the API clears them. Add SQLite/Postgres, authentication, and role-based access for a longer-lived demo.
- The sample uses simple illustrative rules, not institution-approved thresholds or a validated model.
- The account graph is shown as an auditable edge list in the UI; a visual graph can be a future polish item.
- Google Fonts may be requested by the browser for typography. No transaction data is sent to fonts or external model services. For fully air-gapped presentation, remove the `@import` from `frontend/src/styles.css`.
