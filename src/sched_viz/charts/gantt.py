from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ..domain.solution import Solution
from ..renderers.gantt_renderer import GanttRenderer
from ..transforms.gantt_transform import GanttTransformer
from .base import RenderContext, reject_unknown_options


class GanttChart:
    name = "gantt"
    label = "Gantt"

    def render(
        self,
        solution: Solution,
        context: RenderContext,
        **options: Any,
    ) -> go.Figure:
        merge_bars = options.pop("merge_bars", True)
        sort_actors = options.pop("sort_actors", "alpha")
        force_full = options.pop("force_full", False)
        reject_unknown_options(self.name, options)

        view_model = GanttTransformer(
            config=context.config,
            merge_bars=merge_bars,
            sort_actors=sort_actors,
            color_map=dict(context.color_map),
        ).transform(solution)

        return GanttRenderer(config=context.config).render(
            view_model,
            force_full=force_full,
        )