import pytest
import asyncio
from datetime import timedelta
from app.domain import now
from app.config import Settings
from app.agents.tools import (
    calculate_sla_tool,
    search_knowledge_tool,
    rank_resolver_teams_tool,
    validate_citations_tool
)
from app.agents.graph import create_resolve_graph, route_after_triage, route_after_resolver, route_after_resolution
from app.agents.state import ResolveAgentState

# Sample fixtures
@pytest.fixture
def sample_ticket():
    n = now()
    return {
        'id': 't-100',
        'number': 100,
        'title': 'VPN gateway disconnects intermittently',
        'description': 'Remote employees lose connection to the corporate VPN every 15 minutes.',
        'category': 'Network',
        'priority': 'P2',
        'status': 'open',
        'created_at': (n - timedelta(hours=2)).isoformat(),
        'sla_due_at': (n + timedelta(hours=6)).isoformat(),
        'resolved_at': None,
        'solution': '',
        'version': 1
    }

@pytest.fixture
def sample_history():
    return [
        {
            'id': 'hist-1',
            'number': 50,
            'title': 'Corporate VPN certificate expired',
            'description': 'VPN gateway rejected connections due to root CA expiry.',
            'solution': 'Renewed internal root CA and pushed updated VPN client profile.',
            'status': 'resolved',
            'category': 'Network'
        },
        {
            'id': 'hist-2',
            'number': 51,
            'title': 'Printer spooler crash on print server',
            'description': 'Spooler stopped responding.',
            'solution': 'Restarted print spooler service.',
            'status': 'resolved',
            'category': 'Hardware'
        }
    ]

@pytest.fixture
def sample_teams():
    return [
        {
            'id': 'team-net',
            'name': 'Network Operations',
            'categories': ['Network', 'Cloud'],
            'skills': ['vpn', 'firewall', 'routing', 'dns'],
            'capacity': 10
        },
        {
            'id': 'team-sys',
            'name': 'Systems Engineering',
            'categories': ['Applications', 'Identity'],
            'skills': ['linux', 'windows', 'active_directory'],
            'capacity': 8
        }
    ]

# 1. Test Tools
def test_tool_sla(sample_ticket):
    m = calculate_sla_tool(sample_ticket)
    assert m['state'] in ('on_track', 'at_risk', 'breached')
    assert isinstance(m['minutes_remaining'], int)
    assert 0 <= m['elapsed_percent'] <= 100

def test_tool_knowledge_retrieval(sample_ticket, sample_history):
    matches = search_knowledge_tool(sample_ticket, sample_history)
    assert len(matches) == 1
    assert matches[0]['id'] == 'hist-1'
    assert 'vpn' in matches[0]['matched_terms']

def test_tool_knowledge_expansion(sample_ticket, sample_history):
    # Query with extra term
    ticket_sparse = {'id': 't-x', 'title': 'Remote connection issue', 'description': 'Users cannot connect from home', 'status': 'open'}
    no_expansion = search_knowledge_tool(ticket_sparse, sample_history)
    assert len(no_expansion) == 0
    with_expansion = search_knowledge_tool(ticket_sparse, sample_history, extra_terms=['vpn'])
    assert len(with_expansion) == 1
    assert with_expansion[0]['id'] == 'hist-1'

def test_tool_resolver_scoring(sample_teams):
    ranked = rank_resolver_teams_tool('Network', ['vpn', 'firewall'], sample_teams, [])
    assert ranked[0]['name'] == 'Network Operations'
    assert ranked[0]['score'] > 60

def test_tool_citation_validation():
    sources = [{'id': 's1'}, {'id': 's2'}]
    
    # Valid historical
    valid_hist = [{'instruction': 'Check logs', 'source_ids': ['s1'], 'basis': 'historical'}]
    ok, msg = validate_citations_tool(valid_hist, sources)
    assert ok and not msg
    
    # Valid hypothesis
    valid_hyp = [{'instruction': 'Test connection', 'source_ids': [], 'basis': 'hypothesis'}]
    ok, msg = validate_citations_tool(valid_hyp, sources)
    assert ok and not msg
    
    # Unknown source
    invalid_unknown = [{'instruction': 'Check logs', 'source_ids': ['s99'], 'basis': 'historical'}]
    ok, msg = validate_citations_tool(invalid_unknown, sources)
    assert not ok and 'unknown' in msg.lower()
    
    # Historical without source
    invalid_no_source = [{'instruction': 'Check logs', 'source_ids': [], 'basis': 'historical'}]
    ok, msg = validate_citations_tool(invalid_no_source, sources)
    assert not ok and 'no source' in msg.lower()
    
    # Hypothesis with source
    invalid_hyp_with_source = [{'instruction': 'Check logs', 'source_ids': ['s1'], 'basis': 'hypothesis'}]
    ok, msg = validate_citations_tool(invalid_hyp_with_source, sources)
    assert not ok and 'cannot cite' in msg.lower()

# 2. Test Conditional Routing Functions
def test_routing_after_triage():
    # Normal P3
    state_normal = {'ticket': {'priority': 'P3'}, 'triage': {'urgency': 'medium', 'suggested_priority': 'P3', 'fast_track_required': False}}
    assert route_after_triage(state_normal) == 'standard_knowledge'
    
    # Fast-track P1
    state_p1 = {'ticket': {'priority': 'P1'}, 'triage': {'urgency': 'critical', 'suggested_priority': 'P1', 'fast_track_required': True}}
    assert route_after_triage(state_p1) == 'fast_track_sla'

def test_routing_after_resolver():
    # Fast track where SLA already ran
    state_fast = {'sla': {'state': 'at_risk'}}
    assert route_after_resolver(state_fast) == 'run_resolution'
    
    # Standard route where SLA has not run yet
    state_std = {'sla': None}
    assert route_after_resolver(state_std) == 'run_sla'

def test_routing_after_resolution_retry():
    state_retry = {
        'validation_error': 'Step 1 cites unknown source',
        'resolution_retries': 0,
        'settings': Settings(max_resolution_retries=2)
    }
    assert route_after_resolution(state_retry) == 'retry_resolution'
    assert state_retry['resolution_retries'] == 1
    
    # Exhausted retries
    state_exhausted = {
        'validation_error': 'Still bad',
        'resolution_retries': 2,
        'resolution': {'steps': [{'basis': 'historical', 'source_ids': ['bad']}]},
        'settings': Settings(max_resolution_retries=2)
    }
    assert route_after_resolution(state_exhausted) == 'proceed_to_collaboration'
    assert state_exhausted['resolution']['steps'][0]['basis'] == 'hypothesis'
    assert state_exhausted['resolution']['steps'][0]['source_ids'] == []

# 3. End-to-end Graph Execution with Mock LLM
@pytest.mark.anyio
async def test_graph_mock_run(monkeypatch, sample_ticket, sample_history, sample_teams):
    from app.models import TriageOutput, ResolutionOutput, Step
    
    async def mock_call_llm(settings, system_prompt, user_prompt, schema_class, temperature=0.1):
        if schema_class == TriageOutput:
            return TriageOutput(
                category='Network',
                urgency='high',
                suggested_priority='P2',
                required_expertise=['vpn', 'routing'],
                impact_assessment='Remote workers unable to access internal network.',
                fast_track_required=False
            )
        elif schema_class == ResolutionOutput:
            return ResolutionOutput(
                summary='VPN connectivity degradation likely linked to gateway certificates or routing.',
                hypotheses=['Gateway certificate requires renewal.', 'Client network routing conflict.'],
                steps=[
                    Step(instruction='Verify gateway certificate status in management console.', source_ids=['hist-1'], basis='historical'),
                    Step(instruction='Check client MTU settings.', source_ids=[], basis='hypothesis')
                ],
                uncertainties=['Current gateway error log details are unverified.']
            )
        raise ValueError(f"Unexpected schema: {schema_class}")
        
    monkeypatch.setattr('app.agents.triage_agent.call_llm_structured', mock_call_llm)
    monkeypatch.setattr('app.agents.resolution_agent.call_llm_structured', mock_call_llm)
    
    from app.agents.runner import run_multi_agent_workflow
    settings = Settings(gemini_api_key='mock-key', gemini_free_tier_confirmed=True)
    
    result = await run_multi_agent_workflow(sample_ticket, sample_history, sample_teams, settings)
    
    # Assert final bundle contract
    assert result['ticket_id'] == sample_ticket['id']
    assert result['analysis']['category'] == 'Network'
    assert result['analysis']['suggested_priority'] == 'P2'
    assert len(result['analysis']['steps']) == 2
    assert result['resolver']['name'] == 'Network Operations'
    
    # Assert multi_agent breakdown is present
    ma = result['multi_agent']
    assert 'triage' in ma
    assert 'knowledge' in ma
    assert 'resolver' in ma
    assert 'resolution' in ma
    assert 'sla' in ma
    assert 'collaboration' in ma
    assert len(ma['traces']) >= 6
    assert len(ma['routing_decisions']) >= 4
