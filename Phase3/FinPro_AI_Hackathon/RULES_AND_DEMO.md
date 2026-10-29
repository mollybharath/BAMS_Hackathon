# FinPro AI 2.1 — Additional monitoring rules

The rule engine is **batch analysis of uploaded CSV data**, not a streaming real-time monitoring system. Each new CSV can be investigated immediately through the existing React interface and FastAPI upload endpoint. This is a synthetic demonstration and **not production AML policy**.

| Rule | Trigger | Demo score |
|---|---|---|
| R1 | >=3 inbound transfers totalling >=300,000 INR within a rolling 60-minute window | +40 |
| R2 | >=100,000 INR outgoing within 60 minutes of incoming and >=70% of inbound sum | +35 |
| R3 | >=5 outgoing payments to >=3 distinct recipients within 10 minutes | +20 |
| R4 | Time-ordered A->B->C->A transfer cycle within 24 hours | +25 |
| R5 | >=3 payments from one source between 90,000 and <100,000 INR within 24 hours | +20 |
| R6 | >=150,000 INR payment where `is_new_beneficiary` is explicitly `true` | +15 |

The score is capped at 100 and is a **demo heuristic**, not a fraud probability. R6 only runs when its optional enrichment column exists; no inference is made from missing beneficiary history. Rules trigger at most once per case in this version.

## Run
Install `requirements.txt`; start `python -m uvicorn api.main:app --reload --port 8000` in project root. In React use **Import CSV** and upload a file from `test_scenarios/`.

## Expected scenario outputs
- 09_outbound_velocity_R3.csv => R3 / score 20
- 10_circular_flow_R4.csv => R4 / score 25
- 11_near_internal_threshold_R5.csv => R5 / score 20
- 12_new_beneficiary_R6.csv => R6 / score 15
- 13_existing_beneficiary_negative.csv => none / score 0
- 14_velocity_boundary_negative.csv => none / score 0
- 15_open_chain_no_cycle.csv => none / score 0

Run `python -m pytest -q`. Every rule hit contains exact `evidence_ids` from the CSV and is inserted into the evidence findings. The original transaction analysis agent still specializes in R1 and R2, while the rule engine covers R1–R6. The local LLM narrative, if enabled, is not independently verified claim-by-claim.
