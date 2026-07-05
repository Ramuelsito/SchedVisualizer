"""
parallel_machines_demo.py — Parallel Machine Scheduling with real processing times.

Domain mapping:
    Actor    = Machine
    Event    = Job ID  (each job is its own event; color = job identity)
    Start    = cumulative completion time on the machine (real timeline)
    Duration = processing time of the job

With real durations the Gantt X axis represents actual time units,
and bar widths are proportional to job processing times.

Color strategy: one color per job_id.
With 40 jobs this uses all palette colors cycling. The benefit is that
a specific job can be visually tracked across machines if it were
reassigned — and the legend allows filtering by job.

Usage:
    python examples/parallel_machines_demo.py
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sched_viz import VisualizationEngine


# ---------------------------------------------------------------------------
# Problem instance data
# ---------------------------------------------------------------------------

PROCESSING_TIMES = {
    0: 34, 1: 66,  2: 27,  3: 4,   4: 23,  5: 85,  6: 43,  7: 4,
    8: 8,  9: 2,  10: 13, 11: 48, 12: 5,  13: 52, 14: 67, 15: 56,
   16: 67, 17: 6,  18: 29, 19: 9,  20: 20, 21: 76, 22: 98, 23: 7,
   24: 90, 25: 56, 26: 33, 27: 74, 28: 46, 29: 89, 30: 2,  31: 10,
   32: 80, 33: 20, 34: 67, 35: 31, 36: 82, 37: 77, 38: 18, 39: 96,
}

SOLUTION = """
Machine 0: 7 23 9 3 38 33 20 4 8 35 13 11 27 26 32 36 5 21 24 22 | TCT: 6257
Machine 1: 12 30 17 31 2 19 18 0 10 15 14 6 25 28 1 16 34 39 37 29 | TCT: 6703
Total TCT: 12960
"""


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

def parse_parallel_machine_solution(
    solution_str: str,
    processing_times: dict[int, int],
) -> dict:
    """Parse a parallel machine solution into sched_viz input format.

    Args:
        solution_str:     Raw solver output. Expected format per line:
                          "Machine N: j1 j2 j3 ... | TCT: XXXX"
        processing_times: {job_id: processing_time} from the problem instance.
                          Used to compute real start times and durations.

    Returns:
        dict ready for VisualizationEngine.from_dict()

    Color strategy:
        event_id = f"job_{job_id}" — one color per job.
        This lets the user visually track each job and filter by it in the legend.
    """
    assignments = []
    metadata = {}

    for line in solution_str.strip().splitlines():
        line = line.strip()

        if line.startswith("Total TCT"):
            m = re.search(r"Total TCT:\s*(\d+)", line)
            if m:
                metadata["total_tct"] = int(m.group(1))
            continue

        if not line.startswith("Machine"):
            continue

        m = re.match(r"Machine\s+(\d+):\s+([\d\s]+)(?:\|\s*TCT:\s*(\d+))?", line)
        if not m:
            continue

        machine_id = int(m.group(1))
        job_ids    = [int(j) for j in m.group(2).strip().split()]
        tct        = int(m.group(3)) if m.group(3) else None

        cursor = 0
        for job_id in job_ids:
            pt = processing_times[job_id]
            assignments.append({
                "actor_id":       f"machine_{machine_id}",
                "event_id":       f"job_{job_id:02d}",   # zero-padded for alphabetical = numerical order
                "start":          cursor,
                "duration":       pt,
                "participant_id": str(job_id),            # never visualized
                "metadata":       {"job_id": job_id, "machine_tct": tct},
            })
            cursor += pt

    return {"assignments": assignments, "metadata": metadata}


# ---------------------------------------------------------------------------
# Generate dashboard
# ---------------------------------------------------------------------------

data = parse_parallel_machine_solution(SOLUTION, PROCESSING_TIMES)

print(f"Assignments : {len(data['assignments'])}")
print(f"Total TCT   : {data['metadata'].get('total_tct', 'N/A')}")
print()

viz = VisualizationEngine()

print("Generating pm_dashboard.html ...")
viz.from_dict(data).export_dashboard(
    "output/pm_dashboard.html",
    charts=[
        # Gantt: X axis = real time, bar width = processing time
        # merge_bars=False because each job is a unique event and never repeats
        {"type": "gantt",   "merge_bars": False, "sort_actors": "alpha"},
        # Utilization: which machine carries more total processing time
        "utilization",
        # Duration distribution: spread of job processing times
        "duration",
    ],
    title=f"Parallel Machines — Optimal Solution (Total TCT = {data['metadata'].get('total_tct', 'N/A')})",
)
print("→ pm_dashboard.html")
