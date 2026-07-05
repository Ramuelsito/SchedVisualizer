from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.duration_renderer import DurationRenderer
from ..transforms.duration_transform import DurationTransformer
from .base import RenderContext, reject_unknown_options


class DurationChart:
    name = "duration"
    label = "Duration"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        reject_unknown_options(self.name, options)
        view_model = DurationTransformer().transform(solution)
        return DurationRenderer(config=context.config).render(
            view_model,
            color_map=dict(context.color_map),
        )