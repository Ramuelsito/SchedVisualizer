# Refactoring plan: extensible chart architecture

## 1. Goal

Refactor `VisualizationEngine` so that it coordinates use cases but does not know how each chart is transformed or rendered. Adding a chart should require creating and registering a new chart implementation, not adding another method branch or import to the engine.

The target dependency direction is:

```text
Application / composition root
            |
            v
VisualizationEngine ---> ChartRegistry ---> Chart protocol
       |                                      ^
       |                                      |
       +---> DashboardExporter          concrete charts
                                             |
                                      transformer + renderer
```

This applies Dependency Inversion without introducing a DI framework. Dependencies are passed explicitly through constructors, which is enough for this project.

## 2. Current problems being addressed

### 2.1 The engine depends on every concrete chart

`src/sched_viz/engine.py` imports every transformer and renderer and constructs them inside `gantt()`, `heatmap()`, `utilization()`, and `duration_distribution()`.

Adding a chart currently requires modifying the engine in several places:

1. Add transformer and renderer imports.
2. Add a public method.
3. Add an entry to `_renderers` in `export_dashboard()`.
4. Add an entry to `_labels`.
5. Extend documentation and tests.

This does not make new charts impossible, but it means the engine is not closed for modification.

### 2.2 The engine has unrelated output responsibilities

The engine also parses dashboard specifications, renders an HTML template, serializes Plotly figures, and writes files. These concerns make `engine.py` harder to understand and test.

### 2.3 The existing transformer protocol is not an effective boundary

`transforms/base.py` declares `BaseTransformer`, but the engine still refers directly to concrete transformer classes. There is also no abstraction representing the complete operation needed by the engine: transform a `Solution` and render a figure.

Injecting transformers and renderers separately into the engine would expose too much chart-specific assembly. A higher-level `Chart` abstraction is the more useful dependency boundary.

## 3. Design decisions

### 3.1 Define a chart port

The engine needs only three facts about a chart:

- its stable name;
- its display label;
- how to produce a Plotly figure from a solution and options.

Use a `Protocol` so implementations do not need to inherit from a base class.

### 3.2 Keep transformers and renderers separate

The current transform/render split is useful and should remain:

- transformers contain scheduling and aggregation logic;
- renderers contain Plotly-specific presentation logic;
- a concrete chart adapter composes the correct pair.

The adapter is intentionally thin. It exists to hide construction details from the engine.

### 3.3 Use a registry, not conditionals

`ChartRegistry` maps chart names to `Chart` implementations. The engine asks the registry to render a named chart. It does not use `if`, `match`, or a dictionary of its own methods.

The registry is injected into the engine. A default registry is assembled outside the engine in a composition-root function.

Strictly speaking, registering a new built-in chart still changes the composition root. That is expected: the application must choose which implementations exist. The important point is that the stable engine and exporter do not change.

### 3.4 Preserve convenience methods

Methods such as `gantt()` are useful public API. They should remain as compatibility wrappers around the generic operation:

```python
def gantt(self, **options) -> go.Figure:
    return self.render("gantt", **options)
```

These wrappers mean a new chart is immediately available through `render("new-chart")` and dashboards without changing the engine. A named convenience method can be added later only if its usability value justifies expanding the public API.

### 3.5 Extract dashboard export

`DashboardExporter` should receive already-rendered, labelled figures. It should not know about `Solution`, transformers, renderers, or chart names.

This keeps dependencies narrow:

```text
Engine: chart selection and orchestration
Chart: transform + render composition
Exporter: figures -> HTML/file
```

## 4. Expected final structure

```text
src/sched_viz/
├── __init__.py
├── application.py                 # default dependency composition
├── charts/
│   ├── __init__.py
│   ├── base.py                    # Chart protocol and RenderContext
│   ├── registry.py                # ChartRegistry
│   ├── gantt.py                   # GanttChart adapter
│   ├── heatmap.py                 # HeatmapChart adapter
│   ├── utilization.py             # UtilizationChart adapter
│   └── duration.py                # DurationChart adapter
├── export/
│   ├── __init__.py
│   └── dashboard.py               # DashboardExporter
├── engine.py                      # stable facade/orchestrator
├── transforms/                    # unchanged calculation layer
└── renderers/                     # unchanged Plotly layer

tests/
├── test_chart_registry.py
├── test_charts.py
├── test_dashboard_exporter.py
└── test_engine.py
```

`application.py` is a composition root: the place where concrete dependencies are deliberately selected and connected. It is allowed to depend on concrete implementations.

## 5. Proposed code

The code below is the intended implementation, not code already applied to `src/`.

### 5.1 Chart abstraction

Create `src/sched_viz/charts/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import plotly.graph_objects as go

from ..config import VisConfig
from ..domain.solution import Solution


ChartOptions = Mapping[str, Any]


@dataclass(frozen=True)
class RenderContext:
    """Dependencies shared by charts during one render operation."""

    config: VisConfig
    color_map: Mapping[str, str]


class Chart(Protocol):
    """Application-facing port implemented by every chart type."""

    @property
    def name(self) -> str:
        ...

    @property
    def label(self) -> str:
        ...

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        ...
```

`RenderContext` prevents the method signature growing whenever a genuinely shared render dependency is introduced. It should contain dependencies, not arbitrary chart options.

### 5.2 Chart registry

Create `src/sched_viz/charts/registry.py`:

```python
from __future__ import annotations

from collections.abc import Iterable

from .base import Chart


class ChartRegistry:
    def __init__(self, charts: Iterable[Chart] = ()) -> None:
        self._charts: dict[str, Chart] = {}
        for chart in charts:
            self.register(chart)

    def register(self, chart: Chart) -> None:
        if chart.name in self._charts:
            raise ValueError(f"Chart already registered: {chart.name!r}")
        self._charts[chart.name] = chart

    def get(self, name: str) -> Chart:
        try:
            return self._charts[name]
        except KeyError as exc:
            available = ", ".join(self.names())
            raise ValueError(
                f"Unknown chart: {name!r}. Available: [{available}]"
            ) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(self._charts)
```

Duplicate registration should fail rather than silently replace behavior. If runtime replacement later becomes a real requirement, add an explicit `replace()` operation.

### 5.3 Concrete chart adapters

Create `src/sched_viz/charts/gantt.py`:

```python
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.gantt_renderer import GanttRenderer
from ..transforms.gantt_transform import GanttTransformer
from .base import RenderContext


class GanttChart:
    name = "gantt"
    label = "Gantt"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        merge_bars = options.pop("merge_bars", True)
        sort_actors = options.pop("sort_actors", "alpha")
        force_full = options.pop("force_full", False)
        _reject_unknown_options(self.name, options)

        view_model = GanttTransformer(
            config=context.config,
            merge_bars=merge_bars,
            sort_actors=sort_actors,
            color_map=dict(context.color_map),
        ).transform(solution)

        return GanttRenderer(config=context.config).render(
            view_model,
            force_full=force_full,
        )


def _reject_unknown_options(chart_name: str, options: dict[str, Any]) -> None:
    if options:
        names = ", ".join(sorted(options))
        raise TypeError(f"Unknown options for {chart_name!r}: {names}")
```

Do not copy `_reject_unknown_options` into every adapter. Put it in `charts/base.py` or `charts/options.py` and import it. It is shown beside `GanttChart` only to make the example self-contained.

Create `src/sched_viz/charts/heatmap.py`:

```python
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.heatmap_renderer import HeatmapRenderer
from ..transforms.heatmap_transform import HeatmapTransformer
from .base import RenderContext, reject_unknown_options


class HeatmapChart:
    name = "heatmap"
    label = "Heatmap"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        bucket_size = options.pop("bucket_size", "auto")
        sort_actors = options.pop("sort_actors", "alpha")
        metric = options.pop("metric", "occupancy")
        force_full = options.pop("force_full", False)
        reject_unknown_options(self.name, options)

        view_model = HeatmapTransformer(
            bucket_size=bucket_size,
            sort_actors=sort_actors,
            metric=metric,
        ).transform(solution)

        return HeatmapRenderer(config=context.config).render(
            view_model,
            force_full=force_full,
        )
```

Create `src/sched_viz/charts/utilization.py`:

```python
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.utilization_renderer import UtilizationRenderer
from ..transforms.utilization_transform import UtilizationTransformer
from .base import RenderContext, reject_unknown_options


class UtilizationChart:
    name = "utilization"
    label = "Utilization"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        force_full = options.pop("force_full", False)
        reject_unknown_options(self.name, options)

        view_model = UtilizationTransformer().transform(solution)
        return UtilizationRenderer(config=context.config).render(
            view_model,
            force_full=force_full,
        )
```

Create `src/sched_viz/charts/duration.py`:

```python
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.duration_renderer import DurationRenderer
from ..transforms.duration_transform import DurationTransformer
from .base import RenderContext, reject_unknown_options


class DurationChart:
    name = "duration"
    label = "Duration"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        reject_unknown_options(self.name, options)
        view_model = DurationTransformer().transform(solution)
        return DurationRenderer(config=context.config).render(
            view_model,
            color_map=dict(context.color_map),
        )
```

The heatmap and utilization renderers currently accept `color_map` but do not use it. Remove those parameters rather than carrying a misleading dependency forward. Duration and Gantt actually use the shared event colors.

### 5.4 Shared option validation

Add this to `src/sched_viz/charts/base.py`:

```python
def reject_unknown_options(chart_name: str, options: Mapping[str, Any]) -> None:
    if options:
        names = ", ".join(sorted(options))
        raise TypeError(f"Unknown options for {chart_name!r}: {names}")
```

Because adapters receive `**options`, explicit rejection is important. Otherwise a misspelling such as `sort_actor="load"` could be silently ignored.

### 5.5 Default composition root

Create `src/sched_viz/application.py`:

```python
from __future__ import annotations

from .charts.duration import DurationChart
from .charts.gantt import GanttChart
from .charts.heatmap import HeatmapChart
from .charts.registry import ChartRegistry
from .charts.utilization import UtilizationChart


def create_default_chart_registry() -> ChartRegistry:
    return ChartRegistry(
        [
            GanttChart(),
            HeatmapChart(),
            UtilizationChart(),
            DurationChart(),
        ]
    )
```

This is the only built-in location modified when a new default chart is added. The engine remains unchanged.

### 5.6 Dashboard exporter

Create `src/sched_viz/export/dashboard.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

from ..config import VisConfig


LabeledFigure = tuple[str, go.Figure]


class DashboardExporter:
    def __init__(self, config: VisConfig) -> None:
        self._config = config

    def export(
        self,
        path: str | Path,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> None:
        html = self.build_html(figures=figures, title=title)
        Path(path).write_text(html, encoding="utf-8")

    def build_html(
        self,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> str:
        if not figures:
            raise ValueError("Dashboard must contain at least one figure")

        safe_title = escape(title)
        buttons: list[str] = []
        panes: list[str] = []

        for index, (label, figure) in enumerate(figures):
            active = " active" if index == 0 else ""
            safe_label = escape(label)
            figure_html = pio.to_html(
                figure,
                full_html=False,
                include_plotlyjs=False,
            )
            buttons.append(
                f'<button class="tab-btn{active}" '
                f'onclick="showTab(\'tab-{index}\', this)">{safe_label}</button>'
            )
            panes.append(
                f'<div id="tab-{index}" class="tab-pane{active}">'
                f"{figure_html}</div>"
            )

        return self._template(
            title=safe_title,
            tab_buttons="".join(buttons),
            tab_contents="".join(panes),
        )

    def _template(self, title: str, tab_buttons: str, tab_contents: str) -> str:
        # Move the existing HTML/CSS/JavaScript from engine._build_tabbed_html
        # here. Interpolate only escaped text and trusted generated figure HTML.
        ...
```

When implementing `_template()`, move the current template rather than redesigning it in the same commit. Keeping behavior stable makes the structural refactor easier to review. A visual redesign can be a separate change.

The current template loads Plotly from a CDN while its docstring says the result is self-contained. Decide and test one policy:

- **Truly self-contained:** include Plotly JavaScript in the output. The file is larger but works offline.
- **CDN-backed:** retain the script URL and change the documentation to avoid claiming self-containment.

Do not mix this policy decision invisibly into the refactor.

### 5.7 Refactored engine

Replace concrete chart imports in `src/sched_viz/engine.py` with abstractions and injected dependencies. The important parts should become:

```python
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
from .export.dashboard import DashboardExporter
from .schema.input_schema import SolutionInput


class VisualizationEngine:
    def __init__(
        self,
        config: VisConfig | None = None,
        chart_registry: ChartRegistry | None = None,
        dashboard_exporter: DashboardExporter | None = None,
    ) -> None:
        self._config = config or VisConfig()
        self._solution: Solution | None = None
        self._color_registry = ColorRegistry(self._config)
        self._charts = chart_registry or create_default_chart_registry()
        self._dashboard_exporter = (
            dashboard_exporter or DashboardExporter(self._config)
        )

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
            raise ValueError(
                f"Chart spec must be str or dict, got {type(spec).__name__}"
            )

        chart = self._charts.get(chart_name)
        label = chart.label
        if options:
            option_label = ", ".join(
                f"{name}={value}" for name, value in options.items()
            )
            label = f"{label} ({option_label})"

        return label, self.render(chart_name, **options)

    def _require_solution(self) -> Solution:
        if self._solution is None:
            raise RuntimeError(
                "No solution loaded. Call from_dict() or from_json() first."
            )
        return self._solution
```

Keep the existing `show()` and `export()` methods during this refactor to avoid unnecessary API changes. They can be assessed separately after dashboard extraction.

Notice that `_require_solution()` now returns `Solution`. This removes repeated access to an optional attribute and gives type checkers a properly narrowed value.

### 5.8 Package exports

Create `src/sched_viz/charts/__init__.py`:

```python
from .base import Chart, RenderContext
from .registry import ChartRegistry

__all__ = ["Chart", "ChartRegistry", "RenderContext"]
```

Create `src/sched_viz/export/__init__.py`:

```python
from .dashboard import DashboardExporter

__all__ = ["DashboardExporter"]
```

Expose `ChartRegistry` from the top-level package only if custom chart registration is intended as a documented public extension point. Otherwise users can initially import it from `sched_viz.charts`.

## 6. Adding a future chart

Suppose a fragmentation chart is required.

1. Add `FragmentationTransformer` and its view model.
2. Add `FragmentationRenderer`.
3. Add a thin `FragmentationChart` implementing the `Chart` protocol.
4. Register it in `create_default_chart_registry()` if it should be built in.
5. Add focused tests.

No changes are needed in `VisualizationEngine`, `ChartRegistry`, or `DashboardExporter`.

A user-provided chart can be supplied without modifying library code:

```python
registry = create_default_chart_registry()
registry.register(MyCustomChart())

engine = VisualizationEngine(chart_registry=registry)
figure = engine.from_dict(data).render("my-custom-chart")
```

That is the practical Open/Closed benefit of the design.

## 7. Testing strategy

### 7.1 Preserve existing tests first

Before structural changes, run the current suite and record the baseline:

```bash
pytest
```

Do not change existing behavior merely to make the new design easier.

### 7.2 Registry unit tests

Add `tests/test_chart_registry.py`:

```python
import pytest

from sched_viz.charts.registry import ChartRegistry


class StubChart:
    def __init__(self, name: str) -> None:
        self.name = name
        self.label = name.title()


def test_returns_registered_chart():
    chart = StubChart("stub")
    registry = ChartRegistry([chart])
    assert registry.get("stub") is chart


def test_rejects_duplicate_names():
    registry = ChartRegistry([StubChart("stub")])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubChart("stub"))


def test_unknown_chart_lists_available_names():
    registry = ChartRegistry([StubChart("known")])
    with pytest.raises(ValueError, match="known"):
        registry.get("missing")
```

The stub does not need a working `render()` method in tests that never call it. Static type checking may require a complete fake if it is added later.

### 7.3 Engine Dependency Inversion test

Add `tests/test_engine.py`:

```python
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
```

This is the key architectural test: the engine works with an implementation it does not import or construct.

### 7.4 Concrete chart tests

Add focused adapter tests that verify:

- the transformer options reach the correct transformer behavior;
- renderer-only options such as `force_full` reach the renderer;
- unknown options fail clearly;
- duration and Gantt use shared colors;
- heatmap and utilization do not request an unused color map.

Do not duplicate all transformer and renderer tests at the adapter level. Adapter tests should verify wiring, while existing unit tests verify calculations and Plotly output.

### 7.5 Missing transform and renderer coverage

The current suite focuses mainly on Gantt. Add direct tests for:

- heatmap metrics and bucket boundaries;
- utilization mean and median;
- overlapping assignments and utilization clamping semantics;
- duration grouping and statistics;
- actor limits and `force_full` behavior in each renderer.

The utilization test should explicitly decide whether overlapping assignments are valid. Current code sums durations and clamps utilization to `1.0`, which hides overlap rather than reporting it.

### 7.6 Dashboard exporter tests

Use `tmp_path`; no mock filesystem is required:

```python
def test_export_writes_utf8_html(tmp_path, exporter, figure):
    output = tmp_path / "dashboard.html"
    exporter.export(output, [("Gantt", figure)], "Schedule")
    html = output.read_text(encoding="utf-8")
    assert "Schedule" in html
    assert "Gantt" in html
```

Also test:

- first tab is active;
- one button and pane exist per figure;
- empty figures are rejected;
- titles and labels are escaped;
- the chosen Plotly JavaScript policy;
- the engine delegates to an injected recording exporter.

### 7.7 Integration and compatibility tests

Retain or add tests for:

```python
VisualizationEngine().from_dict(data).gantt()
VisualizationEngine().from_dict(data).render("gantt")
VisualizationEngine().from_dict(data).export_dashboard(...)
```

Both Gantt calls should produce equivalent structural output.

## 8. Safe implementation sequence

Make small commits so each architectural decision is reviewable and reversible.

### Commit 1: characterization tests

- Add tests for all current engine chart methods.
- Add dashboard behavior tests around the current implementation.
- Add missing tests for invalid chart specifications.
- Run the suite and commit without production behavior changes.

Suggested message:

```text
test: characterize engine chart and dashboard behavior
```

### Commit 2: chart abstraction and registry

- Add `Chart`, `RenderContext`, and `ChartRegistry`.
- Add registry unit tests.
- Do not change the engine yet.

```text
feat: add chart extension interface and registry
```

### Commit 3: concrete chart adapters

- Add the four adapters.
- Add adapter wiring tests.
- Remove the unused `color_map` parameters from heatmap and utilization renderers.

```text
refactor: compose transforms and renderers as charts
```

### Commit 4: invert engine chart dependencies

- Add the default composition root.
- Inject `ChartRegistry` into the engine.
- Add generic `render()`.
- Convert existing convenience methods into wrappers.
- Replace dashboard chart dispatch with registry lookup.
- Confirm existing public behavior remains intact.

```text
refactor: make visualization engine depend on chart registry
```

### Commit 5: extract dashboard export

- Add `DashboardExporter`.
- Move HTML generation out of `engine.py`.
- Inject exporter into the engine.
- Add exporter and delegation tests.

```text
refactor: extract dashboard HTML exporter from engine
```

### Commit 6: documentation

- Populate `README.md` with the input format and primary API.
- Document `render(name, **options)`.
- Document custom chart registration.
- Correct the self-contained/CDN dashboard description.

```text
docs: describe chart extensions and dashboard export
```

## 9. Git workflow

Suggested branch:

```bash
git switch -c refactor/chart-dependency-inversion
```

Before each commit:

```bash
git status --short
git diff --check
pytest
```

Inspect staged changes before committing:

```bash
git diff --staged
```

Do not combine formatting of unrelated files with this refactor. Keeping commits focused makes review and `git bisect` more useful.

## 10. Costs and trade-offs

### Benefits

- The engine no longer imports concrete plots.
- New charts can be added without changing engine dispatch.
- Custom charts can be injected by library users.
- Transform/render separation remains intact.
- Dashboard HTML and file output become independently testable.
- Unit tests can use lightweight fake charts and exporters.

### Costs

- Four small adapter classes add indirection.
- `**options` sacrifices some static discoverability in the generic API.
- The default composition root still changes for a new built-in chart.
- More modules mean navigation overhead for a small codebase.

The convenience methods preserve typed, discoverable common operations, while `render()` supplies extensibility. If stronger option typing becomes important, introduce chart-specific option dataclasses later; it is not required for this refactor.

## 11. What not to do in this refactor

- Do not add a third-party DI container.
- Do not make every dataclass or utility injectable.
- Do not merge transformers and renderers into the engine-facing adapters.
- Do not redesign all Plotly layouts at the same time.
- Do not change domain filtering semantics in an architectural commit.
- Do not remove existing convenience methods.
- Do not treat the composition root's knowledge of concrete classes as a DIP violation; constructing the object graph is its responsibility.

## 12. Completion criteria

The refactor is complete when:

1. Existing public chart calls still work.
2. `VisualizationEngine.render(name, **options)` works for built-in and injected charts.
3. `engine.py` imports no concrete transformer or renderer.
4. Dashboard chart selection uses `ChartRegistry`.
5. Dashboard HTML generation and writing live outside the engine.
6. Duplicate and unknown chart names produce clear errors.
7. Unknown chart options produce clear errors.
8. Existing and new tests pass.
9. Adding a test-only custom chart requires no engine modification.
10. Documentation explains where concrete dependencies are composed.
