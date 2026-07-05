from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.utilization_renderer import UtilizationRenderer
from ..transforms.utilization_transform import UtilizationTransformer
from .base import RenderContext, reject_unknown_options


class UtilizationChart:
    name = "utilization"
    label = "Utilization"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        force_full = options.pop("force_full", False)
        reject_unknown_options(self.name, options)

        view_model = UtilizationTransformer().transform(solution)
        return UtilizationRenderer(config=context.config).render(
            view_model,
            force_full=force_full,
        )
