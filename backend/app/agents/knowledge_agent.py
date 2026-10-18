from datetime import datetime, timezone
from app.agents.state import ResolveAgentState
from app.agents.tools import search_knowledge_tool
from app.models import KnowledgeOutput
from app.domain import tokens

async def knowledge_node(state: ResolveAgentState) -> dict:
    ticket = state['ticket']
    history_pool = state.get('history_pool', [])
    triage = state.get('triage') or {}
    
    extra_skills = triage.get('required_expertise', [])
    
    # 1. Primary search invocation
    initial_matches = search_knowledge_tool(ticket, history_pool, extra_terms=None, limit=5, min_score=0.12)
    
    used_expansion = False
    final_matches = initial_matches
    
    # 2. Dynamic Query Expansion if no matches found
    if not initial_matches and extra_skills:
        used_expansion = True
        expanded_matches = search_knowledge_tool(ticket, history_pool, extra_terms=extra_skills, limit=5, min_score=0.10)
        if expanded_matches:
            final_matches = expanded_matches

    coverage = round(max((m['retrieval_score'] for m in final_matches), default=0.0), 3)
    hypothesis_only = len(final_matches) == 0
    
    if hypothesis_only:
        synthesis = "No relevant historical incidents with documented solutions were found. Investigation must proceed using unverified hypotheses."
    elif used_expansion:
        synthesis = f"Retrieved {len(final_matches)} relevant historical incidents using triage-expanded search ({', '.join(extra_skills)})."
    else:
        synthesis = f"Found {len(final_matches)} historical incidents with strong keyword match in the knowledge base."

    query_tokens = sorted(tokens(ticket.get('title', '') + ' ' + ticket.get('description', '')))
    
    output = KnowledgeOutput(
        sources_found=final_matches,
        query_terms_used=query_tokens[:12],
        coverage_score=coverage,
        hypothesis_only=hypothesis_only,
        synthesis_notes=synthesis
    )
    
    now_str = datetime.now(timezone.utc).isoformat()
    trace = {
        "agent": "Knowledge Agent",
        "action": "Historical Incident Retrieval & Grounding Evaluation",
        "tool": "search_knowledge_tool",
        "status": "completed",
        "detail": f"Retrieved {len(final_matches)} sources (max score: {coverage}). Expansion used: {used_expansion}. Hypothesis only: {hypothesis_only}",
        "timestamp": now_str
    }
    
    decision = f"Knowledge Agent: found {len(final_matches)} sources (hypothesis_only={hypothesis_only})"
    
    return {
        "knowledge": output.model_dump(),
        "traces": [trace],
        "routing_decisions": [decision]
    }
