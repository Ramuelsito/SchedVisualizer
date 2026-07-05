from __future__ import annotations
from ..config import VisConfig


class ColorRegistry:
    def __init__(self, config: VisConfig):
        self._palette = config.event_palette
        self._cache: dict[str, str] = {}

    def build(self, event_ids: set[str]) -> dict[str, str]:
        new_ids = sorted(event_ids - set(self._cache))
        base = len(self._cache)
        for i, eid in enumerate(new_ids):
            self._cache[eid] = self._palette[(base + i) % len(self._palette)]
        return dict(self._cache)

    def get(self, event_id: str) -> str:
        return self._cache[event_id]

    def reset(self):
        self._cache.clear()
