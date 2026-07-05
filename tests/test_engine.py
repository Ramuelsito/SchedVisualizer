import plotly.graph_objects as go
import pytest

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


class RecordingDashboardExporter:
    def __init__(self) -> None:
        self.calls = []

    def export(self, path, figures, title):
        self.calls.append({"path": path, "figures": figures, "title": title})


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


def test_export_dashboard_delegates_to_injected_exporter(tmp_path):
    exporter = RecordingDashboardExporter()
    engine = VisualizationEngine(dashboard_exporter=exporter).from_dict(
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

    destination = tmp_path / "dashboard.html"
    engine.export_dashboard(destination, charts=["gantt"], title="Injected exporter")

    assert len(exporter.calls) == 1
    assert exporter.calls[0]["path"] == destination
    assert exporter.calls[0]["title"] == "Injected exporter"
    assert exporter.calls[0]["figures"][0][0] == "Gantt"


def test_from_json_loads_solution(tmp_path):
    source = tmp_path / "solution.json"
    source.write_text(
        '{"assignments": [{"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 1}]}',
        encoding="utf-8",
    )

    figure = VisualizationEngine().from_json(source).gantt()

    assert isinstance(figure, go.Figure)


def test_dashboard_spec_requires_type():
    engine = VisualizationEngine().from_dict(
        {"assignments": [{"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 1}]}
    )

    with pytest.raises(ValueError, match="requires a 'type'"):
        engine.export_dashboard("unused.html", charts=[{}])


def test_render_rejects_unknown_chart():
    engine = VisualizationEngine().from_dict(
        {"assignments": [{"actor_id": "A1", "event_id": "E1", "start": 0, "duration": 1}]}
    )

    with pytest.raises(ValueError, match="Unknown chart"):
        engine.render("missing")
