from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from ..domain.models import Assignment
from ..domain.solution import Solution

class AssignmentInput(BaseModel):
    actor_id: str = Field(..., min_length=1)
    event_id: str = Field(..., min_length=1)
    start: int = Field(..., ge=0)
    duration: int = Field(..., ge=1)
    participant_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    def to_domain(self):
        return Assignment(actor_id=self.actor_id, event_id=self.event_id,
                          start=self.start, duration=self.duration,
                          participant_id=self.participant_id, metadata=self.metadata)

class SolutionInput(BaseModel):
    assignments: list[AssignmentInput] = Field(..., min_length=1)
    metadata: dict = Field(default_factory=dict)
    def to_domain(self):
        return Solution(assignments=[a.to_domain() for a in self.assignments], metadata=self.metadata)
