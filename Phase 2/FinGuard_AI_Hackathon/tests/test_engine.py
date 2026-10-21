import pandas as pd
from finguard.demo_data import demo_transactions
from finguard.engine import run_investigation, validate_transactions

def test_demo_case_triggers_rules():
    result = run_investigation(demo_transactions())
    assert result["alert"]["score"] >= 60
    assert len(result["alert"]["triggered_rules"]) >= 1

def test_all_evidence_ids_exist():
    result = run_investigation(demo_transactions())
    valid = set(result["transactions"].transaction_id.astype(str))
    for f in result["evidence_agent"]["findings"]:
        assert set(f["evidence_ids"]).issubset(valid)

def test_invalid_amount_rejected():
    df = demo_transactions()
    df.loc[0, "amount"] = -1
    try:
        validate_transactions(df)
        assert False, "Expected validation error"
    except ValueError:
        assert True
