from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

from ..config import VisConfig


LabeledFigure = tuple[str, go.Figure]


class DashboardExporter:
    def __init__(self, config: VisConfig) -> None:
        self._config = config

    def export(
        self,
        path: str | Path,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> None:
        html = self.build_html(figures=figures, title=title)
        Path(path).write_text(html, encoding="utf-8")

    def build_html(
        self,
        figures: Sequence[LabeledFigure],
        title: str,
    ) -> str:
        if not figures:
            raise ValueError("Dashboard must contain at least one figure")

        safe_title = escape(title)
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
                f'onclick="showTab(\'tab-{index}\', this)">{safe_label}</button>'
            )
            panes.append(
                f'<div id="tab-{index}" class="tab-pane{active}">'
                f"{figure_html}</div>"
            )

        return self._template(
            title=safe_title,
            tab_buttons="".join(buttons),
            tab_contents="".join(panes),
            figures=figures,
        )

    def _template(self, title: str, tab_buttons: str, tab_contents: str, figures: Sequence[LabeledFigure]) -> str:
        bg, surf, txt, txt2, grid, acc, font = (
        self._config.background_color, self._config.surface_color, self._config.text_primary,
        self._config.text_secondary, self._config.grid_color, self._config.event_palette[0], self._config.font_family
    )
        tab_buttons = ""
        tab_contents = ""
        for i, (name, fig) in enumerate(figures):
            active = "active" if i == 0 else ""
            chart_html = pio.to_html(fig, full_html=False, include_plotlyjs=False)
            tab_buttons += f'''
            <button class="tab-btn {active}" onclick="showTab('tab-{i}', this)">{name}</button>'''
            tab_contents += f'''
            <div id="tab-{i}" class="tab-pane {active}">{chart_html}</div>'''

        return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:{bg};color:{txt};font-family:{font};min-height:100vh}}
    header{{background:{surf};border-bottom:1px solid {grid};padding:18px 32px;display:flex;align-items:center;gap:12px}}
    header h1{{font-size:17px;font-weight:600;letter-spacing:-0.3px}}
    header span{{font-size:12px;color:{txt2};background:{bg};border:1px solid {grid};border-radius:4px;padding:2px 8px}}
    .tab-bar{{background:{surf};border-bottom:1px solid {grid};padding:0 32px;display:flex;gap:4px;flex-wrap:wrap}}
    .tab-btn{{background:none;border:none;border-bottom:2px solid transparent;color:{txt2};cursor:pointer;font-family:{font};font-size:13px;padding:12px 16px;transition:color .15s,border-color .15s;white-space:nowrap}}
    .tab-btn:hover{{color:{txt}}}
    .tab-btn.active{{color:{acc};border-bottom-color:{acc};font-weight:500}}
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
