from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.heatmap_renderer import HeatmapRenderer
from ..transforms.heatmap_transform import HeatmapTransformer
from .base import RenderContext, reject_unknown_options


class HeatmapChart:
    name = "heatmap"
    label = "Heatmap"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        bucket_size = options.pop("bucket_size", "auto")
        sort_actors = options.pop("sort_actors", "alpha")
        metric = options.pop("metric", "occupancy")
        force_full = options.pop("force_full", False)
        reject_unknown_options(self.name, options)

        view_model = HeatmapTransformer(
            bucket_size=bucket_size,
            sort_actors=sort_actors,
            metric=metric,
        ).transform(solution)

        return HeatmapRenderer(config=context.config).render(
            view_model,
            force_full=force_full,
        )
