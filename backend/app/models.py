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
