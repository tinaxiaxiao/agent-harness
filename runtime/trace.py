from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


EVENT_TYPES = {
    "run.started",
    "input.received",
    "speech.transcribed",
    "intent.parsed",
    "plan.created",
    "state.changed",
    "tool.call.started",
    "tool.call.completed",
    "tool.call.failed",
    "confirmation.requested",
    "confirmation.received",
    "side_effect.started",
    "side_effect.committed",
    "side_effect.rejected",
    "agent.output",
    "run.completed",
    "run.failed",
}

STATUSES = {"started", "success", "failed", "blocked", "cancelled", "needs_input", "recovered"}


class TraceWriter:
    """Thread-safe JSONL event collector implementing Trace Schema v0.1.0."""

    schema_version = "0.1.0"

    def __init__(self, trace_id: str, run_id: str) -> None:
        self.trace_id = trace_id
        self.run_id = run_id
        self.events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def emit(
        self,
        event_type: str,
        component: str,
        status: str,
        *,
        duration_ms: int = 0,
        attributes: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
        side_effect: bool = False,
    ) -> str:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event_type}")
        if status not in STATUSES:
            raise ValueError(f"unsupported status: {status}")
        with self._lock:
            sequence = len(self.events) + 1
            event_id = f"event_{sequence:04d}"
            event = {
                "schema_version": self.schema_version,
                "event_id": event_id,
                "trace_id": self.trace_id,
                "run_id": self.run_id,
                "sequence": sequence,
                "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "event_type": event_type,
                "component": component,
                "status": status,
                "duration_ms": max(0, int(duration_ms)),
                "parent_event_id": parent_event_id,
                "side_effect": side_effect,
                "attributes": attributes or {},
                "privacy": {"classification": "synthetic", "redacted": True},
            }
            self.events.append(event)
            return event_id

    def count(self, event_type: str) -> int:
        return sum(event["event_type"] == event_type for event in self.events)

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in self.events)
        destination.write_text(payload, encoding="utf-8")
        return destination
