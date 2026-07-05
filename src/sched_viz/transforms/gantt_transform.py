from __future__ import annotations
from dataclasses import dataclass
from itertools import groupby
from ..config import VisConfig
from ..core.color_registry import ColorRegistry
from ..domain.solution import Solution


@dataclass
class GanttBar:
    actor_id: str
    event_id: str
    start: int
    end: int
    label: str = ""

    @property
    def duration(self):
        return self.end - self.start


@dataclass
class GanttViewModel:
    bars: list[GanttBar]
    actor_order: list[str]
    color_map: dict[str, str]
    timeline_start: int
    timeline_end: int


class GanttTransformer:
    def __init__(self, config=None, merge_bars=True, sort_actors="alpha", color_map=None):
        self._config = config or VisConfig()
        self._merge_bars = merge_bars
        self._sort_actors = sort_actors
        self._external_color_map = color_map

    def transform(self, solution: Solution) -> GanttViewModel:
        color_map = (
            self._external_color_map
            if self._external_color_map is not None
            else ColorRegistry(self._config).build(solution.event_ids)
        )
        actor_order = self._build_actor_order(solution)
        bars = self._build_bars(solution)
        return GanttViewModel(
            bars=bars,
            actor_order=actor_order,
            color_map=color_map,
            timeline_start=solution.timeline_start,
            timeline_end=solution.timeline_end,
        )

    def _build_actor_order(self, solution):
        if self._sort_actors == "load":
            from collections import Counter

            counts = Counter(a.actor_id for a in solution.assignments)
            return [aid for aid, _ in counts.most_common()]
        return sorted(solution.actor_ids)

    def _build_bars(self, solution):
        if not self._merge_bars:
            return [
                GanttBar(
                    actor_id=a.actor_id,
                    event_id=a.event_id,
                    start=a.start,
                    end=a.end,
                    label=a.event_id,
                )
                for a in solution.assignments
            ]
        bars = []
        sorted_a = sorted(solution.assignments, key=lambda a: (a.actor_id, a.event_id, a.start))
        for (actor_id, event_id), group in groupby(
            sorted_a, key=lambda a: (a.actor_id, a.event_id)
        ):
            bars.extend(self._merge_group(actor_id, event_id, list(group)))
        return bars

    def _merge_group(self, actor_id, event_id, assignments):
        merged = []
        assignments = sorted(assignments, key=lambda a: a.start)
        cs, ce = assignments[0].start, assignments[0].end
        for a in assignments[1:]:
            if a.start <= ce:
                ce = max(ce, a.end)
            else:
                merged.append(
                    GanttBar(actor_id=actor_id, event_id=event_id, start=cs, end=ce, label=event_id)
                )
                cs, ce = a.start, a.end
        merged.append(
            GanttBar(actor_id=actor_id, event_id=event_id, start=cs, end=ce, label=event_id)
        )
        return merged
