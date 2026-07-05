from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from ..domain.solution import Solution


@dataclass
class ActorUtilization:
    actor_id: str
    assigned_duration: int
    timeline_length: int
    utilization: float
    n_assignments: int


@dataclass
class UtilizationViewModel:
    actors: list[ActorUtilization]
    timeline_length: int
    mean_utilization: float
    median_utilization: float


class UtilizationTransformer:
    def transform(self, solution: Solution) -> UtilizationViewModel:
        tl = solution.timeline_length or 1
        dur: defaultdict[str, int] = defaultdict(int)
        cnt: defaultdict[str, int] = defaultdict(int)
        for a in solution.assignments:
            dur[a.actor_id] += a.duration
            cnt[a.actor_id] += 1
        actors = sorted(
            [
                ActorUtilization(
                    actor_id=aid,
                    assigned_duration=total,
                    timeline_length=tl,
                    utilization=min(total / tl, 1.0),
                    n_assignments=cnt[aid],
                )
                for aid, total in dur.items()
            ],
            key=lambda x: x.utilization,
            reverse=True,
        )
        utils = [a.utilization for a in actors]
        n = len(utils)
        mean = sum(utils) / n
        mid = n // 2
        median = utils[mid] if n % 2 == 1 else (utils[mid - 1] + utils[mid]) / 2
        return UtilizationViewModel(
            actors=actors, timeline_length=tl, mean_utilization=mean, median_utilization=median
        )
