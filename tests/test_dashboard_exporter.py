import plotly.graph_objects as go
import pytest

from sched_viz.config import VisConfig
from sched_viz.export.dashboard import DashboardExporter, PLOTLY_CDN_URL


@pytest.fixture
def exporter() -> DashboardExporter:
    # CDN mode keeps unit-test strings small. Inline behavior has its own test.
    return DashboardExporter(VisConfig(), plotly_js="cdn")


@pytest.fixture
def figure() -> go.Figure:
    return go.Figure(go.Bar(x=[1], y=[2], name="Sample"))


def test_rejects_empty_dashboard(exporter):
    with pytest.raises(ValueError, match="at least one figure"):
        exporter.build_html([], "Empty")


def test_escapes_title_and_label(exporter, figure):
    html = exporter.build_html(
        [("<b>unsafe label</b>", figure)],
        "<script>unsafe title</script>",
    )

    assert "&lt;b&gt;unsafe label&lt;/b&gt;" in html
    assert "<b>unsafe label</b>" not in html
    assert "&lt;script&gt;unsafe title&lt;/script&gt;" in html
    assert "<script>unsafe title</script>" not in html


def test_first_tab_is_active(exporter, figure):
    html = exporter.build_html(
        [("One", figure), ("Two", figure)],
        "Dashboard",
    )

    assert html.count('class="tab-btn active"') == 1
    assert html.count('class="tab-pane active"') == 1


def test_contains_one_plot_per_figure(exporter, figure):
    html = exporter.build_html(
        [("One", figure), ("Two", figure)],
        "Dashboard",
    )

    assert html.count("Plotly.newPlot") == 2


def test_export_writes_utf8_file(exporter, figure, tmp_path):
    output = tmp_path / "dashboard.html"

    exporter.export(output, [("Duración", figure)], "Planificación")

    html = output.read_text(encoding="utf-8")
    assert "Duración" in html
    assert "Planificación" in html


def test_export_creates_parent_directories(exporter, figure, tmp_path):
    output = tmp_path / "nested" / "dashboard.html"

    exporter.export(output, [("Gantt", figure)], "Dashboard")

    assert output.exists()


def test_serializes_each_figure_once(exporter, figure, monkeypatch):
    calls = []

    def fake_to_html(received, **kwargs):
        calls.append((received, kwargs))
        return "<div>plot</div>"

    monkeypatch.setattr(
        "sched_viz.export.dashboard.pio.to_html",
        fake_to_html,
    )

    exporter.build_html(
        [("One", figure), ("Two", figure)],
        "Dashboard",
    )

    assert len(calls) == 2
    assert all(call[1]["include_plotlyjs"] is False for call in calls)


def test_inline_mode_embeds_plotly(figure):
    exporter = DashboardExporter(VisConfig(), plotly_js="inline")

    html = exporter.build_html([("Gantt", figure)], "Dashboard")

    # The bundled Plotly source may contain CDN URLs as data or defaults.
    # What matters is that the document does not load Plotly externally.
    assert f'<script src="{PLOTLY_CDN_URL}"></script>' not in html
    assert "plotly.js" in html.lower()


def test_cdn_mode_references_external_plotly(figure):
    exporter = DashboardExporter(VisConfig(), plotly_js="cdn")

    html = exporter.build_html([("Gantt", figure)], "Dashboard")

    assert f'<script src="{PLOTLY_CDN_URL}"></script>' in html


def test_rejects_unknown_plotly_mode():
    with pytest.raises(ValueError, match="plotly_js"):
        DashboardExporter(VisConfig(), plotly_js="invalid")
