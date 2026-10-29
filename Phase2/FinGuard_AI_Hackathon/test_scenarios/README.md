# FinGuard AI 2.0 — scenario validation pack

All records are synthetic. Import each CSV using **Import CSV** in the React app. Upload automatically runs an investigation.

| File | Expected risk score | Expected rules | Additional observation |
|---|---:|---|---|
| 01_normal_low_risk.csv | 0 | None | No findings |
| 02_inbound_concentration_R1.csv | 40 | R1 | Account hub |
| 03_rapid_pass_through_R2.csv | 35 | R2 | Connected path |
| 04_both_R1_R2.csv | 75 | R1, R2 | Account hub and path |
| 05_delayed_transfer_no_R2.csv | 40 | R1 | Network path still exists; network paths do not validate timing |
| 06_connected_chain_network_only.csv | 0 | None | Network path only |
| 07_threshold_boundary_no_R1.csv | 0 | None | Hub may still be reported, without a risk trigger |
| 08_invalid_duplicate_ids.csv | Error | Validation rejects duplicate transaction_id | No investigation report |

## Why this matters
The implementation currently has two scoring rules only: R1 inbound concentration (+40), R2 rapid outflow (+35). Network paths/hubs are informational and do not add score. The score is not a fraud probability. The planner is deterministic; local LLM is optional. Evidence validation checks references, not the truth of every narrative claim.

## Run
1. Start Python backend and React frontend.
2. Click **Import CSV** (not **Run investigation** first), choose a scenario file.
3. Compare the score and triggered indicators against the table above.
4. Review findings and transaction IDs. For the invalid dataset, expect a validation error.
5. For automated regression, copy `verify_scenarios.py` to your project root and place this scenario folder alongside it, then run `python verify_scenarios.py`.

## Important limitations
- All values are INR; do not combine different currencies without currency conversion.
- Existing rules are hardcoded demo heuristics, not validated financial-crime detection controls.
- The network analyzer may report a path even when transactions are hours apart. This is an observation, not proof of rapid layering.
- Current critic verifies ID membership and some prohibited phrasing, but not every amount, time claim, or model-generated sentence. Do not claim hallucinations are impossible.
- Scenario results were checked against the packaged FinGuard AI 2.0 code.
