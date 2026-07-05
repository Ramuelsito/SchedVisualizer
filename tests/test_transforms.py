"""Tests for the transform layer (GanttTransformer → GanttViewModel)."""

import pytest
from sched_viz.domain.models import Assignment
from sched_viz.domain.solution import Solution
from sched_viz.transforms.gantt_transform import GanttTransformer, GanttViewModel, GanttBar


def make_solution(*assignments) -> Solution:
    return Solution(assignments=list(assignments))


class TestGanttTransformer:

    def test_returns_gantt_view_model(self):
        s = make_solution(Assignment("A1", "E1", 0, 3))
        vm = GanttTransformer().transform(s)
        assert isinstance(vm, GanttViewModel)

    def test_color_map_contains_all_events(self):
        s = make_solution(
            Assignment("A1", "E1", 0, 2),
            Assignment("A2", "E2", 0, 2),
            Assignment("A3", "E3", 0, 2),
        )
        vm = GanttTransformer().transform(s)
        assert {"E1", "E2", "E3"} == set(vm.color_map.keys())

    def test_color_map_is_deterministic(self):
        """Same events → same colors across two separate transformer instances."""
        s = make_solution(
            Assignment("A1", "E1", 0, 2),
            Assignment("A2", "E2", 3, 2),
        )
        vm1 = GanttTransformer().transform(s)
        vm2 = GanttTransformer().transform(s)
        assert vm1.color_map == vm2.color_map

    def test_actor_order_alpha(self):
        s = make_solution(
            Assignment("C", "E1", 0, 1),
            Assignment("A", "E1", 0, 1),
            Assignment("B", "E1", 0, 1),
        )
        vm = GanttTransformer(sort_actors="alpha").transform(s)
        assert vm.actor_order == ["A", "B", "C"]

    def test_actor_order_by_load(self):
        s = make_solution(
            Assignment("A1", "E1", 0,  1),
            Assignment("A2", "E1", 0,  1),
            Assignment("A2", "E1", 2,  1),
            Assignment("A2", "E1", 4,  1),
        )
        vm = GanttTransformer(sort_actors="load").transform(s)
        assert vm.actor_order[0] == "A2"  # most assigned

    def test_timeline_bounds(self):
        s = make_solution(
            Assignment("A1", "E1", 2, 3),  # end=5
            Assignment("A2", "E1", 0, 4),  # end=4
        )
        vm = GanttTransformer().transform(s)
        assert vm.timeline_start == 0
        assert vm.timeline_end == 5

    def test_merge_bars_contiguous(self):
        """Two contiguous assignments of same actor+event → single bar."""
        s = make_solution(
            Assignment("A1", "E1", 0, 3),
            Assignment("A1", "E1", 3, 2),
        )
        vm = GanttTransformer(merge_bars=True).transform(s)
        actor_bars = [b for b in vm.bars if b.actor_id == "A1" and b.event_id == "E1"]
        assert len(actor_bars) == 1
        assert actor_bars[0].start == 0
        assert actor_bars[0].end == 5

    def test_merge_bars_with_gap_produces_two_bars(self):
        """Gap between assignments → two separate bars even with merge=True."""
        s = make_solution(
            Assignment("A1", "E1", 0, 3),
            Assignment("A1", "E1", 6, 2),  # gap at [3,6)
        )
        vm = GanttTransformer(merge_bars=True).transform(s)
        actor_bars = [b for b in vm.bars if b.actor_id == "A1" and b.event_id == "E1"]
        assert len(actor_bars) == 2

    def test_no_merge_preserves_all_bars(self):
        s = make_solution(
            Assignment("A1", "E1", 0, 3),
            Assignment("A1", "E1", 3, 2),
        )
        vm = GanttTransformer(merge_bars=False).transform(s)
        assert len(vm.bars) == 2

    def test_bars_have_correct_duration(self):
        s = make_solution(Assignment("A1", "E1", 4, 6))
        vm = GanttTransformer().transform(s)
        bar = vm.bars[0]
        assert bar.duration == 6
        assert bar.start == 4
        assert bar.end == 10
