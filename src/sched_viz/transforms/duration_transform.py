from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from ..domain.solution import Solution


@dataclass
class DurationViewModel:
    durations_by_event: dict[str, list[int]]
    all_durations: list[int]
    min_duration: int
    max_duration: int
    mean_duration: float


class DurationTransformer:
    def transform(self, solution: Solution) -> DurationViewModel:
        by_event = defaultdict(list)
        for a in solution.assignments:
            by_event[a.event_id].append(a.duration)
        all_d = [a.duration for a in solution.assignments]
        return DurationViewModel(
            durations_by_event=dict(by_event),
            all_durations=all_d,
            min_duration=min(all_d),
            max_duration=max(all_d),
            mean_duration=sum(all_d) / len(all_d),
        )
