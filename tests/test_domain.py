"""Tests for domain models (Assignment, Solution) and their invariants."""

import pytest
from sched_viz.domain.models import Actor, Assignment, Event
from sched_viz.domain.solution import Solution


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_assignment(actor="A1", event="E1", start=0, duration=2) -> Assignment:
    return Assignment(actor_id=actor, event_id=event, start=start, duration=duration)

def make_solution(*assignments) -> Solution:
    return Solution(assignments=list(assignments))


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class TestAssignment:
    def test_end_is_start_plus_duration(self):
        a = make_assignment(start=3, duration=4)
        assert a.end == 7

    def test_rejects_blank_actor_id(self):
        with pytest.raises(ValueError, match="actor_id"):
            Assignment(actor_id="  ", event_id="E1", start=0, duration=1)

    def test_rejects_blank_event_id(self):
        with pytest.raises(ValueError, match="event_id"):
            Assignment(actor_id="A1", event_id="", start=0, duration=1)

    def test_rejects_negative_start(self):
        with pytest.raises(ValueError, match="start"):
            Assignment(actor_id="A1", event_id="E1", start=-1, duration=1)

    def test_rejects_zero_duration(self):
        with pytest.raises(ValueError, match="duration"):
            Assignment(actor_id="A1", event_id="E1", start=0, duration=0)

    def test_is_hashable(self):
        a = make_assignment()
        assert hash(a) is not None
        s = {a}
        assert a in s

    def test_participant_id_not_in_hash(self):
        """participant_id is opaque and must not affect equality/hashing."""
        a1 = Assignment(actor_id="A1", event_id="E1", start=0, duration=2, participant_id="P1")
        a2 = Assignment(actor_id="A1", event_id="E1", start=0, duration=2, participant_id="P2")
        assert a1 == a2


# ---------------------------------------------------------------------------
# Solution — properties
# ---------------------------------------------------------------------------

class TestSolutionProperties:
    def test_actor_ids(self):
        s = make_solution(
            make_assignment(actor="A1"),
            make_assignment(actor="A2"),
            make_assignment(actor="A1"),
        )
        assert s.actor_ids == {"A1", "A2"}

    def test_event_ids(self):
        s = make_solution(
            make_assignment(event="E1"),
            make_assignment(event="E2"),
        )
        assert s.event_ids == {"E1", "E2"}

    def test_timeline_start(self):
        s = make_solution(
            make_assignment(start=3, duration=2),
            make_assignment(start=1, duration=2),
        )
        assert s.timeline_start == 1

    def test_timeline_end(self):
        s = make_solution(
            make_assignment(start=0, duration=5),
            make_assignment(start=3, duration=4),
        )
        assert s.timeline_end == 7  # max(0+5, 3+4)

    def test_timeline_length(self):
        s = make_solution(make_assignment(start=2, duration=3))
        assert s.timeline_length == 3  # end(5) - start(2)

    def test_len(self):
        s = make_solution(make_assignment(), make_assignment())
        assert len(s) == 2

    def test_rejects_empty_assignments(self):
        with pytest.raises(ValueError):
            Solution(assignments=[])


# ---------------------------------------------------------------------------
# Solution — filters
# ---------------------------------------------------------------------------

class TestSolutionFilters:
    def setup_method(self):
        self.solution = make_solution(
            Assignment("A1", "E1", 0,  3),
            Assignment("A1", "E2", 5,  2),
            Assignment("A2", "E1", 1,  4),
            Assignment("A2", "E3", 8,  2),
            Assignment("A3", "E2", 2,  5),
        )

    def test_filter_by_actors(self):
        filtered = self.solution.filter_by_actors(["A1"])
        assert filtered.actor_ids == {"A1"}
        assert len(filtered) == 2

    def test_filter_by_actors_multiple(self):
        filtered = self.solution.filter_by_actors(["A1", "A3"])
        assert filtered.actor_ids == {"A1", "A3"}

    def test_filter_by_events(self):
        filtered = self.solution.filter_by_events(["E1"])
        assert filtered.event_ids == {"E1"}
        assert all(a.event_id == "E1" for a in filtered.assignments)

    def test_filter_by_time_range_overlap(self):
        # window [4, 7): should catch A1/E2(5,7) and A3/E2(2,7)
        filtered = self.solution.filter_by_time_range(4, 7)
        starts = {a.start for a in filtered.assignments}
        assert 5 in starts  # A1/E2 starts at 5, ends at 7 → overlaps [4,7)
        assert 2 in starts  # A3/E2 starts at 2, ends at 7 → overlaps [4,7)

    def test_filter_excludes_non_overlapping(self):
        # window [0, 1): only A1/E1 starts at 0 (end=3 > 0), overlaps
        filtered = self.solution.filter_by_time_range(0, 1)
        assert all(a.start < 1 and a.end > 0 for a in filtered.assignments)

    def test_filter_returns_new_instance(self):
        filtered = self.solution.filter_by_actors(["A1"])
        assert filtered is not self.solution

    def test_filter_does_not_mutate_original(self):
        original_len = len(self.solution)
        self.solution.filter_by_actors(["A1"])
        assert len(self.solution) == original_len

    def test_top_actors_by_load(self):
        top = self.solution.top_actors_by_load(2)
        assert len(top.actor_ids) <= 2

    def test_filter_empty_result_raises(self):
        with pytest.raises(ValueError):
            self.solution.filter_by_actors(["Z_nonexistent"])
