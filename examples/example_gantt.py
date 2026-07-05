"""
Basic Gantt chart example.

Simulates a small scheduling solution with 4 actors, 3 event types,
and a 20-unit timeline. Run with:
  python examples/basic_gantt.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sched_viz import VisualizationEngine

data = {
  "metadata": {"run_id": "example-01", "solver": "manual"},
  "assignments": [
    # Actor A1
    {"actor_id": "A1", "event_id": "E_blue",   "start": 0,  "duration": 3},
    {"actor_id": "A1", "event_id": "E_orange",  "start": 5,  "duration": 2},
    {"actor_id": "A1", "event_id": "E_blue",    "start": 10, "duration": 4},
    # Actor A2
    {"actor_id": "A2", "event_id": "E_orange",  "start": 0,  "duration": 5},
    {"actor_id": "A2", "event_id": "E_green",   "start": 6,  "duration": 3},
    {"actor_id": "A2", "event_id": "E_orange",  "start": 12, "duration": 2},
    # Actor A3
    {"actor_id": "A3", "event_id": "E_green",   "start": 2,  "duration": 6},
    {"actor_id": "A3", "event_id": "E_blue",    "start": 9,  "duration": 3},
    # Actor A4
    {"actor_id": "A4", "event_id": "E_blue",    "start": 1,  "duration": 2},
    {"actor_id": "A4", "event_id": "E_green",   "start": 4,  "duration": 4},
    {"actor_id": "A4", "event_id": "E_orange",  "start": 11, "duration": 5},
  ],
}

viz = VisualizationEngine()
fig = viz.from_dict(data).gantt()
# viz.show(fig)
fig.write_html("test.html")
print("HTML generado")
