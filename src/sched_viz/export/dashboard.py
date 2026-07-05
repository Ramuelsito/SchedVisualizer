from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path
from typing import Literal

import plotly.io as pio
from plotly.offline import get_plotlyjs

from ..config import VisConfig
from .base import LabeledFigure


PlotlyJsMode = Literal["inline", "cdn"]
PLOTLY_CDN_URL = "https://cdn.plot.ly/plotly-2.27.0.min.js"


class DashboardExporter:
    """Convert labelled Plotly figures into a tabbed HTML dashboard."""

    def __init__(
        self,
        config: VisConfig,
        plotly_js: PlotlyJsMode = "inline",
    ) -> None:
        if plotly_js not in ("inline", "cdn"):
            raise ValueError("plotly_js must be 'inline' or 'cdn'")
        self._config = config
        self._plotly_js = plotly_js

    def export(
        self,
        path: str | Path,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> None:
        html = self.build_html(figures=figures, title=title)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html, encoding="utf-8")

    def build_html(
        self,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> str:
        if not figures:
            raise ValueError("Dashboard must contain at least one figure")

        buttons: list[str] = []
        panes: list[str] = []

        for index, (label, figure) in enumerate(figures):
            active = " active" if index == 0 else ""
            safe_label = escape(label)
            figure_html = pio.to_html(
                figure,
                full_html=False,
                include_plotlyjs=False,
            )

            buttons.append(
                f'<button class="tab-btn{active}" '
                f"onclick=\"showTab('tab-{index}', this)\">"
                f"{safe_label}</button>"
            )
            panes.append(f'<div id="tab-{index}" class="tab-pane{active}">{figure_html}</div>')

        return self._template(
            title=escape(title),
            tab_buttons="".join(buttons),
            tab_contents="".join(panes),
            plotly_script=self._plotly_script(),
        )

    def _plotly_script(self) -> str:
        if self._plotly_js == "inline":
            return f"<script>{get_plotlyjs()}</script>"
        return f'<script src="{PLOTLY_CDN_URL}"></script>'

    def _template(
        self,
        title: str,
        tab_buttons: str,
        tab_contents: str,
        plotly_script: str,
    ) -> str:
        config = self._config

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{plotly_script}
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:{config.background_color};color:{config.text_primary};font-family:{config.font_family};min-height:100vh}}
  header{{background:{config.surface_color};border-bottom:1px solid {config.grid_color};padding:18px 32px;display:flex;align-items:center;gap:12px}}
  header h1{{font-size:17px;font-weight:600;letter-spacing:-0.3px}}
  header span{{font-size:12px;color:{config.text_secondary};background:{config.background_color};border:1px solid {config.grid_color};border-radius:4px;padding:2px 8px}}
  .tab-bar{{background:{config.surface_color};border-bottom:1px solid {config.grid_color};padding:0 32px;display:flex;gap:4px;flex-wrap:wrap}}
  .tab-btn{{background:none;border:none;border-bottom:2px solid transparent;color:{config.text_secondary};cursor:pointer;font-family:{config.font_family};font-size:13px;padding:12px 16px;transition:color .15s,border-color .15s;white-space:nowrap}}
  .tab-btn:hover{{color:{config.text_primary}}}
  .tab-btn.active{{color:{config.event_palette[0]};border-bottom-color:{config.event_palette[0]};font-weight:500}}
  .tab-pane{{display:none;padding:24px 32px}}
  .tab-pane.active{{display:block}}
</style>
</head>
<body>
<header><h1>{title}</h1><span>sched_viz</span></header>
<nav class="tab-bar">{tab_buttons}</nav>
<main>{tab_contents}</main>
<script>
  function showTab(id,btn){{
    document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    btn.classList.add('active');
  }}
</script>
</body>
</html>"""
