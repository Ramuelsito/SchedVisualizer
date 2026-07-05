# Plan de mejora de calidad: de 7,5 a 10

## 1. Objetivo y criterio de éxito

Este documento propone una secuencia de cambios manuales para convertir `sched-viz` en un proyecto defendible en una entrevista y publicable como librería pequeña.

Un **10/10** no significa añadir patrones indiscriminadamente. Significa que:

1. El comportamiento principal es correcto y está probado.
2. La arquitectura tiene límites claros y extensibles.
3. Los errores producen mensajes útiles.
4. Los artefactos generados son seguros y su funcionamiento está documentado.
5. El repositorio se puede instalar, comprobar y construir de forma reproducible.
6. La documentación describe el producto actual, no solamente sus planes históricos.

La implementación debe hacerse en commits pequeños. No mezclar una corrección funcional con formateo general o cambios visuales.

---

## 2. Orden recomendado

```text
1. Corregir DashboardExporter
2. Probar DashboardExporter y delegación del engine
3. Probar todos los Chart adapters
4. Completar tests de transforms/renderers/engine
5. Definir la política de Plotly JS
6. Limpiar artefactos versionados
7. Configurar calidad automática y CI
8. Reescribir README como documentación de producto
9. Verificar instalación y construcción del paquete
10. Revisión final y release candidate
```

No comenzar por CI o cobertura. Primero hay que corregir el comportamiento y definir qué se desea comprobar.

---

## 3. Fase 1 — Corregir `DashboardExporter`

### 3.1 Problema

En `src/sched_viz/export/dashboard.py`, `build_html()` crea y escapa botones y paneles, pero `_template()` descarta esos argumentos, recorre otra vez las figuras y vuelve a serializarlas.

Esto provoca:

- serialización duplicada de Plotly;
- dos implementaciones del mismo algoritmo;
- pérdida del escape HTML de las etiquetas;
- una API interna incoherente.

### 3.2 Estructura final deseada

Las responsabilidades deben quedar así:

```text
export()
  └── escribe el archivo

build_html()
  ├── valida la entrada
  ├── escapa texto externo
  ├── serializa cada figura una vez
  └── llama a _template()

_template()
  └── inserta fragmentos ya preparados en el documento
```

### 3.3 Código propuesto

Sustituir el contenido de `src/sched_viz/export/dashboard.py` por una implementación equivalente a esta:

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
    """Convert labelled Plotly figures into a tabbed HTML dashboard."""

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
                f'onclick="showTab(\'tab-{index}\', this)">'
                f"{safe_label}</button>"
            )
            panes.append(
                f'<div id="tab-{index}" class="tab-pane{active}">'
                f"{figure_html}</div>"
            )

        return self._template(
            title=escape(title),
            tab_buttons="".join(buttons),
            tab_contents="".join(panes),
        )

    def _template(
        self,
        title: str,
        tab_buttons: str,
        tab_contents: str,
    ) -> str:
        config = self._config

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:{config.background_color};color:{config.text_primary};font-family:{config.font_family};min-height:100vh}}
  header{{background:{config.surface_color};border-bottom:1px solid {config.grid_color};padding:18px 32px;display:flex;align-items:center;gap:12px}}
  header h1{{font-size:17px;font-weight:600;letter-spacing:-0.3px}}
  header span{{font-size:12px;color:{config.text_secondary};background:{config.background_color};border:1px solid {config.grid_color};border-radius:4px;padding:2px 8px}}
  .tab-bar{{background:{config.surface_color};border-bottom:1px solid {config.grid_color};padding:0 32px;display:flex;gap:4px;flex-wrap:wrap}}
  .tab-btn{{background:none;border:none;border-bottom:2px solid transparent;color:{config.text_secondary};cursor:pointer;font-family:{config.font_family};font-size:13px;padding:12px 16px;transition:color .15s,border-color .15s;white-space:nowrap}}
  .tab-btn:hover{{color:{config.text_primary}}}
  .tab-btn.active{{color:{config.event_palette[0]};border-bottom-color:{config.event_palette[0]};font-weight:500}}
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
```

Este primer cambio debe conservar temporalmente la política CDN actual. La decisión CDN/autocontenido se hará después y en otro commit.

### 3.4 Coste y beneficio

**Coste:** cambio localizado en un archivo y nuevos tests.

**Beneficio:** elimina un bug real, evita trabajo duplicado, recupera el escape HTML y simplifica el flujo.

### 3.5 Criterios de aceptación

- Cada figura se serializa una sola vez.
- El título y las etiquetas quedan escapados.
- El primer botón y panel tienen clase `active`.
- Los demás no tienen clase `active`.
- El aspecto visual actual se mantiene.
- Un dashboard sin figuras produce `ValueError`.

Commit sugerido:

```text
fix: remove duplicate dashboard rendering and escape labels
```

---

## 4. Fase 2 — Tests del exporter

Crear `tests/test_dashboard_exporter.py`.

### 4.1 Fixtures mínimas

```python
import plotly.graph_objects as go
import pytest

from sched_viz.config import VisConfig
from sched_viz.export.dashboard import DashboardExporter


@pytest.fixture
def exporter() -> DashboardExporter:
    return DashboardExporter(VisConfig())


@pytest.fixture
def figure() -> go.Figure:
    return go.Figure(go.Bar(x=[1], y=[2], name="Sample"))
```

### 4.2 Casos obligatorios

```python
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
```

### 4.3 Comprobar que no se serializa dos veces

La aserción sobre `Plotly.newPlot` detecta la duplicación observable. Para comprobar exactamente una llamada a `pio.to_html` por figura puede usarse `monkeypatch`:

```python
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
```

Commit sugerido:

```text
test: cover dashboard HTML generation and file export
```

---

## 5. Fase 3 — Verificar la inyección del exporter

Actualmente `VisualizationEngine` permite inyectar `DashboardExporter`, pero falta demostrar que realmente delega.

Añadir a `tests/test_engine.py`:

```python
class RecordingDashboardExporter:
    def __init__(self) -> None:
        self.calls = []

    def export(self, path, figures, title):
        self.calls.append(
            {
                "path": path,
                "figures": figures,
                "title": title,
            }
        )


def test_export_dashboard_delegates_to_injected_exporter(tmp_path):
    exporter = RecordingDashboardExporter()
    engine = VisualizationEngine(
        dashboard_exporter=exporter,
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

    destination = tmp_path / "dashboard.html"
    engine.export_dashboard(
        destination,
        charts=["gantt"],
        title="Injected exporter",
    )

    assert len(exporter.calls) == 1
    assert exporter.calls[0]["path"] == destination
    assert exporter.calls[0]["title"] == "Injected exporter"
    assert exporter.calls[0]["figures"][0][0] == "Gantt"
```

### ¿Hace falta un protocolo para el exporter?

Para practicar Dependency Inversion explícitamente, puede añadirse un puerto pequeño en `src/sched_viz/export/base.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .dashboard import LabeledFigure


class DashboardOutput(Protocol):
    def export(
        self,
        path: str | Path,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> None:
        ...
```

Y el engine usaría:

```python
dashboard_exporter: DashboardOutput | None = None
```

Esto mejora la expresión arquitectónica y permite que el test fake cumpla una interfaz documentada. No hace falta un contenedor DI.

Evitar un import circular: si `LabeledFigure` causa uno, mover el alias a `export/base.py` junto con el protocolo y hacer que `dashboard.py` lo importe desde allí.

Commit sugerido:

```text
test: verify dashboard exporter dependency injection
```

El protocolo puede ir en otro commit si se desea distinguir test de diseño:

```text
refactor: define dashboard output port
```

---

## 6. Fase 4 — Tests de los `Chart` adapters

Los adapters son el punto donde se conectan opciones, transformer y renderer. No deben repetir todos los tests de esas capas, pero sí verificar el cableado y los errores.

Crear `tests/test_charts.py`.

### 6.1 Contexto compartido

```python
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
```

### 6.2 Casos mínimos

```python
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
```

Añadir pruebas específicas:

- Gantt acepta `merge_bars`, `sort_actors` y `force_full`.
- Heatmap acepta `bucket_size`, `sort_actors`, `metric` y `force_full`.
- Utilization solo acepta `force_full`.
- Duration rechaza cualquier opción.
- Gantt y Duration usan los colores de `RenderContext`.

Ejemplo de color:

```python
def test_duration_uses_shared_event_colors(solution, context):
    figure = DurationChart().render(solution, context)
    colors = {trace.name: trace.marker.color for trace in figure.data}
    assert colors == {"E1": "#111111", "E2": "#222222"}
```

Commit sugerido:

```text
test: cover chart adapter wiring and option validation
```

---

## 7. Fase 5 — Completar cobertura funcional

No perseguir un porcentaje arbitrario. Probar decisiones, límites y errores.

### 7.1 `HeatmapTransformer`

Casos esenciales:

- `occupancy` cuenta unidades ocupadas por bucket.
- `assignments` cuenta asignaciones que intersectan cada bucket.
- `events` cuenta eventos distintos.
- `bucket_size="auto"` nunca produce cero.
- `bucket_size` explícito divide correctamente el horizonte.
- orden `alpha` y orden por carga.
- métrica desconocida produce `ValueError`.
- asignación que cruza dos buckets afecta a ambos.

### 7.2 `UtilizationTransformer`

Casos esenciales:

- duración asignada por actor;
- número de asignaciones;
- orden descendente de utilización;
- media y mediana para número par e impar de actores;
- horizonte con inicio distinto de cero;
- decisión explícita sobre solapamientos.

El código actual suma duraciones y limita el resultado a `1.0`:

```python
utilization=min(total / timeline_length, 1.0)
```

Esto oculta solapamientos. Hay que escoger y documentar una semántica:

1. **Los solapamientos son inválidos:** validarlos en `Solution` o schema.
2. **Los solapamientos son posibles:** calcular unión de intervalos para ocupación real.
3. **Se desea carga acumulada:** permitir valores mayores que `1.0` y llamarlo load ratio.

Para una librería genérica, la opción 2 suele ser la más robusta.

### 7.3 `DurationTransformer`

Casos esenciales:

- agrupación por evento;
- mínimo y máximo;
- media;
- múltiples eventos con duraciones repetidas.

### 7.4 Renderers

Probar comportamiento observable, no cada propiedad decorativa:

- tipo de figura;
- número/nombre de traces;
- límites `max_actors`, `max_timeline` y `max_buckets`;
- efecto de `force_full`;
- colores compartidos;
- ausencia de `participant_id` y metadata sensible;
- rango de ejes coherente con el view model.

### 7.5 Engine

Añadir tests para:

- `from_json()` usando `tmp_path`;
- todos los convenience methods;
- `render()` con chart desconocido;
- dashboard spec sin `type`;
- dashboard spec con tipo incorrecto;
- opciones inválidas;
- filtros encadenados;
- export HTML individual;
- error cuando no hay solución.

Commit sugerido:

```text
test: cover transforms renderers and engine edge cases
```

---

## 8. Fase 6 — Política de Plotly JavaScript

### 8.1 Problema actual

El exporter genera fragmentos con `include_plotlyjs=False` y añade una versión fija desde CDN. El documento no funciona sin red y la versión JavaScript puede no coincidir con la versión Python instalada.

### 8.2 Recomendación

Ofrecer una política explícita mediante configuración del exporter:

```python
from typing import Literal


PlotlyJsMode = Literal["cdn", "inline"]


class DashboardExporter:
    def __init__(
        self,
        config: VisConfig,
        plotly_js: PlotlyJsMode = "cdn",
    ) -> None:
        self._config = config
        self._plotly_js = plotly_js
```

Dos implementaciones posibles:

#### Modo CDN

- Figuras con `include_plotlyjs=False`.
- Template con el script CDN.
- Documento pequeño, requiere red.

#### Modo inline

- Incluir Plotly JS exactamente una vez.
- Las demás figuras usan `include_plotlyjs=False`.
- Documento grande, funciona offline.

La forma más simple de obtener el bundle una vez es usar `plotly.offline.get_plotlyjs()`:

```python
from plotly.offline import get_plotlyjs


def _plotly_script(self) -> str:
    if self._plotly_js == "inline":
        return f"<script>{get_plotlyjs()}</script>"
    return '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
```

Antes de adoptar `plotly-latest`, revisar la recomendación de la versión de Plotly utilizada. Una alternativa más reproducible es obtener o documentar una versión compatible en una constante única.

### 8.3 Tests

```python
def test_cdn_mode_references_external_plotly(...):
    assert "https://" in html


def test_inline_mode_has_no_external_plotly_script(...):
    assert "cdn.plot.ly" not in html
    assert "plotly.js" in html.lower()
```

### 8.4 Documentación

Usar nombres precisos:

- `cdn`: “single HTML dashboard; requires network access”.
- `inline`: “self-contained HTML dashboard; larger file”.

Commit sugerido:

```text
feat: make dashboard Plotly JS policy explicit
```

---

## 9. Fase 7 — Higiene de Git

El `.gitignore` actual ya ignora correctamente:

```gitignore
__pycache__/
*.py[cod]
output/
```

Pero `.gitignore` no deja de seguir archivos que ya están versionados.

### 9.1 Retirar caches del índice

Primero comprobar qué caches están tracked:

```bash
git ls-files | grep -E '(__pycache__|\.py[co]$)'
```

Retirarlos del índice sin borrar la copia local:

```bash
git rm --cached -r src/sched_viz/__pycache__
git rm --cached -r src/sched_viz/core/__pycache__
git rm --cached -r src/sched_viz/domain/__pycache__
git rm --cached -r src/sched_viz/renderers/__pycache__
git rm --cached -r src/sched_viz/schema/__pycache__
git rm --cached -r src/sched_viz/transforms/__pycache__
git rm --cached -r tests/__pycache__
```

Ejecutar solamente para rutas que aparezcan en `git ls-files`.

### 9.2 Decidir qué hacer con `output/`

Hay dos estrategias coherentes:

#### Opción recomendada: outputs generados fuera de Git

- Mantener `output/` ignorado.
- Retirar HTML previamente versionados con `git rm --cached`.
- Generarlos mediante los ejemplos.
- Incluir capturas pequeñas en `docs/images/` si hacen falta en README.

#### Opción alternativa: ejemplos oficiales versionados

- No ignorar todo `output/`.
- Guardar solo uno o dos HTML elegidos conscientemente.
- Añadir instrucciones para regenerarlos.
- Evitar que cada ejecución ensucie el working tree.

No usar los HTML como golden tests completos: contienen IDs y serialización que pueden cambiar entre versiones de Plotly.

### 9.3 Comprobaciones

```bash
git status --short
git check-ignore -v output/new-dashboard.html
git check-ignore -v src/sched_viz/__pycache__/engine.cpython-312.pyc
```

Commit sugerido:

```text
chore: remove generated artifacts from version control
```

---

## 10. Fase 8 — Herramientas de calidad

### 10.1 Dependencias de desarrollo

Actualizar `pyproject.toml`:

```toml
[project.optional-dependencies]
export = ["kaleido>=0.2"]
dev = [
    "pytest>=7",
    "pytest-cov>=5",
    "ruff>=0.6",
    "mypy>=1.10",
    "kaleido>=0.2",
]
```

Las versiones exactas deben revisarse cuando se implemente. No copiar versiones obsoletas sin comprobarlas.

### 10.2 Pytest

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
```

### 10.3 Coverage

```toml
[tool.coverage.run]
branch = true
source = ["sched_viz"]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 85
```

`85%` es un punto inicial razonable, no una medida de diseño. Subirlo únicamente cuando las pruebas adicionales representen casos útiles.

### 10.4 Ruff

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
```

Aplicar el formatter en un commit independiente para no ocultar cambios funcionales:

```bash
ruff check .
ruff format --check .
```

### 10.5 Mypy

Empezar de forma incremental:

```toml
[tool.mypy]
python_version = "3.11"
packages = ["sched_viz"]
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```

No activar `strict = true` hasta corregir primero las anotaciones existentes. La meta es feedback útil, no añadir decenas de ignores.

### 10.6 Comandos locales

```bash
python -m pytest
python -m pytest --cov=sched_viz --cov-report=term-missing
ruff check .
ruff format --check .
mypy -p sched_viz
```

Commits sugeridos:

```text
chore: configure pytest coverage and ruff
chore: add incremental static type checking
```

---

## 11. Fase 9 — Integración continua

Crear `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install project
        run: python -m pip install -e ".[dev]"

      - name: Test
        run: python -m pytest --cov=sched_viz --cov-report=term-missing

      - name: Lint
        run: ruff check .

      - name: Format
        run: ruff format --check .

      - name: Type check
        run: mypy -p sched_viz
```

Revisar las versiones actuales de GitHub Actions al implementar. La configuración anterior muestra la estructura, no sustituye esa comprobación.

Si `mypy` o coverage aún no están estabilizados, añadirlos después. No dejar CI permanentemente roja.

Commit sugerido:

```text
ci: test supported Python versions and quality checks
```

---

## 12. Fase 10 — Convertir README en documentación real

El `README.md` actual contiene principalmente el análisis previo y propuestas de refactoring. Eso es útil como material de estudio, pero no funciona como portada de una librería.

Mover el análisis histórico a `docs/design-review.md` o conservarlo en `Refactoring.md`. Reescribir README con esta estructura:

```text
# sched-viz

Breve descripción y captura

## Features
## Installation
## Quick start
## Input format
## Available charts
## Filtering
## Dashboard export
## CDN vs self-contained export
## Custom charts
## Architecture
## Development
## Running tests
## Project status and limitations
## License
```

### 12.1 Quick start mínimo

```python
from sched_viz import VisualizationEngine


data = {
    "assignments": [
        {
            "actor_id": "machine-1",
            "event_id": "job-42",
            "start": 0,
            "duration": 3,
        }
    ]
}

figure = VisualizationEngine().from_dict(data).gantt()
figure.show()
```

### 12.2 Documentar extensión mediante DIP

Mostrar un custom chart pequeño y explicar:

- `VisualizationEngine` depende de `ChartRegistry` y del protocolo `Chart`.
- La composición predeterminada vive en `application.py`.
- Un chart concreto compone transformer y renderer.
- No se usa un framework DI.

### 12.3 Limitaciones honestas

Documentar:

- semántica de solapamientos;
- requisitos de Kaleido para exportación estática;
- costes del HTML inline;
- comportamiento ante soluciones grandes;
- estado alpha mientras la API no sea estable.

Commit sugerido:

```text
docs: replace design notes with product documentation
```

---

## 13. Fase 11 — Packaging y API pública

### 13.1 Revisar metadata

En `pyproject.toml`, reemplazar URLs placeholder:

```toml
[project.urls]
Homepage = "https://github.com/<usuario>/sched-viz"
Repository = "https://github.com/<usuario>/sched-viz"
Issues = "https://github.com/<usuario>/sched-viz/issues"
```

Añadir autores si corresponde y comprobar que existe un archivo `LICENSE` compatible con `MIT`.

### 13.2 Build

En un entorno de desarrollo con dependencias instaladas:

```bash
python -m build
python -m twine check dist/*
```

Instalar el wheel en un entorno limpio y ejecutar un smoke test:

```bash
python -m venv /tmp/sched-viz-smoke
/tmp/sched-viz-smoke/bin/pip install dist/*.whl
/tmp/sched-viz-smoke/bin/python -c "from sched_viz import VisualizationEngine; print(VisualizationEngine)"
```

### 13.3 API pública

Decidir qué se soporta públicamente y exportarlo conscientemente:

- `VisualizationEngine`
- `VisConfig`
- modelos de dominio principales
- `Chart`, `ChartRegistry`, `RenderContext` si la extensión es pública

No exportar automáticamente todos los transformers y renderers salvo que exista compromiso de compatibilidad.

Commit sugerido:

```text
build: validate package metadata and public API
```

---

## 14. Fase 12 — Pulido de código

Cambios pequeños detectados durante la revisión:

### 14.1 Docstrings de módulo

En `charts/base.py` y `charts/registry.py`, los strings descriptivos están después de imports. No son docstrings de módulo.

Moverlos a la primera línea:

```python
"""Chart interfaces and shared rendering context."""

from __future__ import annotations
```

### 14.2 Alias no utilizado

`ChartOptions = Mapping[str, Any]` está documentado pero no se usa. Elegir:

- usarlo en una API real;
- o eliminarlo para evitar superficie conceptual innecesaria.

### 14.3 Formato y final de archivo

- Añadir newline final a `engine.py`.
- Formatear firmas largas.
- Mantener docstrings en la API pública.
- Evitar comentarios que solo repiten el código.

### 14.4 Validación de identificadores

Unificar la validación de espacios entre schema y dominio. Pydantic acepta inicialmente `" "` por longitud, pero el dominio lo rechaza.

Una opción Pydantic v2:

```python
from typing import Annotated

from pydantic import StringConstraints


NonBlankId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
```

Usarlo para `actor_id` y `event_id`. Mantener también los invariantes del dominio porque este puede construirse sin Pydantic.

Commit sugerido:

```text
refactor: align validation and clean public module documentation
```

---

## 15. Revisión manual del resultado visual

Los tests estructurales no detectan problemas como textos cortados, leyendas solapadas o colores poco legibles.

Crear una checklist manual para cada release:

### Dataset pequeño

- Gantt con 3–5 actores.
- Heatmap con varios buckets.
- Utilización con valores sobre y bajo la media.
- Histograma con varios eventos.

### Dataset grande

- Límite de actores visible.
- Scroll/zoom funcional.
- `force_full=True` comprobado.
- Altura del documento razonable.

### Dashboard

- Cambio de pestañas.
- Resize de ventana.
- Hover y leyendas.
- Título con caracteres Unicode.
- Modo CDN con red.
- Modo inline sin red.

Las capturas representativas pueden guardarse en `docs/images/`, no en `output/`.

---

## 16. Estrategia Git completa

Crear una rama:

```bash
git switch -c quality/product-readiness
```

Secuencia recomendada de commits:

```text
fix: remove duplicate dashboard rendering and escape labels
test: cover dashboard HTML generation and file export
test: verify dashboard exporter dependency injection
test: cover chart adapter wiring and option validation
test: cover transforms renderers and engine edge cases
feat: make dashboard Plotly JS policy explicit
chore: remove generated artifacts from version control
chore: configure pytest coverage and ruff
chore: add incremental static type checking
ci: test supported Python versions and quality checks
docs: replace design notes with product documentation
build: validate package metadata and public API
```

Antes de cada commit:

```bash
git status --short
git diff --check
python -m pytest
```

Antes del pull request:

```bash
python -m pytest --cov=sched_viz --cov-report=term-missing
ruff check .
ruff format --check .
mypy -p sched_viz
python -m build
```

Revisar el historial:

```bash
git log --oneline --decorate main..HEAD
```

Cada commit debe poder explicarse por separado durante la entrevista.

---

## 17. Rúbrica final de evaluación

### Correctitud — 2 puntos

- Todos los charts funcionan.
- Casos límite definidos.
- Exporter sin duplicación ni inyección HTML.
- Semántica de solapamientos documentada.

### Diseño — 2 puntos

- Schema, domain, transform, renderer y export separados.
- Engine depende del contrato de charts.
- Registry extensible.
- Dependencias inyectadas donde aportan valor.
- Sin abstracciones ceremoniales.

### Tests — 2 puntos

- Domain, schema, transforms, renderers, charts, engine y exporter cubiertos.
- Errores y límites probados.
- Integración pública probada.
- Cobertura de ramas razonable.

### Experiencia de usuario — 1,5 puntos

- README accionable.
- Ejemplos ejecutables.
- Errores claros.
- HTML online/offline documentado.
- Resultados visuales revisados.

### Ingeniería del repositorio — 1,5 puntos

- CI verde en Python soportado.
- Ruff, typing y build reproducible.
- Sin caches ni outputs accidentales.
- Commits pequeños y explicables.

### Publicación — 1 punto

- Metadata y licencia correctas.
- Wheel instalable.
- API pública definida.
- Limitaciones y estado del proyecto claros.

---

## 18. Definition of Done

El objetivo se considera completado cuando:

- [ ] `DashboardExporter` no duplica serialización.
- [ ] Título y labels están escapados.
- [ ] CDN e inline tienen comportamiento explícito y probado.
- [ ] Todos los charts tienen tests de adapter.
- [ ] Todos los transforms y renderers tienen cobertura esencial.
- [ ] El engine tiene tests de integración y errores.
- [ ] La inyección del registry y exporter está demostrada con fakes.
- [ ] La semántica de asignaciones solapadas está decidida.
- [ ] No hay `__pycache__`, `.pyc` ni outputs accidentales tracked.
- [ ] `python -m pytest` pasa.
- [ ] Coverage cumple el umbral acordado.
- [ ] Ruff y mypy pasan.
- [ ] CI pasa en Python 3.11 y 3.12.
- [ ] README permite instalar y usar la librería desde cero.
- [ ] El dashboard se ha revisado manualmente en datasets pequeño y grande.
- [ ] El wheel se construye e instala en un entorno limpio.

El orden importa: primero corregir y probar el comportamiento; después automatizar su garantía; finalmente pulir documentación y publicación.
