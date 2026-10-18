from langgraph.graph import StateGraph, START, END
from app.agents.state import ResolveAgentState
from app.agents.triage_agent import triage_node
from app.agents.sla_agent import sla_node
from app.agents.knowledge_agent import knowledge_node
from app.agents.resolver_agent import resolver_node
from app.agents.resolution_agent import resolution_node
from app.agents.collaboration_agent import collaboration_node
from app.agents.tools import validate_citations_tool

def route_after_triage(state: ResolveAgentState) -> str:
    """Conditional router after triage: fast-track P1/critical incidents to SLA first."""
    triage = state.get('triage') or {}
    ticket = state.get('ticket') or {}
    
    is_p1 = ticket.get('priority') == 'P1' or triage.get('suggested_priority') == 'P1'
    is_critical = triage.get('urgency') == 'critical' or triage.get('fast_track_required', False)
    
    if is_p1 or is_critical:
        return "fast_track_sla"
    return "standard_knowledge"

def route_after_sla(state: ResolveAgentState) -> str:
    """Conditional router after SLA: if fast-tracked, continue to knowledge; else go to resolution."""
    # If resolver has not run yet, this SLA was fast-tracked
    if not state.get('resolver'):
        return "continue_to_knowledge"
    return "continue_to_resolution"

def route_after_resolver(state: ResolveAgentState) -> str:
    """Conditional router after resolver: if SLA hasn't run yet, run SLA; else proceed to resolution."""
    if not state.get('sla'):
        return "run_sla"
    return "run_resolution"

def route_after_resolution(state: ResolveAgentState) -> str:
    """Bounded retry conditional router: self-correct if citations fail validation."""
    val_error = state.get('validation_error')
    retries = state.get('resolution_retries', 0)
    settings = state.get('settings')
    max_retries = getattr(settings, 'max_resolution_retries', 2) if settings else 2
    
    if val_error and retries < max_retries:
        state['resolution_retries'] = retries + 1
        return "retry_resolution"
    
    # If retries exhausted and error still exists, sanitize steps for safety
    if val_error and state.get('resolution'):
        res = state['resolution']
        for step in res.get('steps', []):
            step['basis'] = 'hypothesis'
            step['source_ids'] = []
        state['validation_error'] = None
        
    return "proceed_to_collaboration"

def create_resolve_graph():
    """Build and compile the multi-agent StateGraph with conditional edges and bounded retries."""
    workflow = StateGraph(ResolveAgentState)
    
    # 1. Register all 6 agent nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("sla", sla_node)
    workflow.add_node("knowledge", knowledge_node)
    workflow.add_node("resolver", resolver_node)
    workflow.add_node("resolution", resolution_node)
    workflow.add_node("collaboration", collaboration_node)
    
    # 2. Add edges with conditional routing
    workflow.add_edge(START, "triage")
    
    # Triage conditional branching
    workflow.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "fast_track_sla": "sla",
            "standard_knowledge": "knowledge"
        }
    )
    
    # Knowledge always proceeds to resolver
    workflow.add_edge("knowledge", "resolver")
    
    # Resolver conditional branching
    workflow.add_conditional_edges(
        "resolver",
        route_after_resolver,
        {
            "run_sla": "sla",
            "run_resolution": "resolution"
        }
    )
    
    # SLA conditional branching
    workflow.add_conditional_edges(
        "sla",
        route_after_sla,
        {
            "continue_to_knowledge": "knowledge",
            "continue_to_resolution": "resolution"
        }
    )
    
    # Resolution self-correction bounded retry loop
    workflow.add_conditional_edges(
        "resolution",
        route_after_resolution,
        {
            "retry_resolution": "resolution",
            "proceed_to_collaboration": "collaboration"
        }
    )
    
    # Collaboration completes workflow
    workflow.add_edge("collaboration", END)
    
    return workflow.compile()

# Global compiled instance
compiled_graph = create_resolve_graph()
