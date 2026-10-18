import operator
from typing import TypedDict, Annotated, Optional, Literal, List, Dict, Any
from app.models import Category, Priority

class AgentTrace(TypedDict):
    agent: str
    action: str
    tool: str
    status: str
    detail: str
    timestamp: str

class ResolveAgentState(TypedDict):
    # Core ticket and environment inputs
    ticket: dict
    history_pool: list[dict]
    teams_pool: list[dict]
    settings: Any

    # Individual agent outputs
    triage: Optional[dict]
    knowledge: Optional[dict]
    resolver: Optional[dict]
    resolution: Optional[dict]
    sla: Optional[dict]
    collaboration: Optional[dict]

    # Dynamic orchestration control
    traces: Annotated[list[dict], operator.add]
    routing_decisions: Annotated[list[str], operator.add]
    sla_completed_early: bool
    resolution_retries: int
    validation_error: Optional[str]
    status: str

    # Consolidated output for backward-compatible response
    final_recommendation: Optional[dict]
