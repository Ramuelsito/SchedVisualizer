# sched-viz

Domain-agnostic scheduling visualizations built with Plotly.

`sched-viz` converts assignments on a numerical timeline into interactive Gantt, heatmap, utilization, and duration charts. Actors and events are opaque identifiers, so the same API can represent machines and jobs, interviewers and interviews, or other scheduling domains.

## Features

- Pydantic validation at the input boundary.
- Typed domain models independent of Plotly.
- Separate transform and renderer layers.
- Fluent loading and filtering API.
- Extensible chart registry based on a structural `Chart` protocol.
- Shared event colors across visualizations.
- Tabbed HTML dashboards with inline or CDN-backed Plotly JavaScript.
- Optional PNG, SVG, and PDF export through Kaleido.

## Installation

The project requires Python 3.11 or newer.

```bash
python -m pip install -e .
```

For static image export:

```bash
python -m pip install -e ".[export]"
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Quick start

```python
from sched_viz import VisualizationEngine


data = {
    "assignments": [
        {"actor_id": "machine-1", "event_id": "job-1", "start": 0, "duration": 3},
        {"actor_id": "machine-1", "event_id": "job-2", "start": 4, "duration": 2},
        {"actor_id": "machine-2", "event_id": "job-1", "start": 1, "duration": 3},
    ],
    "metadata": {"run_id": "example-1"},
}

engine = VisualizationEngine().from_dict(data)
figure = engine.gantt(sort_actors="alpha")
figure.show()
```

The engine also loads JSON:

```python
engine = VisualizationEngine().from_json("solution.json")
```

## Input format

Each assignment requires:

| Field | Type | Constraint |
|---|---|---|
| `actor_id` | `str` | Non-blank; surrounding whitespace is removed |
| `event_id` | `str` | Non-blank; surrounding whitespace is removed |
| `start` | `int` | Greater than or equal to zero |
| `duration` | `int` | Greater than or equal to one |

Optional fields are `participant_id`, assignment `metadata`, and solution `metadata`. `participant_id` is deliberately excluded from chart view models and hover data.

## Charts

```python
gantt = engine.gantt(merge_bars=True, sort_actors="load")
heatmap = engine.heatmap(bucket_size="auto", metric="occupancy")
utilization = engine.utilization()
durations = engine.duration_distribution()
```

Every chart is also available through the extension-oriented API:

```python
figure = engine.render("heatmap", metric="events", bucket_size=5)
```

Unknown charts and unknown chart options fail with explicit errors.

## Filtering

Filtering returns the same engine for fluent use but replaces its current solution with a filtered copy:

```python
figure = (
    VisualizationEngine()
    .from_dict(data)
    .filter(actors=["machine-1"], time_range=(0, 10))
    .gantt()
)
```

Available filters are `actors`, `events`, `time_range`, and `top_actors`.

## Dashboard export

```python
engine.export_dashboard(
    "output/report.html",
    charts=[
        {"type": "gantt", "sort_actors": "load"},
        {"type": "heatmap", "metric": "occupancy"},
        "utilization",
        "duration",
    ],
    title="Scheduling report",
)
```

The default `DashboardExporter` embeds Plotly JavaScript and produces a self-contained file that works offline. This makes the HTML several megabytes larger.

To produce a smaller file that loads Plotly from a CDN, inject a configured exporter:

```python
from sched_viz import VisualizationEngine, VisConfig
from sched_viz.export import DashboardExporter


config = VisConfig()
engine = VisualizationEngine(
    config=config,
    dashboard_exporter=DashboardExporter(config, plotly_js="cdn"),
).from_dict(data)
engine.export_dashboard("output/report.html")
```

CDN mode requires network access when the dashboard is opened.

## Static export

With the `export` extra installed:

```python
figure = engine.gantt()
engine.export(figure, "output/gantt.png", fmt="png", scale=2)
```

HTML figure export does not require Kaleido:

```python
engine.export(figure, "output/gantt.html", fmt="html")
```

## Custom charts and Dependency Inversion

`VisualizationEngine` does not import concrete transforms or renderers. It asks an injected `ChartRegistry` for an object implementing the `Chart` protocol.

```python
import plotly.graph_objects as go

from sched_viz import VisualizationEngine
from sched_viz.charts import ChartRegistry


class AssignmentCountChart:
    name = "assignment-count"
    label = "Assignment count"

    def render(self, solution, context, **options):
        if options:
            raise TypeError(f"Unknown options: {sorted(options)}")
        return go.Figure(
            go.Indicator(mode="number", value=len(solution.assignments))
        )


registry = ChartRegistry([AssignmentCountChart()])
engine = VisualizationEngine(chart_registry=registry).from_dict(data)
figure = engine.render("assignment-count")
```

Built-in implementations are assembled in `sched_viz.application`. This is the composition root: it is the intentional place where abstractions are connected to concrete classes. No DI framework is needed.

## Architecture

```text
dict / JSON
    ↓
Pydantic input schema
    ↓
Domain models
    ↓
Solution filters
    ↓
Chart registry → Chart adapter
                     ├── Transformer → View model
                     └── Renderer    → Plotly Figure
    ↓
Dashboard output port → DashboardExporter → HTML
```

- `schema/` validates external data and maps it into domain objects.
- `domain/` represents assignments and scheduling operations.
- `transforms/` computes chart-specific view models.
- `renderers/` converts view models into Plotly figures.
- `charts/` composes transformer/renderer pairs behind the `Chart` protocol.
- `export/` owns dashboard serialization and file output.
- `engine.py` is the public facade and orchestrator.

## Examples

```bash
python examples/example_gantt.py
python examples/full_dashboard.py
python examples/parallel_machines_demo.py
```

Generated files are written under `output/`, which is intentionally excluded from Git.

## Development

Run the test suite:

```bash
python -m pytest
```

Run all local quality checks:

```bash
python -m pytest --cov=sched_viz --cov-report=term-missing
ruff check .
mypy -p sched_viz
python -m build
python -m twine check dist/*
```

GitHub Actions runs tests, critical Ruff checks, type checking, and package validation on Python 3.11 and 3.12. Formatting remains a local migration step until the existing codebase has been formatted in a dedicated commit.

## Current limitations

- The project is alpha and its public API can still evolve.
- Actor assignments are not rejected when they overlap.
- Utilization currently sums assignment durations and clamps the ratio at 100%; overlapping assignments can therefore hide excess load.
- Static image export depends on the Plotly/Kaleido environment.
- Very large visualizations are initially capped by renderer viewport settings unless `force_full=True` is used.

## License

MIT, as declared in `pyproject.toml`.
