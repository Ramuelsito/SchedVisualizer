"""Focused tests for the non-Gantt transforms and renderers."""

import pytest

from sched_viz.domain.models import Assignment
from sched_viz.domain.solution import Solution
from sched_viz.renderers.heatmap_renderer import HeatmapRenderer
from sched_viz.renderers.utilization_renderer import UtilizationRenderer
from sched_viz.transforms.duration_transform import DurationTransformer
from sched_viz.transforms.heatmap_transform import HeatmapTransformer
from sched_viz.transforms.utilization_transform import UtilizationTransformer


def make_solution(*assignments: Assignment) -> Solution:
    return Solution(assignments=list(assignments))


class TestHeatmapTransformer:
    def test_rejects_unknown_metric(self):
        with pytest.raises(ValueError, match="Invalid metric"):
            HeatmapTransformer(metric="unknown")

    def test_assignment_crossing_buckets_is_counted_in_each_bucket(self):
        solution = make_solution(Assignment("A1", "E1", 0, 4))

        view_model = HeatmapTransformer(
            bucket_size=2,
            metric="assignments",
        ).transform(solution)

        assert view_model.z == [[1.0, 1.0]]
        assert view_model.bucket_labels == ["0", "2"]

    def test_events_metric_counts_distinct_events(self):
        solution = make_solution(
            Assignment("A1", "E1", 0, 1),
            Assignment("A1", "E1", 1, 1),
            Assignment("A1", "E2", 1, 1),
        )

        view_model = HeatmapTransformer(
            bucket_size=2,
            metric="events",
        ).transform(solution)

        assert view_model.z == [[2.0]]


class TestUtilizationTransformer:
    def test_calculates_actor_statistics(self):
        solution = make_solution(
            Assignment("A1", "E1", 0, 2),
            Assignment("A1", "E2", 2, 1),
            Assignment("A2", "E1", 0, 1),
        )

        view_model = UtilizationTransformer().transform(solution)

        by_actor = {actor.actor_id: actor for actor in view_model.actors}
        assert by_actor["A1"].assigned_duration == 3
        assert by_actor["A1"].n_assignments == 2
        assert by_actor["A1"].utilization == 1.0
        assert by_actor["A2"].utilization == pytest.approx(1 / 3)
        assert view_model.mean_utilization == pytest.approx(2 / 3)
        assert view_model.median_utilization == pytest.approx(2 / 3)


class TestDurationTransformer:
    def test_groups_durations_and_calculates_summary(self):
        solution = make_solution(
            Assignment("A1", "E1", 0, 2),
            Assignment("A2", "E1", 0, 4),
            Assignment("A3", "E2", 0, 3),
        )

        view_model = DurationTransformer().transform(solution)

        assert view_model.durations_by_event == {"E1": [2, 4], "E2": [3]}
        assert view_model.min_duration == 2
        assert view_model.max_duration == 4
        assert view_model.mean_duration == 3


class TestAdditionalRenderers:
    def test_heatmap_respects_actor_limit(self):
        solution = make_solution(*[Assignment(f"A{i}", "E1", 0, 1) for i in range(4)])
        view_model = HeatmapTransformer(bucket_size=1).transform(solution)

        limited = HeatmapRenderer(max_actors=2).render(view_model)
        full = HeatmapRenderer(max_actors=2).render(view_model, force_full=True)

        assert len(limited.data[0].y) == 2
        assert len(full.data[0].y) == 4

    def test_utilization_respects_actor_limit(self):
        solution = make_solution(*[Assignment(f"A{i}", "E1", 0, i + 1) for i in range(4)])
        view_model = UtilizationTransformer().transform(solution)

        limited = UtilizationRenderer(max_actors=2).render(view_model)
        full = UtilizationRenderer(max_actors=2).render(view_model, force_full=True)

        assert len(limited.data[0].y) == 2
        assert len(full.data[0].y) == 4
