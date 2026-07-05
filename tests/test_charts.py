import pytest

from sched_viz.charts.base import RenderContext
from sched_viz.charts.duration import DurationChart
from sched_viz.charts.gantt import GanttChart
from sched_viz.charts.heatmap import HeatmapChart
from sched_viz.charts.utilization import UtilizationChart
from sched_viz.config import VisConfig
from sched_viz.domain.models import Assignment
from sched_viz.domain.solution import Solution


@pytest.fixture
def solution():
    return Solution(
        assignments=[
            Assignment("A2", "E1", 0, 2),
            Assignment("A1", "E2", 2, 3),
        ]
    )


@pytest.fixture
def context():
    return RenderContext(
        config=VisConfig(),
        color_map={"E1": "#111111", "E2": "#222222"},
    )


@pytest.mark.parametrize(
    "chart",
    [GanttChart(), HeatmapChart(), UtilizationChart(), DurationChart()],
)
def test_chart_returns_plotly_figure(chart, solution, context):
    figure = chart.render(solution, context)
    assert figure.data


@pytest.mark.parametrize(
    "chart",
    [GanttChart(), HeatmapChart(), UtilizationChart(), DurationChart()],
)
def test_chart_rejects_unknown_options(chart, solution, context):
    with pytest.raises(TypeError, match="unknown_option"):
        chart.render(solution, context, unknown_option=True)


def test_duration_uses_shared_event_colors(solution, context):
    figure = DurationChart().render(solution, context)
    colors = {trace.name: trace.marker.color for trace in figure.data}
    assert colors == {"E1": "#111111", "E2": "#222222"}
