from __future__ import annotations
import plotly.graph_objects as go
from ..config import VisConfig
from ..transforms.utilization_transform import UtilizationViewModel

class UtilizationRenderer:
    def __init__(self, config=None, max_actors=40):
        self._config = config or VisConfig()
        self._max_actors = max_actors

    def render(self, vm: UtilizationViewModel, force_full=False, color_map=None) -> go.Figure:
        cfg = self._config
        is_large = not force_full and len(vm.actors) > self._max_actors
        visible = vm.actors if not is_large else vm.actors[:self._max_actors]
        pct = [round(a.utilization*100,1) for a in visible]
        labels = [a.actor_id for a in visible]
        colors = [cfg.event_palette[0] if a.utilization >= vm.mean_utilization else cfg.event_palette[3] for a in visible]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=pct, y=labels, orientation="h",
                             marker=dict(color=colors, opacity=cfg.bar_opacity, line=dict(width=0)),
                             customdata=[[a.actor_id, a.assigned_duration, a.n_assignments] for a in visible],
                             hovertemplate="<b>%{customdata[0]}</b><br>Utilization: %{x:.1f}%<br>Assigned: %{customdata[1]} units<br>Assignments: %{customdata[2]}<br><extra></extra>",
                             name="Utilization"))
        for value, label, color in [(vm.mean_utilization*100,"Mean",cfg.event_palette[2]),(vm.median_utilization*100,"Median",cfg.event_palette[6])]:
            fig.add_vline(x=value, line=dict(color=color, width=1.5, dash="dash"),
                          annotation=dict(text=f"{label}: {value:.1f}%", font=dict(color=color, size=11), bgcolor=cfg.surface_color))
        sub = (f"<br><sup style='color:{cfg.text_secondary}'>Showing top {self._max_actors} of {len(vm.actors)}</sup>" if is_large else "")
        h = max(cfg.fig_min_height, len(visible)*cfg.fig_height_per_actor+120)
        fig.update_layout(height=h, width=cfg.fig_width, paper_bgcolor=cfg.background_color, plot_bgcolor=cfg.surface_color,
                          font=dict(family=cfg.font_family, color=cfg.text_primary, size=12),
                          title=dict(text=f"Actor Utilization{sub}", font=dict(size=15, color=cfg.text_primary), x=0.01),
                          showlegend=False, margin=dict(l=140, r=60, t=70, b=60),
                          xaxis=dict(title=dict(text="Utilization (%)", font=dict(color=cfg.text_secondary)),
                                     range=[0,105], gridcolor=cfg.grid_color, ticksuffix="%",
                                     tickfont=dict(color=cfg.text_secondary), fixedrange=False),
                          yaxis=dict(gridcolor=cfg.grid_color, tickfont=dict(color=cfg.text_secondary, size=10),
                                     fixedrange=False, autorange="reversed"))
        return fig
