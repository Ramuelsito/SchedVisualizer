from __future__ import annotations
import plotly.graph_objects as go
from ..config import VisConfig
from ..transforms.gantt_transform import GanttBar, GanttViewModel


class GanttRenderer:
    def __init__(self, config=None, max_actors=50, max_timeline=200):
        self._config = config or VisConfig()
        self._max_actors = max_actors
        self._max_timeline = max_timeline

    def render(self, vm: GanttViewModel, force_full=False) -> go.Figure:
        cfg = self._config
        n = len(vm.actor_order)
        tl = vm.timeline_end - vm.timeline_start
        is_large = not force_full and (n > self._max_actors or tl > self._max_timeline)
        actor_index = {a: i for i, a in enumerate(reversed(vm.actor_order))}
        bars_by_event: dict[str, list[GanttBar]] = {}
        for bar in vm.bars:
            bars_by_event.setdefault(bar.event_id, []).append(bar)
        fig = go.Figure()
        for event_id, bars in sorted(bars_by_event.items()):
            color = vm.color_map.get(event_id, cfg.event_palette[0])
            opacity = cfg.bar_opacity * (0.85 if is_large else 1.0)
            fig.add_trace(
                go.Bar(
                    name=event_id,
                    x=[b.duration for b in bars],
                    y=[actor_index[b.actor_id] for b in bars],
                    base=[b.start for b in bars],
                    orientation="h",
                    marker=dict(color=color, opacity=opacity, line=dict(width=0)),
                    customdata=[[b.actor_id, b.event_id, b.start, b.duration] for b in bars],
                    hovertemplate="<b>%{customdata[1]}</b><br>Actor: %{customdata[0]}<br>Start: %{customdata[2]}<br>Duration: %{customdata[3]}<br><extra></extra>",
                )
            )
        h = max(cfg.fig_min_height, n * cfg.fig_height_per_actor + 120)
        ix = (
            [-0.5, min(n - 0.5, self._max_actors - 0.5)]
            if is_large and n > self._max_actors
            else [-0.5, n - 0.5]
        )
        xx = (
            [vm.timeline_start, vm.timeline_start + self._max_timeline]
            if is_large and tl > self._max_timeline
            else [vm.timeline_start, vm.timeline_end]
        )
        sub = (
            f"<br><sup style='color:{cfg.text_secondary}'>Large solution — scroll/zoom to explore · force_full=True to disable</sup>"
            if is_large
            else ""
        )
        fig.update_layout(
            barmode="overlay",
            height=h,
            width=cfg.fig_width,
            paper_bgcolor=cfg.background_color,
            plot_bgcolor=cfg.surface_color,
            font=dict(family=cfg.font_family, color=cfg.text_primary, size=12),
            title=dict(
                text=f"Gantt Chart{sub}", font=dict(size=15, color=cfg.text_primary), x=0.01
            ),
            legend=dict(
                bgcolor=cfg.surface_color,
                bordercolor=cfg.grid_color,
                borderwidth=1,
                font=dict(size=11),
                title=dict(text="Event", font=dict(size=12)),
            ),
            margin=dict(l=140, r=40, t=70, b=60),
            dragmode="zoom",
            xaxis=dict(
                title=dict(text="Timeline", font=dict(color=cfg.text_secondary)),
                range=xx,
                gridcolor=cfg.grid_color,
                zerolinecolor=cfg.axis_color,
                tickfont=dict(color=cfg.text_secondary),
                fixedrange=False,
            ),
            yaxis=dict(
                tickmode="array",
                tickvals=list(actor_index.values()),
                ticktext=list(reversed(vm.actor_order)),
                tickfont=dict(color=cfg.text_secondary, size=10),
                gridcolor=cfg.grid_color,
                range=ix,
                fixedrange=False,
            ),
            modebar=dict(
                bgcolor=cfg.surface_color, color=cfg.text_secondary, activecolor=cfg.text_primary
            ),
        )
        return fig
