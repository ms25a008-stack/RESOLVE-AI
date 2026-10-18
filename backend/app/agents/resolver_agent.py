from datetime import datetime, timezone
from app.agents.state import ResolveAgentState
from app.agents.tools import rank_resolver_teams_tool
from app.models import ResolverOutput

async def resolver_node(state: ResolveAgentState) -> dict:
    ticket = state['ticket']
    teams_pool = state.get('teams_pool', [])
    history_pool = state.get('history_pool', [])
    triage = state.get('triage') or {}
    
    category = triage.get('category') or ticket.get('category', 'Applications')
    expertise = triage.get('required_expertise') or []
    
    # Deterministic team scoring tool invocation
    ranked_teams = rank_resolver_teams_tool(
        category=category,
        expertise=expertise,
        teams=teams_pool,
        tickets=history_pool
    )
    
    if not ranked_teams:
        raise ValueError("No resolver teams configured in system.")
        
    recommended = ranked_teams[0]
    alternates = ranked_teams[1:3]
    
    capacity_constrained = recommended.get('active_tickets', 0) >= recommended.get('capacity', 1)
    
    reasoning = recommended.get('reason', '')
    if capacity_constrained:
        reasoning += f" CAUTION: {recommended['name']} has reached its configured workload limit ({recommended['active_tickets']}/{recommended['capacity']}). Consider escalation or routing to {alternates[0]['name'] if alternates else 'supervisor'}."
    
    output = ResolverOutput(
        recommended_team=recommended,
        alternate_teams=alternates,
        capacity_constrained=capacity_constrained,
        reasoning=reasoning
    )
    
    now_str = datetime.now(timezone.utc).isoformat()
    trace = {
        "agent": "Resolver Agent",
        "action": "Team Workload Balancing & Skill-Match Scoring",
        "tool": "rank_resolver_teams_tool",
        "status": "completed",
        "detail": f"Recommended: {recommended['name']} (Score: {recommended['score']}/100, Load: {recommended['active_tickets']}/{recommended['capacity']}, Constrained: {capacity_constrained})",
        "timestamp": now_str
    }
    
    decision = f"Resolver Agent selected: {recommended['name']} (score={recommended['score']}, constrained={capacity_constrained})"
    
    return {
        "resolver": output.model_dump(),
        "traces": [trace],
        "routing_decisions": [decision]
    }
