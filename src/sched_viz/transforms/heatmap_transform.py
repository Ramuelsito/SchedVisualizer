from __future__ import annotations
from dataclasses import dataclass
from ..domain.solution import Solution

AUTO_TARGET_BUCKETS = 30


@dataclass
class HeatmapViewModel:
    z: list[list[float]]
    actor_labels: list[str]
    bucket_labels: list[str]
    bucket_size: int
    max_value: float
    metric: str


class HeatmapTransformer:
    def __init__(self, bucket_size="auto", sort_actors="alpha", metric="occupancy"):
        if metric not in ("occupancy", "assignments", "events"):
            raise ValueError(f"Invalid metric: {metric}")
        self._bucket_size = bucket_size
        self._sort_actors = sort_actors
        self._metric = metric

    def transform(self, solution: Solution) -> HeatmapViewModel:
        t_start, t_end = solution.timeline_start, solution.timeline_end
        span = max(t_end - t_start, 1)
        bucket_size = (
            max(1, round(span / AUTO_TARGET_BUCKETS))
            if self._bucket_size == "auto"
            else int(self._bucket_size)
        )
        n_buckets = max(1, (span + bucket_size - 1) // bucket_size)
        actor_ids = (
            sorted(solution.actor_ids) if self._sort_actors == "alpha" else self._by_load(solution)
        )
        if self._metric == "occupancy":
            z = self._occupancy(solution, actor_ids, t_start, n_buckets, bucket_size)
        elif self._metric == "assignments":
            z = self._assignments(solution, actor_ids, t_start, n_buckets, bucket_size)
        else:
            z = self._events(solution, actor_ids, t_start, n_buckets, bucket_size)
        max_value = max((max(row) for row in z if row), default=1.0) or 1.0
        return HeatmapViewModel(
            z=z,
            actor_labels=actor_ids,
            bucket_labels=[str(t_start + i * bucket_size) for i in range(n_buckets)],
            bucket_size=bucket_size,
            max_value=max_value,
            metric=self._metric,
        )

    def _occupancy(self, sol, actors, t0, nb, bs):
        z = {a: [0.0] * nb for a in actors}
        for a in sol.assignments:
            for t in range(a.start, a.end):
                idx = (t - t0) // bs
                if 0 <= idx < nb:
                    z[a.actor_id][idx] += 1.0
        return [z[a] for a in actors]

    def _assignments(self, sol, actors, t0, nb, bs):
        z = {a: [0.0] * nb for a in actors}
        for a in sol.assignments:
            for idx in range(max(0, (a.start - t0) // bs), min(nb, (a.end - 1 - t0) // bs + 1)):
                z[a.actor_id][idx] += 1.0
        return [z[a] for a in actors]

    def _events(self, sol, actors, t0, nb, bs):
        z: dict[str, list[set[str]]] = {actor: [set() for _ in range(nb)] for actor in actors}
        for a in sol.assignments:
            for idx in range(max(0, (a.start - t0) // bs), min(nb, (a.end - 1 - t0) // bs + 1)):
                z[a.actor_id][idx].add(a.event_id)
        return [[float(len(c)) for c in z[a]] for a in actors]

    def _by_load(self, sol):
        from collections import Counter

        return [aid for aid, _ in Counter(a.actor_id for a in sol.assignments).most_common()]
