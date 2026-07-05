"""
Full dashboard example.

Simulates a small scheduling solution with 4 actors, 3 event types,
and a 20-unit timeline. Run with:
  python examples/full_dashboard.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sched_viz import VisualizationEngine

data = {
    "metadata": {"run_id": "example-01", "solver": "manual"},
    "assignments": [
        # Actor A1
        {"actor_id": "A1", "event_id": "Event01", "start": 0, "duration": 3},
        {"actor_id": "A1", "event_id": "Event02", "start": 5, "duration": 2},
        {"actor_id": "A1", "event_id": "Event01", "start": 10, "duration": 4},
        # Actor A2
        {"actor_id": "A2", "event_id": "Event02", "start": 0, "duration": 5},
        {"actor_id": "A2", "event_id": "Event03", "start": 6, "duration": 3},
        {"actor_id": "A2", "event_id": "Event02", "start": 12, "duration": 2},
        # Actor A3
        {"actor_id": "A3", "event_id": "Event03", "start": 2, "duration": 6},
        {"actor_id": "A3", "event_id": "Event01", "start": 9, "duration": 3},
        # Actor A4
        {"actor_id": "A4", "event_id": "Event01", "start": 1, "duration": 2},
        {"actor_id": "A4", "event_id": "Event03", "start": 4, "duration": 4},
        {"actor_id": "A4", "event_id": "Event02", "start": 11, "duration": 5},
    ],
}

viz = VisualizationEngine()
viz.from_dict(data).export_dashboard(
    "output/report.html",
    charts=[
        {"type": "gantt", "sort_actors": "load"},
        {"type": "heatmap", "metric": "occupancy"},
        "utilization",
    ],
)
print("HTML generado")
