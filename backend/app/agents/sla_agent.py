from datetime import datetime, timezone
from app.agents.state import ResolveAgentState
from app.agents.tools import calculate_sla_tool
from app.models import SLAOutput

async def sla_node(state: ResolveAgentState) -> dict:
    ticket = state['ticket']
    triage = state.get('triage') or {}
    
    # Deterministic SLA calculation tool invocation
    metrics = calculate_sla_tool(ticket)
    
    minutes_remaining = metrics['minutes_remaining']
    elapsed_percent = metrics['elapsed_percent']
    sla_state = metrics['state']
    
    # Assess escalation necessity
    is_fast_track = triage.get('fast_track_required', False)
    escalation_needed = (sla_state in ('at_risk', 'breached')) or is_fast_track
    
    # Generate deterministic advisory
    if sla_state == 'breached':
        advisory = f"CRITICAL: SLA breach occurred. Resolution is {abs(minutes_remaining)} minutes overdue. Immediate senior engineer assignment required."
    elif sla_state == 'at_risk':
        advisory = f"WARNING: SLA at risk. Only {minutes_remaining} minutes remaining ({elapsed_percent}% budget consumed). High priority triage dispatch needed."
    elif is_fast_track:
        advisory = f"ELEVATED: Fast-track priority detected by Triage. SLA clock is active with {minutes_remaining} minutes remaining."
    else:
        advisory = f"NORMAL: SLA on track. {minutes_remaining} minutes remaining ({elapsed_percent}% elapsed)."

    output = SLAOutput(
        state=sla_state,
        reason=metrics['reason'],
        minutes_remaining=minutes_remaining,
        elapsed_percent=elapsed_percent,
        escalation_needed=escalation_needed,
        advisory=advisory
    )
    
    now_str = datetime.now(timezone.utc).isoformat()
    trace = {
        "agent": "SLA Agent",
        "action": "Deterministic SLA Metric Calculation & Risk Assessment",
        "tool": "calculate_sla_tool",
        "status": "completed",
        "detail": f"State: {sla_state}, Remaining: {minutes_remaining}m, Elapsed: {elapsed_percent}%, Escalation: {escalation_needed}",
        "timestamp": now_str
    }
    
    decision = f"SLA Agent evaluated: state={sla_state}, escalation_needed={escalation_needed}"
    
    return {
        "sla": output.model_dump(),
        "traces": [trace],
        "routing_decisions": [decision]
    }
