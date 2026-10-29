from pathlib import Path
import pandas as pd
import pytest
from finpro.engine import detect_alerts, validate_transactions
from finpro.agentic import run_agentic_investigation

CASES = Path(__file__).resolve().parents[1] / "test_scenarios"
@pytest.mark.parametrize("filename,expected", [
    ("09_outbound_velocity_R3.csv", {"R3"}),
    ("10_circular_flow_R4.csv", {"R4"}),
    ("11_near_internal_threshold_R5.csv", {"R5"}),
    ("12_new_beneficiary_R6.csv", {"R6"}),
    ("13_existing_beneficiary_negative.csv", set()),
    ("14_velocity_boundary_negative.csv", set()),
    ("15_open_chain_no_cycle.csv", set()),
])
def test_rule_scenarios(filename, expected):
    df = validate_transactions(pd.read_csv(CASES / filename))
    result = detect_alerts(df)
    assert {x["rule_id"] for x in result["rule_hits"]} == expected
    valid = set(df.transaction_id)
    for hit in result["rule_hits"]:
        assert set(hit["evidence_ids"]).issubset(valid)

def test_new_rules_surface_as_evidence_findings():
    result = run_agentic_investigation(pd.read_csv(CASES / "09_outbound_velocity_R3.csv"))
    assert any(f.get("rule_id") == "R3" for f in result["findings"])
