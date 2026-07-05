"""Registry used to discover chart implementations by stable name."""

from __future__ import annotations

from collections.abc import Iterable

from .base import Chart


class ChartRegistry:
    def __init__(self, charts: Iterable[Chart] = ()) -> None:
        self._charts: dict[str, Chart] = {}
        for chart in charts:
            self.register(chart)

    def register(self, chart: Chart) -> None:
        if chart.name in self._charts:
            raise ValueError(f"Chart already registered: {chart.name!r}")
        self._charts[chart.name] = chart

    def get(self, name: str) -> Chart:
        try:
            return self._charts[name]
        except KeyError as exc:
            available = ", ".join(self.names())
            raise ValueError(f"Unknown chart: {name!r}. Available: [{available}]") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(self._charts)
