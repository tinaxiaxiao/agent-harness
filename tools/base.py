from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolError(RuntimeError):
    def __init__(self, code: str, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.transient = transient


class Tool(ABC):
    name: str
    side_effect: bool = False

    @abstractmethod
    def invoke(self, **arguments: Any) -> dict[str, Any]:
        raise NotImplementedError
