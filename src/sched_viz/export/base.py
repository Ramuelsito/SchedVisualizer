from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, TypeAlias

import plotly.graph_objects as go


LabeledFigure: TypeAlias = tuple[str, go.Figure]


class DashboardOutput(Protocol):
    """Port used by the engine to persist a rendered dashboard."""

    def export(
        self,
        path: str | Path,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> None: ...
