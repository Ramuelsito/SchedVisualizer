from __future__ import annotations
import plotly.graph_objects as go
from ..config import VisConfig
from ..transforms.duration_transform import DurationViewModel

class DurationRenderer:
    def __init__(self, config=None):
        self._config = config or VisConfig()

    def render(self, vm: DurationViewModel, color_map=None) -> go.Figure:
        cfg = self._config
        fig = go.Figure()
        for event_id, durations in sorted(vm.durations_by_event.items()):
            # Always use the shared color_map so colors match across all charts.
            # If the engine is used standalone without a color_map, fall back to
            # the first palette color (neutral, not index-based to avoid mismatches).
            color = (color_map or {}).get(event_id, cfg.event_palette[0])
            fig.add_trace(go.Histogram(x=durations, name=event_id,
                                       marker=dict(color=color, opacity=0.7, line=dict(width=0)),
                                       hovertemplate=f"<b>{event_id}</b><br>Duration: %{{x}}<br>Count: %{{y}}<br><extra></extra>"))
        fig.add_vline(x=vm.mean_duration, line=dict(color=cfg.text_secondary, width=1.5, dash="dash"),
                      annotation=dict(text=f"Mean: {vm.mean_duration:.1f}", font=dict(color=cfg.text_secondary, size=11), bgcolor=cfg.surface_color))
        fig.update_layout(barmode="overlay", height=420, width=cfg.fig_width,
                          paper_bgcolor=cfg.background_color, plot_bgcolor=cfg.surface_color,
                          font=dict(family=cfg.font_family, color=cfg.text_primary, size=12),
                          title=dict(text="Assignment Duration Distribution", font=dict(size=15, color=cfg.text_primary), x=0.01),
                          legend=dict(bgcolor=cfg.surface_color, bordercolor=cfg.grid_color, borderwidth=1, title=dict(text="Event")),
                          margin=dict(l=60, r=40, t=70, b=60),
                          xaxis=dict(title=dict(text="Duration (units)", font=dict(color=cfg.text_secondary)),
                                     gridcolor=cfg.grid_color, tickfont=dict(color=cfg.text_secondary), fixedrange=False),
                          yaxis=dict(title=dict(text="Count", font=dict(color=cfg.text_secondary)),
                                     gridcolor=cfg.grid_color, tickfont=dict(color=cfg.text_secondary), fixedrange=False))
        return fig
