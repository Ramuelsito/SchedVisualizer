from __future__ import annotations
import plotly.graph_objects as go
from ..config import VisConfig
from ..transforms.heatmap_transform import HeatmapViewModel


class HeatmapRenderer:
    def __init__(self, config=None, max_actors=60, max_buckets=100):
        self._config = config or VisConfig()
        self._max_actors = max_actors
        self._max_buckets = max_buckets

    def render(self, vm: HeatmapViewModel, force_full=False, color_map=None) -> go.Figure:
        cfg = self._config
        is_large = not force_full and (
            len(vm.actor_labels) > self._max_actors or len(vm.bucket_labels) > self._max_buckets
        )
        actors = vm.actor_labels[: self._max_actors] if is_large else vm.actor_labels
        buckets = vm.bucket_labels[: self._max_buckets] if is_large else vm.bucket_labels
        z = [
            row[: self._max_buckets] if is_large else row
            for row in vm.z[: self._max_actors if is_large else len(vm.z)]
        ]
        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=buckets,
                y=actors,
                colorscale=[
                    [0.0, cfg.surface_color],
                    [0.4, cfg.event_palette[0]],
                    [1.0, cfg.event_palette[3]],
                ],
                zmin=0,
                zmax=vm.max_value,
                hoverongaps=False,
                hovertemplate="Actor: %{y}<br>Bucket: %{x}<br>Load: %{z:.0f} units<br><extra></extra>",
                colorbar=dict(
                    title=dict(text=vm.metric.capitalize(), font=dict(color=cfg.text_secondary)),
                    tickfont=dict(color=cfg.text_secondary),
                    bgcolor=cfg.surface_color,
                    bordercolor=cfg.grid_color,
                ),
            )
        )
        sub = (
            f"<br><sup style='color:{cfg.text_secondary}'>Showing {len(actors)}/{len(vm.actor_labels)} actors</sup>"
            if is_large
            else ""
        )
        h = max(cfg.fig_min_height, len(actors) * 18 + 140)
        fig.update_layout(
            height=h,
            width=cfg.fig_width,
            paper_bgcolor=cfg.background_color,
            plot_bgcolor=cfg.surface_color,
            font=dict(family=cfg.font_family, color=cfg.text_primary, size=12),
            title=dict(
                text=f"Heatmap — {vm.metric}{sub}",
                font=dict(size=15, color=cfg.text_primary),
                x=0.01,
            ),
            margin=dict(l=140, r=80, t=70, b=80),
            xaxis=dict(
                title=dict(
                    text=f"Timeline · bucket size = {vm.bucket_size}",
                    font=dict(color=cfg.text_secondary),
                ),
                tickfont=dict(color=cfg.text_secondary, size=9),
                gridcolor=cfg.grid_color,
                fixedrange=False,
            ),
            yaxis=dict(
                tickfont=dict(color=cfg.text_secondary, size=9),
                gridcolor=cfg.grid_color,
                fixedrange=False,
                autorange="reversed",
            ),
        )
        return fig
