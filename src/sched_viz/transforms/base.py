from __future__ import annotations
from typing import Protocol, TypeVar
from ..domain.solution import Solution
ViewModelT = TypeVar("ViewModelT")
class BaseTransformer(Protocol[ViewModelT]):
    def transform(self, solution: Solution) -> ViewModelT: ...
