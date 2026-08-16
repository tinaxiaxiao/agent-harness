from __future__ import annotations

import time
from typing import Any

from tools import ToolError, ToolRegistry

from .trace import TraceWriter


class Executor:
    def __init__(self, registry: ToolRegistry, trace: TraceWriter) -> None:
        self.registry = registry
        self.trace = trace
        self.retry_count = 0

    def execute(self, name: str, *, retries: int = 0, **arguments: Any) -> dict[str, Any]:
        tool = self.registry.get(name)
        attempt = 0
        while True:
            attempt += 1
            started = time.perf_counter()
            parent = self.trace.emit(
                "tool.call.started",
                name,
                "started",
                attributes={"attempt": attempt, "arguments": _safe_arguments(arguments)},
                side_effect=tool.side_effect,
            )
            if tool.side_effect:
                self.trace.emit(
                    "side_effect.started",
                    name,
                    "started",
                    attributes={"attempt": attempt},
                    parent_event_id=parent,
                    side_effect=True,
                )
            try:
                result = tool.invoke(**arguments)
            except ToolError as exc:
                duration = int((time.perf_counter() - started) * 1000)
                self.trace.emit(
                    "tool.call.failed",
                    name,
                    "failed",
                    duration_ms=duration,
                    attributes={"attempt": attempt, "code": exc.code, "transient": exc.transient},
                    parent_event_id=parent,
                    side_effect=tool.side_effect,
                )
                if attempt <= retries and exc.transient:
                    self.retry_count += 1
                    continue
                if tool.side_effect:
                    self.trace.emit(
                        "side_effect.rejected",
                        name,
                        "failed",
                        attributes={"code": exc.code},
                        parent_event_id=parent,
                        side_effect=True,
                    )
                raise
            duration = int((time.perf_counter() - started) * 1000)
            status = "recovered" if attempt > 1 else "success"
            self.trace.emit(
                "tool.call.completed",
                name,
                status,
                duration_ms=duration,
                attributes={"attempt": attempt, "result": result},
                parent_event_id=parent,
                side_effect=tool.side_effect,
            )
            if tool.side_effect:
                self.trace.emit(
                    "side_effect.committed",
                    name,
                    status,
                    duration_ms=duration,
                    attributes={"attempt": attempt, "resource_id": result.get("reservation_id") or result.get("navigation_id")},
                    parent_event_id=parent,
                    side_effect=True,
                )
            return result


def _safe_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    safe = dict(arguments)
    if "confirmation_token" in safe:
        safe["confirmation_token"] = "[REDACTED]"
    return safe
