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