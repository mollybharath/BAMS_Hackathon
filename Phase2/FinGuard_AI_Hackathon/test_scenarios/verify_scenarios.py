"""Run from FinGuard_AI_Hackathon root after placing scenario CSVs in scenario_test_pack/."""
from pathlib import Path
import pandas as pd
from finguard.agentic import run_agentic_investigation

root = Path(__file__).resolve().parent
cases = {
 '01_normal_low_risk.csv': (0, set()),
 '02_inbound_concentration_R1.csv': (40, {'R1'}),
 '03_rapid_pass_through_R2.csv': (35, {'R2'}),
 '04_both_R1_R2.csv': (75, {'R1','R2'}),
 '05_delayed_transfer_no_R2.csv': (40, {'R1'}),
 '06_connected_chain_network_only.csv': (0, set()),
 '07_threshold_boundary_no_R1.csv': (0, set()),
}
for filename, (score, expected) in cases.items():
    result = run_agentic_investigation(pd.read_csv(root / filename), filename)
    actual = {rule.split(' ')[0] for rule in result['alert']['triggered_rules']}
    valid_ids = set(pd.read_csv(root / filename)['transaction_id'].astype(str))
    assert result['alert']['score'] == score, filename
    assert actual == expected, (filename, actual, expected)
    assert all(set(f['evidence_ids']).issubset(valid_ids) for f in result['findings']), filename
    print(f'PASS {filename}: score={score}, rules={sorted(actual)}')
try:
    run_agentic_investigation(pd.read_csv(root / '08_invalid_duplicate_ids.csv'), 'invalid')
    raise AssertionError('Duplicate IDs should have been rejected')
except ValueError as exc:
    assert 'unique' in str(exc)
    print('PASS 08_invalid_duplicate_ids.csv: duplicate IDs rejected')
print('All eight scenarios passed')
