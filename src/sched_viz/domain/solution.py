from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from .models import Assignment


@dataclass
class Solution:
    assignments: list[Assignment]
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.assignments:
            raise ValueError("Solution must contain at least one assignment")

    @property
    def actor_ids(self):
        return {a.actor_id for a in self.assignments}

    @property
    def event_ids(self):
        return {a.event_id for a in self.assignments}

    @property
    def timeline_start(self):
        return min(a.start for a in self.assignments)

    @property
    def timeline_end(self):
        return max(a.end for a in self.assignments)

    @property
    def timeline_length(self):
        return self.timeline_end - self.timeline_start

    def __len__(self):
        return len(self.assignments)

    def __repr__(self):
        return f"Solution(assignments={len(self.assignments)}, actors={len(self.actor_ids)}, timeline=[{self.timeline_start},{self.timeline_end}))"

    def filter_by_events(self, event_ids):
        return self._clone([a for a in self.assignments if a.event_id in set(event_ids)])

    def filter_by_actors(self, actor_ids):
        return self._clone([a for a in self.assignments if a.actor_id in set(actor_ids)])

    def filter_by_time_range(self, start, end):
        return self._clone([a for a in self.assignments if a.start < end and a.end > start])

    def top_actors_by_load(self, n):
        counts = Counter(a.actor_id for a in self.assignments)
        return self.filter_by_actors([aid for aid, _ in counts.most_common(n)])

    def _clone(self, assignments):
        if not assignments:
            raise ValueError("Filtered solution would be empty")
        return Solution(assignments=assignments, metadata=self.metadata.copy())
