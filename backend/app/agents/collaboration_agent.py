from datetime import datetime, timezone
from app.agents.state import ResolveAgentState
from app.models import CollaborationOutput

async def collaboration_node(state: ResolveAgentState) -> dict:
    ticket = state['ticket']
    settings = state['settings']
    triage = state.get('triage') or {}
    knowledge = state.get('knowledge') or {}
    resolver = state.get('resolver') or {}
    resolution = state.get('resolution') or {}
    sla = state.get('sla') or {}
    traces = state.get('traces') or []
    routing = state.get('routing_decisions') or []
    
    rec_team = resolver.get('recommended_team', {})
    category = triage.get('category', ticket.get('category', 'Applications'))
    suggested_priority = triage.get('suggested_priority', ticket.get('priority', 'P3'))
    
    # 1. Executive Summary
    exec_summary = (
        f"Incident '{ticket.get('title')}' classified as {category} with {triage.get('urgency', 'normal')} urgency. "
        f"{resolution.get('summary', '')} "
        f"Assigned routing recommended to {rec_team.get('name', 'Unassigned')} based on skill alignment and current workload."
    )
    
    # 2. Engineer Review Packet
    engineer_packet = (
        f"RECOMMENDED ACTION: Route to {rec_team.get('name', 'Unassigned')} under category '{category}'.\n"
        f"SLA STATUS: {sla.get('advisory', 'Normal')}\n"
        f"DIAGNOSTIC PLAN: {len(resolution.get('steps', []))} steps generated "
        f"({sum(1 for s in resolution.get('steps', []) if s.get('basis') == 'historical')} historically grounded, "
        f"{sum(1 for s in resolution.get('steps', []) if s.get('basis') == 'hypothesis')} hypotheses).\n"
        f"KEY UNCERTAINTIES: {'; '.join(resolution.get('uncertainties', ['None listed']))}\n"
        f"ROUTING JUSTIFICATION: {rec_team.get('reason', 'Skill & category alignment')}"
    )
    
    # 3. Suggested Handoff Note
    handoff_note = (
        f"ResolveAI Multi-Agent Analysis: Assigned to {rec_team.get('name')}. "
        f"Triage determined {triage.get('urgency')} urgency. SLA remaining: {sla.get('minutes_remaining', 0)} mins."
    )
    
    # 4. Requester Safe Update
    requester_update = (
        f"Your ticket regarding '{ticket.get('title')}' has been triaged and prioritized as {suggested_priority}. "
        f"The {rec_team.get('name')} team has been notified and is reviewing diagnostic steps."
    )
    
    collab_output = CollaborationOutput(
        executive_summary=exec_summary,
        engineer_review_packet=engineer_packet,
        suggested_handoff_note=handoff_note,
        requester_update=requester_update
    )
    
    # Backward compatible analysis dict
    legacy_analysis = {
        "category": category,
        "suggested_priority": suggested_priority,
        "summary": resolution.get('summary', exec_summary),
        "hypotheses": resolution.get('hypotheses', []),
        "required_expertise": triage.get('required_expertise', []),
        "steps": resolution.get('steps', []),
        "uncertainties": resolution.get('uncertainties', [])
    }
    
    # Sources list formatting
    raw_sources = knowledge.get('sources_found', [])
    legacy_sources = [
        {
            "id": s.get('id'),
            "number": s.get('number'),
            "title": s.get('title'),
            "solution": s.get('solution'),
            "retrieval_score": s.get('retrieval_score', 0.0),
            "matched_terms": s.get('matched_terms', []),
            "is_sample": s.get('is_sample', False)
        }
        for s in raw_sources
    ]
    
    now_str = datetime.now(timezone.utc).isoformat()
    trace = {
        "agent": "Collaboration Agent",
        "action": "Multi-Agent Synthesis & Engineer Decision Packet Assembly",
        "tool": "Collaboration Synthesis Engine",
        "status": "completed",
        "detail": f"Synthesized outputs across 5 agents. Assembled human-review packet for {rec_team.get('name')}.",
        "timestamp": now_str
    }
    
    all_traces = traces + [trace]
    all_routing = routing + ["Collaboration Agent finalized recommendation package."]
    
    # Final bundle
    final_bundle = {
        "ticket_id": str(ticket.get('id')),
        "ticket_version": ticket.get('version', 1),
        "analysis": legacy_analysis,
        "sources": legacy_sources,
        "resolver": rec_team,
        "model": getattr(settings, 'gemini_model', 'gemini-2.5-flash'),
        "multi_agent": {
            "triage": triage,
            "knowledge": knowledge,
            "resolver": resolver,
            "resolution": resolution,
            "sla": sla,
            "collaboration": collab_output.model_dump(),
            "traces": all_traces,
            "routing_decisions": all_routing
        }
    }
    
    return {
        "collaboration": collab_output.model_dump(),
        "final_recommendation": final_bundle,
        "status": "requires_approval",
        "traces": [trace],
        "routing_decisions": ["Collaboration Agent finalized recommendation package."]
    }
