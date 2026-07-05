"""Tests for the input schema layer (SolutionInput, AssignmentInput)."""

import pytest
from pydantic import ValidationError
from sched_viz.schema.input_schema import AssignmentInput, SolutionInput
from sched_viz.domain.solution import Solution


VALID_DATA = {
    "assignments": [
        {"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 3},
        {"actor_id": "A1", "event_id": "E2", "start": 5, "duration": 2},
        {"actor_id": "A2", "event_id": "E1", "start": 1, "duration": 4},
    ]
}


class TestAssignmentInput:
    def test_valid_assignment(self):
        a = AssignmentInput(actor_id="A1", event_id="E1", start=0, duration=2)
        assert a.actor_id == "A1"
        assert a.event_id == "E1"
        assert a.start == 0
        assert a.duration == 2

    def test_optional_participant_id(self):
        a = AssignmentInput(actor_id="A1", event_id="E1", start=0, duration=1)
        assert a.participant_id is None

        a2 = AssignmentInput(
            actor_id="A1", event_id="E1", start=0, duration=1, participant_id="P99"
        )
        assert a2.participant_id == "P99"

    def test_rejects_empty_actor_id(self):
        with pytest.raises(ValidationError):
            AssignmentInput(actor_id="", event_id="E1", start=0, duration=1)

    def test_rejects_empty_event_id(self):
        with pytest.raises(ValidationError):
            AssignmentInput(actor_id="A1", event_id="", start=0, duration=1)

    def test_rejects_whitespace_only_ids(self):
        with pytest.raises(ValidationError):
            AssignmentInput(actor_id="   ", event_id="E1", start=0, duration=1)

    def test_strips_identifier_whitespace(self):
        assignment = AssignmentInput(actor_id=" A1 ", event_id=" E1 ", start=0, duration=1)

        assert assignment.actor_id == "A1"
        assert assignment.event_id == "E1"

    def test_rejects_negative_start(self):
        with pytest.raises(ValidationError):
            AssignmentInput(actor_id="A1", event_id="E1", start=-1, duration=1)

    def test_rejects_zero_duration(self):
        with pytest.raises(ValidationError):
            AssignmentInput(actor_id="A1", event_id="E1", start=0, duration=0)

    def test_to_domain_produces_assignment(self):
        from sched_viz.domain.models import Assignment

        a = AssignmentInput(actor_id="A1", event_id="E1", start=2, duration=3)
        domain = a.to_domain()
        assert isinstance(domain, Assignment)
        assert domain.actor_id == "A1"
        assert domain.start == 2
        assert domain.end == 5


class TestSolutionInput:
    def test_valid_solution(self):
        sol = SolutionInput.model_validate(VALID_DATA).to_domain()
        assert isinstance(sol, Solution)
        assert len(sol) == 3

    def test_metadata_defaults_to_empty_dict(self):
        sol = SolutionInput.model_validate(VALID_DATA)
        assert sol.metadata == {}

    def test_metadata_is_preserved(self):
        data = {**VALID_DATA, "metadata": {"run_id": "test-42"}}
        sol = SolutionInput.model_validate(data).to_domain()
        assert sol.metadata["run_id"] == "test-42"

    def test_rejects_empty_assignments(self):
        with pytest.raises(ValidationError):
            SolutionInput.model_validate({"assignments": []})

    def test_gaps_between_assignments_are_allowed(self):
        """Actors can have idle time — gaps must NOT be rejected."""
        data = {
            "assignments": [
                {"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 2},
                {"actor_id": "A1", "event_id": "E1", "start": 10, "duration": 2},  # gap of 8
            ]
        }
        sol = SolutionInput.model_validate(data).to_domain()
        assert len(sol) == 2

    def test_overlapping_assignments_for_different_actors_are_allowed(self):
        data = {
            "assignments": [
                {"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 5},
                {"actor_id": "A2", "event_id": "E1", "start": 2, "duration": 5},
            ]
        }
        sol = SolutionInput.model_validate(data).to_domain()
        assert len(sol) == 2
