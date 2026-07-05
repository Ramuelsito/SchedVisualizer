# Planning: Scheduling Visualization API

## Decisiones de diseño previas al código

### Formato de entrada recomendado: Dataclasses + protocolo de entrada JSON/dict

**Argumento:** dado que el objetivo es una librería reutilizable, independiente de cualquier solver,
el formato de entrada debe:
- Ser **agnóstico al origen** (da igual si viene de un solver Python, un CSV, una API REST)
- Ser **validable** (poder detectar datos malformados antes de visualizar)
- Ser **serializable** (para compartir soluciones, guardar ejemplos de test, publicar la lib)

La estrategia es un **contrato de entrada en dos capas**:

```
Capa 1 → InputSchema (dict/JSON)     # Lo que recibe la API del mundo exterior
Capa 2 → Domain Models (dataclasses) # Representación interna tipada
```

El usuario puede pasar JSON directamente o construir los dataclasses manualmente.
La API valida y normaliza en el borde, y trabaja internamente siempre con dataclasses.

### Stack recomendado

| Necesidad              | Librería        | Razón                                                    |
|------------------------|-----------------|----------------------------------------------------------|
| Visualización base     | **Plotly**      | Interactivo + exportable a PNG/PDF/HTML sin cambiar código |
| Dashboard              | **Streamlit**   | Mínimo boilerplate, perfecto para uso personal y demos   |
| Validación de entrada  | **Pydantic v2** | Validación + serialización JSON nativa, estándar de facto |
| Exportación estática   | **Kaleido**     | Backend de Plotly para PNG/PDF sin browser               |
| Estructura de proyecto | **src layout**  | Estándar para paquetes publicables en PyPI               |

---

## Arquitectura del sistema

```
interview_viz/
├── pyproject.toml
├── README.md
├── src/
│   └── sched_viz/
│       ├── __init__.py               # API pública
│       │
│       ├── schema/                   # Capa 1: contrato de entrada
│       │   ├── __init__.py
│       │   ├── input_schema.py       # Pydantic models ← ActorInput, EventInput, SlotInput
│       │   └── validators.py         # Validaciones de dominio (slots válidos, etc.)
│       │
│       ├── domain/                   # Capa 2: modelos internos tipados
│       │   ├── __init__.py
│       │   ├── models.py             ← Actor, Event, Slot, Assignment
│       │   └── solution.py           ← Solution (colección de Assignments)
│       │
│       ├── transforms/               # Solution → ViewModel
│       │   ├── __init__.py
│       │   ├── base.py               # Protocolo/ABC BaseTransformer
│       │   ├── gantt_transform.py    # → GanttViewModel
│       │   ├── heatmap_transform.py  # → HeatmapViewModel
│       │   └── utilization_transform.py
│       │
│       ├── renderers/                # ViewModel → figura
│       │   ├── __init__.py
│       │   ├── base.py               # Protocolo/ABC BaseRenderer
│       │   ├── gantt_renderer.py     # GanttViewModel → Plotly Figure
│       │   ├── heatmap_renderer.py
│       │   └── utilization_renderer.py
│       │
│       ├── export/                   # Figura → archivo
│       │   ├── __init__.py
│       │   └── exporter.py           # PNG, PDF, HTML, SVG
│       │
│       ├── filters/                  # Reducción de datos antes de visualizar
│       │   ├── __init__.py
│       │   └── solution_filters.py   # por día, bloque, entrevistador, etc.
│       │
│       ├── engine.py                 # API unificada (facade principal)
│       └── config.py                 # Tema visual, colores, tamaños
│
├── dashboard/                        # App Streamlit (opcional, separada)
│   └── app.py
│
├── tests/
│   ├── fixtures/                     # JSON de soluciones de ejemplo
│   ├── test_schema.py
│   ├── test_transforms.py
│   └── test_renderers.py
│
└── examples/
    ├── basic_gantt.py
    └── full_dashboard.py
```

---

## Diseño de la capa de entrada (Schema)

### InputSchema (Pydantic)

```python
# schema/input_schema.py

from pydantic import BaseModel, field_validator
from typing import Optional

class AssignmentInput(BaseModel):
    candidate_id: str
    interviewer_id: str
    block_id: str
    day: int              # 0-indexed, rango [0, horizon_days)
    slot: int             # 0-indexed dentro del día, rango [0, slots_per_day)

class SolutionInput(BaseModel):
    assignments: list[AssignmentInput]
    horizon_days: int = 10
    slots_per_day: int = 5
    metadata: Optional[dict] = None   # info libre: nombre del run, solver usado, etc.

    @field_validator("assignments")
    def validate_slots(cls, assignments, info):
        # validar que day y slot estén en rango
        ...
```

### Por qué este diseño
- `candidate_id` es un string opaco → la viz nunca necesita saber quién es el candidato
- `block_id` agrupa visualmente → los colores se asignan por bloque, no por candidato
- `metadata` libre → permite anotar soluciones sin romper el contrato
- La API acepta directamente un dict/JSON: `SolutionInput.model_validate(data)`

---

## Diseño de los Domain Models (internos)

```python
# domain/models.py

from dataclasses import dataclass

@dataclass(frozen=True)
class Assignment:
    candidate_id: str
    interviewer_id: str
    block_id: str
    day: int
    slot: int

@dataclass
class Solution:
    assignments: list[Assignment]
    horizon_days: int
    slots_per_day: int
    metadata: dict

    def filter_by_day(self, day: int) -> "Solution": ...
    def filter_by_block(self, block_id: str) -> "Solution": ...
    def filter_by_interviewer(self, interviewer_id: str) -> "Solution": ...
    def get_interviewers(self) -> set[str]: ...
    def get_blocks(self) -> set[str]: ...
```

---

## Diseño de los Transformers

```python
# transforms/base.py

from typing import Protocol, TypeVar
from ..domain.solution import Solution

ViewModelT = TypeVar("ViewModelT")

class BaseTransformer(Protocol[ViewModelT]):
    def transform(self, solution: Solution) -> ViewModelT: ...
```

```python
# transforms/gantt_transform.py

from dataclasses import dataclass

@dataclass
class GanttBar:
    interviewer_id: str
    block_id: str
    day: int
    slot_start: int
    slot_end: int          # para bloques con múltiples slots contiguos
    color_key: str         # block_id normalizado para asignación de color

@dataclass
class GanttViewModel:
    bars: list[GanttBar]
    interviewers: list[str]   # orden del eje Y
    days: list[int]
    slots_per_day: int
    color_map: dict[str, str] # block_id → color hex

class GanttTransformer:
    def transform(self, solution: Solution) -> GanttViewModel:
        # 1. Agrupa assignments por (interviewer, day, slot)
        # 2. Detecta bloques contiguos y los fusiona en barras
        # 3. Genera color_map consistente por block_id
        # 4. Ordena interviewers para el eje Y
        ...
```

**Decisión clave de agregación:** con 2000 entrevistadores no se puede mostrar todo.
El transformer recibe una `Solution` ya filtrada. Los filtros van antes, no dentro del transformer.

---

## Diseño de los Renderers

```python
# renderers/base.py

from typing import Protocol
import plotly.graph_objects as go

class BaseRenderer(Protocol):
    def render(self, view_model) -> go.Figure: ...
```

```python
# renderers/gantt_renderer.py

import plotly.graph_objects as go
from ..transforms.gantt_transform import GanttViewModel

class GanttRenderer:
    def __init__(self, config: VisConfig = None):
        self.config = config or VisConfig()

    def render(self, vm: GanttViewModel) -> go.Figure:
        # Eje X: tiempo continuo (day * slots_per_day + slot)
        # Eje Y: interviewer_id (una fila por entrevistador)
        # Barras: shapes de Plotly, coloreadas por block_id
        # Separadores de día: líneas verticales punteadas
        # Hover: day, slot, block_id (sin candidate_id)
        ...
```

---

## El Engine: API unificada

```python
# engine.py

class VisualizationEngine:
    """Punto de entrada único. El usuario solo necesita conocer esta clase."""

    def from_dict(self, data: dict) -> "VisualizationEngine":
        """Carga una solución desde dict/JSON."""
        ...

    def from_json(self, path: str) -> "VisualizationEngine":
        """Carga desde archivo JSON."""
        ...

    def filter(self, days=None, blocks=None, interviewers=None) -> "VisualizationEngine":
        """Encadena filtros. Devuelve self para fluent API."""
        ...

    def gantt(self, **kwargs) -> go.Figure:
        """Transforma + renderiza Gantt. Shortcut principal."""
        ...

    def heatmap(self, **kwargs) -> go.Figure: ...
    def utilization(self, **kwargs) -> go.Figure: ...

    def export(self, fig: go.Figure, path: str, format="png"): ...
    def show(self, fig: go.Figure): ...
```

### Uso final que debería sentirse así:

```python
from interview_viz import VisualizationEngine

viz = VisualizationEngine()
fig = (
    viz.from_json("solution_run_42.json")
       .filter(days=[0, 1, 2])
       .gantt()
)
viz.export(fig, "gantt_day0_2.png")
```

---

## Fases de desarrollo

### Fase 1 — Fundamentos (prioridad máxima)
**Objetivo:** tener el primer Gantt chart funcional con arquitectura correcta desde el día 1.

- [ ] Estructura de proyecto con `src layout` y `pyproject.toml`
- [ ] `schema/input_schema.py` con Pydantic (AssignmentInput, SolutionInput)
- [ ] `domain/models.py` (Assignment, Solution con métodos de filtro)
- [ ] `transforms/gantt_transform.py` (GanttTransformer → GanttViewModel)
- [ ] `renderers/gantt_renderer.py` (GanttRenderer → Plotly Figure)
- [ ] `engine.py` básico (from_dict + gantt + show)
- [ ] `examples/basic_gantt.py` con datos sintéticos de prueba
- [ ] `config.py` con tema visual base

**Entregable:** `viz.from_dict(data).gantt()` funciona y produce un Gantt limpio.

---

### Fase 2 — Filtros y escala
**Objetivo:** hacer la herramienta usable con los volúmenes reales (2000 entrevistadores).

- [ ] `filters/solution_filters.py` completo (día, bloque, rango de slots, top-N entrevistadores)
- [ ] Fluent API en el engine (`.filter(...).gantt()`)
- [ ] Paginación de entrevistadores en el Gantt (mostrar N a la vez)
- [ ] Generador de datos sintéticos realistas para desarrollo/tests
- [ ] `export/exporter.py` (PNG + PDF con Kaleido)

**Entregable:** se puede explorar cualquier subconjunto de la solución real.

---

### Fase 3 — Visualizaciones adicionales
**Objetivo:** completar el conjunto de vistas analíticas.

- [ ] `transforms/heatmap_transform.py` + `renderers/heatmap_renderer.py`
  - Carga por entrevistador × día (cuántos slots ocupados)
- [ ] `transforms/utilization_transform.py` + renderer
  - % de utilización por entrevistador, distribución de carga
- [ ] Visualización de fragmentación de bloques
  - Bloques con slots no contiguos → métrica de fragmentación
- [ ] Exportación HTML standalone (dashboard ligero sin Streamlit)

**Entregable:** suite completa de vistas para análisis de soluciones.

---

### Fase 4 — Dashboard interactivo
**Objetivo:** interfaz visual para exploración sin escribir código.

- [ ] `dashboard/app.py` con Streamlit
  - Upload de JSON de solución
  - Selectores de día / bloque / entrevistador
  - Tabs: Gantt | Heatmap | Utilización
  - Botón de exportación
- [ ] Separación limpia: el dashboard solo llama al engine, no toca transforms ni renderers

**Entregable:** app Streamlit ejecutable con `streamlit run dashboard/app.py`.

---

### Fase 5 — Calidad y publicación
**Objetivo:** convertirlo en una librería compartible.

- [ ] Tests de integración con fixtures JSON
- [ ] Docstrings en API pública
- [ ] `README.md` con ejemplos y capturas
- [ ] `pyproject.toml` completo (versión, dependencias, entry points)
- [ ] Publicación en PyPI

---

## Resumen de principios de diseño

| Principio                  | Implementación concreta                                      |
|----------------------------|--------------------------------------------------------------|
| Entrada agnóstica           | Pydantic acepta dict/JSON de cualquier origen                |
| Separación estricta         | Schema → Domain → Transform → Render, sin saltar capas      |
| Extensibilidad              | Nuevas vistas = nuevo Transformer + nuevo Renderer           |
| Sin datos sensibles en viz  | `candidate_id` nunca llega al ViewModel ni al renderer       |
| Escalabilidad               | Filtros obligatorios antes de transformar, nunca todo a la vez|
| API fluida                  | Fluent interface en el engine para uso interactivo           |
| Publicable                  | src layout + pyproject.toml desde el día 1                   |
