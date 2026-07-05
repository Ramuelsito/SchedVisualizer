import plotly.graph_objects as go

from sched_viz.charts.registry import ChartRegistry
from sched_viz import VisualizationEngine


class RecordingChart:
    name = "recording"
    label = "Recording"

    def __init__(self) -> None:
        self.calls = []

    def render(self, solution, context, **options):
        self.calls.append((solution, context, options))
        return go.Figure()


def test_engine_renders_an_injected_chart():
    chart = RecordingChart()
    engine = VisualizationEngine(
        chart_registry=ChartRegistry([chart]),
    ).from_dict(
        {
            "assignments": [
                {
                    "actor_id": "A1",
                    "event_id": "E1",
                    "start": 0,
                    "duration": 1,
                }
            ]
        }
    )

    figure = engine.render("recording", sample_option=True)

    assert isinstance(figure, go.Figure)
    assert chart.calls[0][2] == {"sample_option": True}
