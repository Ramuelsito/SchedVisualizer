## 1. Project purpose

  sched-viz is a domain-agnostic Python library for visualizing scheduling solutions.

  It accepts generic assignments containing:

  - an actor, such as a machine or interviewer;
  - an event, such as a job or interview block;
  - a start time;
  - a duration.

  It then produces Plotly visualizations:

  - Gantt chart;
  - actor/time heatmap;
  - utilization chart;
  - duration distribution;
  - tabbed HTML dashboard.

  The parallel-machine example demonstrates the intended abstraction well: machines become actors and jobs become events (examples/
  parallel_machines_demo.py:4).

  The project is alpha-stage. README.md is empty, while Planning.md:35 describes a broader architecture than the current
  implementation.

  ## 2. Main execution flow

  For a typical call:

  fig = VisualizationEngine().from_dict(data).filter(...).gantt()

  the flow is:

  dict/JSON
     ↓
  Pydantic input schema
     ↓ to_domain()
  Domain Solution and Assignment objects
     ↓ optional filters
  Visualization-specific transformer
     ↓
  View model
     ↓
  Plotly renderer
     ↓
  go.Figure
     ↓ optional show/export/dashboard

  More concretely:

  1. VisualizationEngine.from_dict() validates input with SolutionInput.model_validate() (src/sched_viz/engine.py:48).
  2. SolutionInput.to_domain() creates domain objects (src/sched_viz/schema/input_schema.py:18).
  3. VisualizationEngine.filter() replaces its current Solution with filtered copies (src/sched_viz/engine.py:63).
  4. A chart method constructs its transformer and renderer. For Gantt this occurs in src/sched_viz/engine.py:85.
  5. The transformer converts domain data into a chart-specific view model.
  6. The renderer converts that view model into a Plotly figure.
  7. The engine can display or export the figure, or assemble several figures into an HTML dashboard.

  One important behavioral detail: the fluent engine is stateful. Calling filter() mutates the engine’s current solution, although
  the underlying Solution filters return new objects.

  ## 3. Major module responsibilities

  ### Public API

  src/sched_viz/__init__.py:1 exposes the engine, configuration, and principal domain types.

  ### Configuration

  src/sched_viz/config.py:4 defines the visual theme, palette, figure dimensions, and sizing rules.

  ### Schema layer

  src/sched_viz/schema/input_schema.py:6 defines Pydantic models for validating external dictionaries and converting them to domain
  models.

  ### Domain layer

  src/sched_viz/domain/models.py:4 defines:

  - Actor;
  - Event;
  - immutable Assignment;
  - assignment invariants and derived end.

  src/sched_viz/domain/solution.py:6 defines the aggregate holding assignments, timeline properties, filtering, and top-actor
  selection.

  Actor and Event are public but are not actually used by Solution or the processing pipeline. Assignments store their IDs directly.

  ### Core utilities

  src/sched_viz/core/color_registry.py:4 assigns stable colors to event IDs and retains them across charts produced by one engine.

  ### Transforms

  Each transformer reads a Solution and creates a rendering-oriented data structure:

  - src/sched_viz/transforms/gantt_transform.py:26: actor ordering, bar construction, merging, colors, timeline.
  - src/sched_viz/transforms/heatmap_transform.py:16: bucket selection and occupancy/assignment/event matrices.
  - src/sched_viz/transforms/utilization_transform.py:21: per-actor utilization and summary statistics.
  - src/sched_viz/transforms/duration_transform.py:14: duration groups and statistics.
  - src/sched_viz/transforms/base.py:5: structural transformer protocol.

  ### Renderers

  Renderers depend on view models rather than domain objects:

  - src/sched_viz/renderers/gantt_renderer.py:6
  - src/sched_viz/renderers/heatmap_renderer.py:6
  - src/sched_viz/renderers/utilization_renderer.py:6
  - src/sched_viz/renderers/duration_renderer.py:6

  They contain Plotly-specific layout, styling, hover, and viewport behavior.

  ### Engine

  src/sched_viz/engine.py:20 is the facade and composition root. It handles:

  - input loading;
  - mutable fluent state;
  - filtering;
  - transformer/renderer construction;
  - chart dispatch;
  - display;
  - individual export;
  - dashboard selection;
  - dashboard HTML generation and file writing.

  ### Tests

  Current tests cover:

  - domain invariants and filters;
  - schema validation and mapping;
  - Gantt transformation;
  - Gantt rendering;
  - three basic engine scenarios.

  There are no direct tests for heatmap, utilization, duration, JSON loading, individual export, dashboard generation, or color-
  registry lifecycle.

  ## 4. Schemas, domain models, transforms, and renderers

  These are four representations with different purposes:

   Layer        Knows about                                 Should not know about
  ━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Schema       External input shape and validation         Plotly and chart layout
  ───────────  ──────────────────────────────────────────  ────────────────────────────────────
   Domain       Scheduling concepts and invariants          Pydantic and Plotly
  ───────────  ──────────────────────────────────────────  ────────────────────────────────────
   Transform    How domain data becomes chart-ready data    File formats and HTML export
  ───────────  ──────────────────────────────────────────  ────────────────────────────────────
   Renderer     Plotly presentation of one view model       Input parsing and domain filtering

  The dependency direction is mostly correct:

  Schema ──creates──> Domain
  Transform ──reads──> Domain
  Renderer ──reads──> Transform view model
  Engine ──coordinates──> all of them

  A transformer is important because it prevents renderers from becoming a mixture of scheduling calculations and Plotly calls. For
  example, Gantt bar merging occurs in src/sched_viz/transforms/gantt_transform.py:47, while Plotly trace creation occurs in src/
  sched_viz/renderers/gantt_renderer.py:18.

  ## 5. Concrete design issues

  ### Engine has mixed responsibilities

  src/sched_viz/engine.py:20 is simultaneously:

  - facade;
  - mutable session;
  - input loader;
  - chart factory;
  - export service;
  - dashboard specification parser;
  - HTML template generator;
  - filesystem writer.

  The strongest example is export_dashboard() plus the large _build_tabbed_html() function (src/sched_viz/engine.py:132, src/
  sched_viz/engine.py:200).

  This makes dashboard behavior harder to test without exercising the facade and filesystem.

  ### Tight coupling to concrete chart implementations

  The engine imports and instantiates every concrete transformer and renderer (src/sched_viz/engine.py:9). Adding a chart requires:

  - new imports;
  - a new engine method;
  - changes to the dashboard renderer map;
  - changes to the label map;
  - documentation updates.

  That is concrete coupling and an Open/Closed weakness.

  ### Protocol exists but is not used as a boundary

  BaseTransformer is defined in src/sched_viz/transforms/base.py:5, but the engine never accepts or stores a BaseTransformer. It
  constructs concrete classes directly.

  There is no corresponding renderer protocol despite one being proposed in Planning.md:214.

  Consequently, the abstraction documents intent but does not currently provide Dependency Inversion.

  ### Validation is duplicated and slightly inconsistent

  Both Pydantic schemas and dataclasses validate the same fields:

  - src/sched_viz/schema/input_schema.py:6
  - src/sched_viz/domain/models.py:26

  Some duplication is justified because domain objects can be constructed without Pydantic. However, behavior has drifted:

  - Pydantic’s min_length=1 accepts a whitespace-only string.
  - The domain model rejects it using .strip().
  - Therefore schema validation may succeed and to_domain() then raise ValueError, rather than producing one consistent Pydantic
    ValidationError.

  Also, Assignment.__post_init__() calls .strip() directly. A non-string passed directly into the domain model produces an incidental
  AttributeError.

  ### Repeated actor-order logic

  Both Gantt and heatmap transforms implement alphabetical/load ordering separately:

  - src/sched_viz/transforms/gantt_transform.py:40
  - src/sched_viz/transforms/heatmap_transform.py:60

  This is small duplication, but it can drift when new ordering modes are added.

  ### Unused parameters and unnecessary work

  The engine builds and supplies a color_map for utilization and heatmap (src/sched_viz/engine.py:99, src/sched_viz/engine.py:106),
  but both renderers ignore it:

  - src/sched_viz/renderers/heatmap_renderer.py:12
  - src/sched_viz/renderers/utilization_renderer.py:11

  This gives the API a misleading dependency.

  ### Mutable objects inside frozen dataclasses

  Assignment, Actor, and Event are frozen, but their metadata dictionaries remain mutable (src/sched_viz/domain/models.py:4).
  “Frozen” therefore means attributes cannot be reassigned, not that the object is deeply immutable.

  Assignment also excludes participant_id and metadata from equality and hashing. That is intentional and tested, but it means two
  assignments with different participants can compare equal.

  ### Renderer layout duplication

  Every renderer repeats substantial Plotly theme and layout construction. Examples include background, font, margins, axes, and
  figure dimensions. This creates maintenance duplication across all four renderer files.

  ### Test coverage is uneven

  Only the Gantt path has focused transform and renderer tests. The additional charts are effectively unprotected. Dashboard HTML
  embeds content and file output but has no escaping or output tests; for example, title is interpolated directly into HTML at src/
  sched_viz/engine.py:215.

  ## 6. SOLID principles already present

  ### Single Responsibility

  Present at the layer level:

  - schema validates and maps input;
  - domain expresses scheduling state;
  - transforms calculate view data;
  - renderers create figures.

  Individual transformers and renderers generally have cohesive responsibilities.

  ### Open/Closed

  Partially present. A new visualization can be implemented as a new transformer/view-model/renderer pair without modifying existing
  pairs.

  The engine remains a modification point, so this is only partial.

  ### Liskov Substitution

  There is little inheritance, which avoids many LSP problems. Transformers structurally conform to the same transform(Solution)
  concept.

  No strong LSP claim can be made because the protocol is not used polymorphically.

  ### Interface Segregation

  The transformer protocol is appropriately small: one transform() operation. View models also expose only data needed by their
  renderer.

  ### Dependency Inversion

  The architecture has conceptual dependency boundaries—renderers consume view models rather than domain objects—but runtime
  orchestration depends on concrete implementations. DIP is therefore present in spirit, not fully implemented.

  ## 7. Violations or weaknesses

  These are better described as degrees rather than binary failures:

  - SRP: violated most clearly by VisualizationEngine, especially dashboard/export behavior.
  - OCP: weakened because every new chart requires engine and dashboard dispatch changes.
  - LSP: no demonstrated violation; there is not enough substitutable inheritance to exercise it.
  - ISP: largely respected.
  - DIP: weak in the engine because it constructs concrete collaborators directly.
  - DRY: actor sorting, renderer theming, schema/domain validation, and chart dispatch contain duplication.

  Not every concrete dependency is harmful. Plotly-specific renderers are supposed to depend on Plotly. The relevant question is
  whether a dependency obstructs change or testing.

  ## 8. Proposed small refactoring

  Extract dashboard export and HTML generation from the engine.

  ### Files involved

  Modify:

  - src/sched_viz/engine.py:132

  Add:

  - src/sched_viz/export/__init__.py
  - src/sched_viz/export/dashboard_exporter.py
  - tests/test_dashboard_exporter.py

  Potentially add focused integration assertions to:

  - tests/test_renderers.py:71

  ### Expected structure

  src/sched_viz/
  ├── engine.py
  └── export/
      ├── __init__.py
      └── dashboard_exporter.py

  tests/
  └── test_dashboard_exporter.py

  dashboard_exporter.py would own:

  - parsing chart specifications, or receiving already rendered labelled figures;
  - building tabbed HTML;
  - escaping dashboard titles and labels;
  - writing UTF-8 HTML.

  The engine would retain the public method but delegate:

  def export_dashboard(...):
      figures = self._render_dashboard_charts(charts)
      DashboardExporter(self._config).export(path, figures, title)

  For the smallest change, DashboardExporter can be constructed inside the method. Constructor injection is not required yet.

  ### Benefit

  - Restores a clearer facade responsibility for the engine.
  - Makes HTML generation directly unit-testable as a pure operation.
  - Isolates filesystem behavior behind one small class.
  - Gives HTML escaping and offline/online Plotly script policy a clear home.
  - Reduces the size and conceptual scope of engine.py.
  - Creates the export boundary already anticipated in Planning.md:69.

  ### Cost

  - One new package and class.
  - A small internal API for labelled figures and configuration.
  - Minor import and delegation changes.
  - No intended public API break.

  This is preferable to introducing a full chart registry first because it has a clear immediate testability benefit and limited
  blast radius.

  ### Required tests

  1. HTML contains one tab per supplied figure.
  2. First tab is active.
  3. Chart labels appear correctly.
  4. Plotly figure fragments are included.
  5. The Plotly script is included according to the chosen policy.
  6. Titles and labels are HTML-escaped.
  7. Export writes UTF-8 content to tmp_path.
  8. Empty figure input has defined behavior.
  9. Existing VisualizationEngine.export_dashboard() still creates a dashboard.
  10. Invalid chart specifications retain current errors.

  ## 9. Would Dependency Injection improve this project?

  A DI framework or container would be unnecessary overengineering.

  Targeted constructor injection could become useful, but only at real variation or test seams:

  - a dashboard exporter;
  - a chart registry;
  - possibly a color registry;
  - possibly an output writer.

  For example:

  VisualizationEngine(
      config=config,
      dashboard_exporter=DashboardExporter(config),
  )

  That would let an engine test inject a spy exporter, but the current tests can use tmp_path, and exporter construction is cheap. It
  is not yet necessary.

  The current VisConfig constructor parameter is already simple manual DI. That is the right scale for this project.

  The practical rule is:

  > Introduce an injectable abstraction when there are multiple implementations, an expensive/external dependency, or a test seam
  > that materially simplifies tests.

  Do not add interfaces around every transformer merely to claim DIP. A chart registry becomes worthwhile when charts need plugins,
  user-defined implementations, or independent release evolution.

  ## Implementation plan

  After approval:

  1. Create a feature branch such as refactor/extract-dashboard-exporter.
  2. Add characterization tests for current dashboard output and engine delegation.
  3. Add export/dashboard_exporter.py with pure HTML generation separated from file writing.
  4. Move _build_tabbed_html() out of engine.py.
  5. Make VisualizationEngine.export_dashboard() delegate while preserving its public signature.
  6. Escape title and generated labels; capture that behavior in tests.
  7. Run the existing test suite and the new dashboard tests.
  8. Review the diff for accidental public API changes.
  9. Commit in two logical units if desired:
      - characterization tests;
      - exporter extraction and engine delegation.

  No files have been modified and no dependencies were installed. I’ll wait for approval before implementing.