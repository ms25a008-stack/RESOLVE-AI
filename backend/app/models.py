from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
Category = Literal['Network','Identity','Applications','Hardware','Cloud','Security']
Priority = Literal['P1','P2','P3','P4']
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
class TicketInput(Strict):
    title: str = Field(min_length=5,max_length=160)
    description: str = Field(min_length=20,max_length=5000)
    priority: Priority = 'P3'
    category: Category = 'Applications'
class Step(Strict):
    instruction: str = Field(min_length=5,max_length=1500)
    source_ids: list[str] = Field(max_length=5)
    basis: Literal['historical','hypothesis']
class Analysis(Strict):
    category: Category
    suggested_priority: Priority
    summary: str = Field(min_length=10,max_length=2500)
    hypotheses: list[str] = Field(max_length=8)
    required_expertise: list[str] = Field(max_length=8)
    steps: list[Step] = Field(min_length=1,max_length=8)
    uncertainties: list[str] = Field(min_length=1,max_length=8)
class Decision(Strict):
    decision: Literal['approved','rejected']
    comment: str = Field(min_length=5,max_length=2000)
class Change(Strict):
    version: int = Field(ge=1)
    status: Literal['open','in_progress','waiting','resolved']
    solution: str = Field(default='',max_length=5000)
    note: str = Field(min_length=5,max_length=2000)
class Note(Strict):
    note: str = Field(min_length=3,max_length=2000)

class TriageOutput(Strict):
    category: Category
    urgency: Literal['critical','high','medium','low']
    suggested_priority: Priority
    required_expertise: list[str] = Field(max_length=8)
    impact_assessment: str = Field(min_length=5,max_length=2000)
    fast_track_required: bool = False

class KnowledgeOutput(Strict):
    sources_found: list[dict] = Field(default_factory=list)
    query_terms_used: list[str] = Field(default_factory=list)
    coverage_score: float = 0.0
    hypothesis_only: bool = False
    synthesis_notes: str = Field(default='',max_length=2000)

class ResolverOutput(Strict):
    recommended_team: dict
    alternate_teams: list[dict] = Field(default_factory=list)
    capacity_constrained: bool = False
    reasoning: str = Field(min_length=5,max_length=2000)

class ResolutionOutput(Strict):
    summary: str = Field(min_length=10,max_length=2500)
    hypotheses: list[str] = Field(max_length=8)
    steps: list[Step] = Field(min_length=1,max_length=8)
    uncertainties: list[str] = Field(min_length=1,max_length=8)

class SLAOutput(Strict):
    state: Literal['on_track','at_risk','breached','met','missed']
    reason: str
    minutes_remaining: int
    elapsed_percent: int
    escalation_needed: bool = False
    advisory: str = Field(default='',max_length=1500)

class CollaborationOutput(Strict):
    executive_summary: str = Field(min_length=10,max_length=2500)
    engineer_review_packet: str = Field(min_length=10,max_length=3000)
    suggested_handoff_note: str = Field(default='',max_length=2000)
    requester_update: str = Field(default='',max_length=2000)

class AgentTraceEvent(Strict):
    agent: str
    action: str
    tool: str = ''
    status: str
    detail: str
    timestamp: str

class MultiAgentBundle(Strict):
    triage: TriageOutput
    knowledge: KnowledgeOutput
    resolver: ResolverOutput
    resolution: ResolutionOutput
    sla: SLAOutput
    collaboration: CollaborationOutput
    traces: list[AgentTraceEvent] = Field(default_factory=list)
    routing_decisions: list[str] = Field(default_factory=list)
    retries_used: int = 0
