from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Actor:
    id: str
    metadata: dict = field(default_factory=dict, hash=False, compare=False)
    def __post_init__(self):
        if not self.id or not self.id.strip(): raise ValueError("Actor.id must be non-empty")

@dataclass(frozen=True)
class Event:
    id: str
    metadata: dict = field(default_factory=dict, hash=False, compare=False)
    def __post_init__(self):
        if not self.id or not self.id.strip(): raise ValueError("Event.id must be non-empty")

@dataclass(frozen=True)
class Assignment:
    actor_id: str
    event_id: str
    start: int
    duration: int
    participant_id: str | None = field(default=None, hash=False, compare=False)
    metadata: dict = field(default_factory=dict, hash=False, compare=False)
    def __post_init__(self):
        if not self.actor_id.strip(): raise ValueError("actor_id must be non-empty")
        if not self.event_id.strip(): raise ValueError("event_id must be non-empty")
        if self.start < 0: raise ValueError("start must be >= 0")
        if self.duration < 1: raise ValueError("duration must be >= 1")
    @property
    def end(self): return self.start + self.duration
