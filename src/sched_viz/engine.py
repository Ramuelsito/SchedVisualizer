from __future__ import annotations
import json
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio
from .config import VisConfig
from .core.color_registry import ColorRegistry
from .domain.solution import Solution
from .renderers.gantt_renderer import GanttRenderer
from .renderers.heatmap_renderer import HeatmapRenderer
from .renderers.utilization_renderer import UtilizationRenderer
from .renderers.duration_renderer import DurationRenderer
from .schema.input_schema import SolutionInput
from .transforms.gantt_transform import GanttTransformer
from .transforms.heatmap_transform import HeatmapTransformer
from .transforms.utilization_transform import UtilizationTransformer
from .transforms.duration_transform import DurationTransformer


class VisualizationEngine:
    """Fluent API for loading, filtering, and rendering scheduling solutions.

    Quick start::

        from sched_viz import VisualizationEngine

        fig = VisualizationEngine().from_dict(data).gantt()
        fig.show()

        # Export a full dashboard
        VisualizationEngine().from_dict(data).export_dashboard("report.html", charts=[
            {"type": "gantt", "sort_actors": "load"},
            {"type": "heatmap", "metric": "assignments", "bucket_size": 10},
            "utilization",
            "duration",
        ])
    """

    def __init__(self, config: VisConfig | None = None) -> None:
        self._config = config or VisConfig()
        self._solution: Solution | None = None
        self._color_registry = ColorRegistry(self._config)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def from_dict(self, data: dict) -> "VisualizationEngine":
        """Load a solution from a plain Python dict."""
        self._solution = SolutionInput.model_validate(data).to_domain()
        return self

    def from_json(self, path: str | Path) -> "VisualizationEngine":
        """Load a solution from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return self.from_dict(data)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter(self, actors=None, events=None, time_range=None, top_actors=None) -> "VisualizationEngine":
        """Chain filters. Returns self for fluent chaining."""
        self._require_solution()
        s = self._solution
        if actors is not None:     s = s.filter_by_actors(actors)
        if events is not None:     s = s.filter_by_events(events)
        if time_range is not None: s = s.filter_by_time_range(*time_range)
        if top_actors is not None: s = s.top_actors_by_load(top_actors)
        self._solution = s
        return self

    # ------------------------------------------------------------------
    # Color map (shared across all renderers)
    # ------------------------------------------------------------------

    def _build_color_map(self) -> dict[str, str]:
        return self._color_registry.build(self._solution.event_ids)

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def gantt(self, merge_bars=True, sort_actors="alpha", force_full=False) -> go.Figure:
        """Render a Gantt chart.

        Args:
            merge_bars:  Merge contiguous same-event bars. Default True.
            sort_actors: "alpha" (default) or "load".
            force_full:  Disable viewport cap for large solutions.
        """
        self._require_solution()
        color_map = self._build_color_map()
        vm = GanttTransformer(config=self._config, merge_bars=merge_bars,
                              sort_actors=sort_actors, color_map=color_map).transform(self._solution)
        return GanttRenderer(config=self._config).render(vm, force_full=force_full)

    def utilization(self, force_full=False) -> go.Figure:
        """Render a per-actor utilization bar chart."""
        self._require_solution()
        color_map = self._build_color_map()
        vm = UtilizationTransformer().transform(self._solution)
        return UtilizationRenderer(config=self._config).render(vm, force_full=force_full, color_map=color_map)

    def heatmap(self, bucket_size="auto", sort_actors="alpha", metric="occupancy", force_full=False) -> go.Figure:
        """Render a load heatmap (actors x time buckets).

        Args:
            bucket_size: Timeline units per bucket. "auto" targets ~30 columns.
            sort_actors: "alpha" or "load".
            metric:      "occupancy" | "assignments" | "events".
            force_full:  Disable viewport cap.
        """
        self._require_solution()
        color_map = self._build_color_map()
        vm = HeatmapTransformer(bucket_size=bucket_size, sort_actors=sort_actors,
                                metric=metric).transform(self._solution)
        return HeatmapRenderer(config=self._config).render(vm, force_full=force_full, color_map=color_map)

    def duration_distribution(self) -> go.Figure:
        """Render assignment duration distribution histogram by event."""
        self._require_solution()
        color_map = self._build_color_map()
        vm = DurationTransformer().transform(self._solution)
        return DurationRenderer(config=self._config).render(vm, color_map=color_map)

    # ------------------------------------------------------------------
    # Dashboard export
    # ------------------------------------------------------------------

    def export_dashboard(self, path: str | Path, charts: list | None = None,
                         title: str = "Scheduling Solution Dashboard") -> None:
        """Export charts as a single self-contained HTML file with tabs.

        Each entry in ``charts`` can be:

        * A **string** — chart name with default parameters.
        * A **dict** — ``{"type": "<name>", **kwargs}`` for custom parameters.

        Available chart types:

        * ``"gantt"``        — kwargs: ``merge_bars``, ``sort_actors``, ``force_full``
        * ``"utilization"``  — kwargs: ``force_full``
        * ``"heatmap"``      — kwargs: ``bucket_size``, ``sort_actors``, ``metric``, ``force_full``
        * ``"duration"``     — no kwargs

        Example::

            viz.export_dashboard("report.html", charts=[
                {"type": "gantt", "sort_actors": "load"},
                {"type": "heatmap", "metric": "assignments", "bucket_size": 10},
                "utilization",
                "duration",
            ])
        """
        self._require_solution()
        _renderers = {"gantt": self.gantt, "utilization": self.utilization,
                      "heatmap": self.heatmap, "duration": self.duration_distribution}
        _labels = {"gantt": "Gantt", "utilization": "Utilization",
                   "heatmap": "Heatmap", "duration": "Duration"}
        charts = charts or list(_renderers.keys())
        figures = []
        for spec in charts:
            if isinstance(spec, str):
                chart_type, kwargs = spec, {}
            elif isinstance(spec, dict):
                spec = dict(spec)
                chart_type = spec.pop("type")
                kwargs = spec
            else:
                raise ValueError(f"Chart spec must be str or dict, got {type(spec)}")
            if chart_type not in _renderers:
                raise ValueError(f"Unknown chart: {chart_type!r}. Available: {list(_renderers)}")
            label = _labels[chart_type]
            if kwargs:
                label += " (" + ", ".join(f"{k}={v}" for k, v in kwargs.items()) + ")"
            figures.append((label, _renderers[chart_type](**kwargs)))
        Path(path).write_text(_build_tabbed_html(figures, title=title, config=self._config), encoding="utf-8")

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def show(self, fig: go.Figure) -> None:
        """Display figure in browser or notebook."""
        fig.show()

    def export(self, fig: go.Figure, path: str | Path, fmt: str = "png", scale: float = 2.0) -> None:
        """Export a single figure to PNG, PDF, SVG, or HTML."""
        path = Path(path)
        if fmt == "html": fig.write_html(str(path))
        else: fig.write_image(str(path), format=fmt, scale=scale)

    def _require_solution(self):
        if self._solution is None:
            raise RuntimeError("No solution loaded. Call from_dict() or from_json() first.")


def _build_tabbed_html(figures, title, config):
    bg, surf, txt, txt2, grid, acc, font = (
        config.background_color, config.surface_color, config.text_primary,
        config.text_secondary, config.grid_color, config.event_palette[0], config.font_family
    )
    tab_buttons = ""
    tab_contents = ""
    for i, (name, fig) in enumerate(figures):
        active = "active" if i == 0 else ""
        chart_html = pio.to_html(fig, full_html=False, include_plotlyjs=False)
        tab_buttons += f'''
        <button class="tab-btn {active}" onclick="showTab('tab-{i}', this)">{name}</button>'''
        tab_contents += f'''
        <div id="tab-{i}" class="tab-pane {active}">{chart_html}</div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:{bg};color:{txt};font-family:{font};min-height:100vh}}
  header{{background:{surf};border-bottom:1px solid {grid};padding:18px 32px;display:flex;align-items:center;gap:12px}}
  header h1{{font-size:17px;font-weight:600;letter-spacing:-0.3px}}
  header span{{font-size:12px;color:{txt2};background:{bg};border:1px solid {grid};border-radius:4px;padding:2px 8px}}
  .tab-bar{{background:{surf};border-bottom:1px solid {grid};padding:0 32px;display:flex;gap:4px;flex-wrap:wrap}}
  .tab-btn{{background:none;border:none;border-bottom:2px solid transparent;color:{txt2};cursor:pointer;font-family:{font};font-size:13px;padding:12px 16px;transition:color .15s,border-color .15s;white-space:nowrap}}
  .tab-btn:hover{{color:{txt}}}
  .tab-btn.active{{color:{acc};border-bottom-color:{acc};font-weight:500}}
  .tab-pane{{display:none;padding:24px 32px}}
  .tab-pane.active{{display:block}}
</style>
</head>
<body>
<header><h1>{title}</h1><span>sched_viz</span></header>
<nav class="tab-bar">{tab_buttons}</nav>
<main>{tab_contents}</main>
<script>
  function showTab(id,btn){{
    document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    btn.classList.add('active');
  }}
</script>
</body>
</html>"""
