from finguard.demo_data import demo_transactions
from finguard.agentic import run_agentic_investigation


def test_agentic_workflow_has_planner_critic_and_report():
    result = run_agentic_investigation(demo_transactions())
    agents = {step['agent'] for step in result['steps']}
    assert 'Investigation Planner' in agents
    assert 'Evidence Critic' in agents
    assert 'Report Agent' in agents
    assert result['alert']['score'] >= 60
    assert result['network']['nodes']
    assert result['report_markdown'].startswith('# FinGuard AI Investigation Draft')


def test_all_findings_have_valid_evidence_ids():
    result = run_agentic_investigation(demo_transactions())
    valid = {row['transaction_id'] for row in result['transactions']}
    for finding in result['findings']:
        assert set(finding['evidence_ids']).issubset(valid)


def test_no_external_llm_is_required():
    result = run_agentic_investigation(demo_transactions())
    assert result['plan']
    assert result['human_decision']['status'] == 'pending'


def test_api_health_and_investigation():
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    assert client.get('/api/health').json()['mode'] == 'local-only'
    demo = client.get('/api/demo').json()
    response = client.post('/api/investigate', json={'case_id': 'TEST-API-001', 'transactions': demo['transactions']})
    assert response.status_code == 200
    assert response.json()['case_id'] == 'TEST-API-001'
