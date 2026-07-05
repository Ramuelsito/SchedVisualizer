from __future__ import annotations
from dataclasses import dataclass, field

DEFAULT_EVENT_PALETTE = [
    "#4C9BE8",
    "#E8834C",
    "#4CE87A",
    "#E84C6B",
    "#A04CE8",
    "#E8D44C",
    "#4CE8D4",
    "#E84CC2",
    "#8BE84C",
    "#4C6BE8",
    "#E8A84C",
    "#4CE8B0",
]
BACKGROUND_COLOR = "#0F1117"
SURFACE_COLOR = "#1A1D27"
GRID_COLOR = "#2A2D3A"
TEXT_PRIMARY = "#E8EAF0"
TEXT_SECONDARY = "#7C8098"
AXIS_COLOR = "#3A3D50"


@dataclass
class VisConfig:
    event_palette: list[str] = field(default_factory=lambda: list(DEFAULT_EVENT_PALETTE))
    background_color: str = BACKGROUND_COLOR
    surface_color: str = SURFACE_COLOR
    grid_color: str = GRID_COLOR
    text_primary: str = TEXT_PRIMARY
    text_secondary: str = TEXT_SECONDARY
    axis_color: str = AXIS_COLOR
    font_family: str = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    bar_opacity: float = 0.88
    bar_corner_radius: int = 3
    slot_width_px: int = 60
    actor_row_height: int = 36
    fig_height_per_actor: int = 40
    fig_min_height: int = 300
    fig_width: int = 1200
