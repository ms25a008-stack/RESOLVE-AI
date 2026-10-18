import asyncio
from typing import Any
from fastapi import HTTPException
from app.agents.graph import compiled_graph
from app.agents.state import ResolveAgentState

async def run_multi_agent_workflow(ticket: dict, history: list[dict], teams: list[dict], settings: Any) -> dict:
    """Execute the compiled LangGraph multi-agent workflow for incident investigation."""
    if not settings.gemini_api_key:
        raise HTTPException(503, 'Gemini is not configured. Add GEMINI_API_KEY in the backend secret settings.')
    if not settings.gemini_free_tier_confirmed:
        raise HTTPException(503, 'Confirm the Gemini project uses the free tier before enabling AI.')
        
    initial_state: ResolveAgentState = {
        "ticket": ticket,
        "history_pool": history,
        "teams_pool": teams,
        "settings": settings,
        "triage": None,
        "knowledge": None,
        "resolver": None,
        "resolution": None,
        "sla": None,
        "collaboration": None,
        "traces": [],
        "routing_decisions": [],
        "sla_completed_early": False,
        "resolution_retries": 0,
        "validation_error": None,
        "status": "in_progress",
        "final_recommendation": None
    }
    
    try:
        final_state = await compiled_graph.ainvoke(initial_state)
        rec = final_state.get('final_recommendation')
        if not rec:
            raise HTTPException(502, "Multi-agent workflow failed to produce a final recommendation.")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        err_str = str(e)
        if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
            raise HTTPException(429, 'Gemini quota reached. Try later; no paid fallback is enabled.')
        raise HTTPException(502, f"Multi-agent investigation failed: {err_str}")
