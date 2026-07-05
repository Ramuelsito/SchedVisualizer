from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from .application import create_default_chart_registry
from .charts.base import RenderContext
from .charts.registry import ChartRegistry
from .config import VisConfig
from .core.color_registry import ColorRegistry
from .domain.solution import Solution
from .export import DashboardOutput, DashboardExporter
from .schema.input_schema import SolutionInput


class VisualizationEngine:
    def __init__(
        self,
        config: VisConfig | None = None,
        chart_registry: ChartRegistry | None = None,
        dashboard_exporter: DashboardOutput | None = None,
    ) -> None:
        self._config = config or VisConfig()
        self._solution: Solution | None = None
        self._color_registry = ColorRegistry(self._config)
        self._charts = chart_registry or create_default_chart_registry()
        self._dashboard_exporter = dashboard_exporter or DashboardExporter(self._config)

    def from_dict(self, data: dict) -> "VisualizationEngine":
        self._solution = SolutionInput.model_validate(data).to_domain()
        return self

    def from_json(self, path: str | Path) -> "VisualizationEngine":
        with Path(path).open(encoding="utf-8") as source:
            return self.from_dict(json.load(source))

    def filter(
        self,
        actors=None,
        events=None,
        time_range=None,
        top_actors=None,
    ) -> "VisualizationEngine":
        """Filter the loaded solution by actors, events, time range, or top actors."""
        solution = self._require_solution()
        if actors is not None:
            solution = solution.filter_by_actors(actors)
        if events is not None:
            solution = solution.filter_by_events(events)
        if time_range is not None:
            solution = solution.filter_by_time_range(*time_range)
        if top_actors is not None:
            solution = solution.top_actors_by_load(top_actors)
        self._solution = solution
        return self

    def render(self, chart_name: str, **options: Any) -> go.Figure:
        """Render a chart by name with optional parameters."""
        solution = self._require_solution()
        chart = self._charts.get(chart_name)
        context = RenderContext(
            config=self._config,
            color_map=self._color_registry.build(solution.event_ids),
        )
        return chart.render(solution, context, **options)

    # Compatibility and discoverability helpers.
    def gantt(self, **options: Any) -> go.Figure:
        return self.render("gantt", **options)

    def heatmap(self, **options: Any) -> go.Figure:
        return self.render("heatmap", **options)

    def utilization(self, **options: Any) -> go.Figure:
        return self.render("utilization", **options)

    def duration_distribution(self, **options: Any) -> go.Figure:
        return self.render("duration", **options)

    def export_dashboard(
        self,
        path: str | Path,
        charts: list[str | dict[str, Any]] | None = None,
        title: str = "Scheduling Solution Dashboard",
    ) -> None:
        self._require_solution()
        chart_specs = charts or list(self._charts.names())
        figures = [self._render_dashboard_chart(spec) for spec in chart_specs]
        self._dashboard_exporter.export(path, figures, title)

    def _render_dashboard_chart(
        self,
        spec: str | dict[str, Any],
    ) -> tuple[str, go.Figure]:
        if isinstance(spec, str):
            chart_name = spec
            options: dict[str, Any] = {}
        elif isinstance(spec, dict):
            options = dict(spec)
            try:
                chart_name = options.pop("type")
            except KeyError as exc:
                raise ValueError("Chart specification requires a 'type'") from exc
        else:
            raise ValueError(f"Chart spec must be str or dict, got {type(spec).__name__}")

        chart = self._charts.get(chart_name)
        label = chart.label
        if options:
            option_label = ", ".join(f"{name}={value}" for name, value in options.items())
            label = f"{label} ({option_label})"

        return label, self.render(chart_name, **options)

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def show(self, fig: go.Figure) -> None:
        """Display figure in browser or notebook."""
        fig.show()

    def export(
        self,
        fig: go.Figure,
        path: str | Path,
        fmt: str = "png",
        scale: float = 2.0,
    ) -> None:
        """Export a single figure to PNG, PDF, SVG, or HTML."""
        path = Path(path)
        if fmt == "html":
            fig.write_html(str(path))
        else:
            fig.write_image(str(path), format=fmt, scale=scale)

    def _require_solution(self) -> Solution:
        if self._solution is None:
            raise RuntimeError("No solution loaded. Call from_dict() or from_json() first.")
        return self._solution
