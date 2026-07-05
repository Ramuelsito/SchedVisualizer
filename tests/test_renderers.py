"""Tests for the renderer layer (GanttRenderer → Plotly Figure)."""

import pytest
import plotly.graph_objects as go
from sched_viz.domain.models import Assignment
from sched_viz.domain.solution import Solution
from sched_viz.transforms.gantt_transform import GanttTransformer
from sched_viz.renderers.gantt_renderer import GanttRenderer
from sched_viz.config import VisConfig


def make_gantt_figure(assignments, config=None):
    s = Solution(assignments=assignments)
    vm = GanttTransformer(config=config).transform(s)
    return GanttRenderer(config=config).render(vm), vm


class TestGanttRenderer:
    def test_returns_plotly_figure(self):
        fig, _ = make_gantt_figure([Assignment("A1", "E1", 0, 3)])
        assert isinstance(fig, go.Figure)

    def test_one_trace_per_event(self):
        """Each unique event_id gets exactly one Bar trace (for legend grouping)."""
        assignments = [
            Assignment("A1", "E1", 0, 2),
            Assignment("A1", "E2", 4, 2),
            Assignment("A2", "E1", 1, 2),
        ]
        fig, _ = make_gantt_figure(assignments)
        trace_names = {t.name for t in fig.data}
        assert trace_names == {"E1", "E2"}

    def test_participant_id_not_in_hover(self):
        """participant_id must never appear in hover templates or customdata."""
        a = Assignment("A1", "E1", 0, 3, participant_id="SENSITIVE_P1")
        fig, _ = make_gantt_figure([a])
        for trace in fig.data:
            assert "SENSITIVE_P1" not in str(trace.hovertemplate or "")
            if trace.customdata is not None:
                for row in trace.customdata:
                    assert "SENSITIVE_P1" not in str(row)

    def test_figure_height_scales_with_actors(self):
        """More actors → taller figure."""
        few_actors = [Assignment(f"A{i}", "E1", 0, 2) for i in range(3)]
        many_actors = [Assignment(f"A{i}", "E1", 0, 2) for i in range(20)]

        fig_few, _ = make_gantt_figure(few_actors)
        fig_many, _ = make_gantt_figure(many_actors)
        assert fig_many.layout.height > fig_few.layout.height

    def test_custom_config_is_applied(self):
        cfg = VisConfig(background_color="#FFFFFF", fig_width=800)
        fig, _ = make_gantt_figure([Assignment("A1", "E1", 0, 2)], config=cfg)
        assert fig.layout.paper_bgcolor == "#FFFFFF"
        assert fig.layout.width == 800

    def test_xaxis_range_matches_timeline(self):
        assignments = [
            Assignment("A1", "E1", 5, 3),  # timeline_start = 5
            Assignment("A2", "E1", 10, 4),  # timeline_end   = 14
        ]
        fig, vm = make_gantt_figure(assignments)
        xrange = fig.layout.xaxis.range
        assert xrange[0] == vm.timeline_start
        assert xrange[1] == vm.timeline_end


class TestEngineEndToEnd:
    """Integration tests through the public engine API."""

    def test_from_dict_gantt(self):
        from sched_viz import VisualizationEngine

        data = {
            "assignments": [
                {"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 3},
                {"actor_id": "A2", "event_id": "E2", "start": 2, "duration": 4},
            ]
        }
        fig = VisualizationEngine().from_dict(data).gantt()
        assert isinstance(fig, go.Figure)

    def test_filter_then_gantt(self):
        from sched_viz import VisualizationEngine

        data = {
            "assignments": [
                {"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 2},
                {"actor_id": "A2", "event_id": "E1", "start": 0, "duration": 2},
                {"actor_id": "A3", "event_id": "E2", "start": 0, "duration": 2},
            ]
        }
        fig = VisualizationEngine().from_dict(data).filter(actors=["A1", "A2"]).gantt()
        trace_actors = {row[0] for t in fig.data for row in (t.customdata or [])}
        assert "A3" not in trace_actors

    def test_no_solution_raises(self):
        from sched_viz import VisualizationEngine

        with pytest.raises(RuntimeError, match="No solution loaded"):
            VisualizationEngine().gantt()
