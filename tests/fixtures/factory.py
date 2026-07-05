"""
Synthetic data factory for testing.

Generates realistic scheduling solutions without coupling tests
to any real domain. All IDs are opaque strings.
"""

from __future__ import annotations
import random
from sched_viz.domain.models import Assignment
from sched_viz.domain.solution import Solution


def make_solution(
    n_actors: int = 5,
    n_events: int = 3,
    timeline_length: int = 20,
    avg_assignments_per_actor: int = 4,
    seed: int = 42,
) -> Solution:
    """Generate a synthetic Solution with no overlaps per actor."""
    rng = random.Random(seed)
    actor_ids = [f"actor_{i:03d}" for i in range(n_actors)]
    event_ids = [f"event_{chr(65 + i)}" for i in range(n_events)]

    assignments: list[Assignment] = []

    for actor_id in actor_ids:
        cursor = 0
        for _ in range(avg_assignments_per_actor):
            if cursor >= timeline_length:
                break
            gap = rng.randint(0, 2)
            start = cursor + gap
            duration = rng.randint(1, 3)
            if start + duration > timeline_length:
                break
            assignments.append(
                Assignment(
                    actor_id=actor_id,
                    event_id=rng.choice(event_ids),
                    start=start,
                    duration=duration,
                )
            )
            cursor = start + duration

    return Solution(assignments=assignments)
