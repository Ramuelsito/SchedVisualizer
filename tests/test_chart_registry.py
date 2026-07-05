import pytest

from sched_viz.charts.registry import ChartRegistry


class StubChart:
    def __init__(self, name: str) -> None:
        self.name = name
        self.label = name.title()


def test_returns_registered_chart():
    chart = StubChart("stub")
    registry = ChartRegistry([chart])
    assert registry.get("stub") is chart


def test_rejects_duplicate_names():
    registry = ChartRegistry([StubChart("stub")])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubChart("stub"))


def test_unknown_chart_lists_available_names():
    registry = ChartRegistry([StubChart("known")])
    with pytest.raises(ValueError, match="known"):
        registry.get("missing")
