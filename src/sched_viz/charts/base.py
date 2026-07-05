from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import plotly.graph_objects as go

from ..config import VisConfig
from ..domain.solution import Solution

""" 
  ChartOptions represents a dictionary of options that can be
  passed to a chart's render method. The keys are option names, 
  and the values are the corresponding option values.
"""
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
        
def reject_unknown_options(chart_name: str, options: Mapping[str, Any]) -> None:
    if options:
        names = ", ".join(sorted(options))
        raise TypeError(f"Unknown options for {chart_name!r}: {names}")
