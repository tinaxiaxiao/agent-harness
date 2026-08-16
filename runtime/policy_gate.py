from __future__ import annotations

import hashlib

from .trace import TraceWriter


class PolicyGate:
    """Issues scoped confirmation tokens before external side effects."""

    def __init__(self, trace: TraceWriter) -> None:
        self.trace = trace
        self._tokens: dict[str, str] = {}

    def request(self, action_summary: dict, approved: bool) -> str | None:
        request_id = self.trace.emit(
            "confirmation.requested",
            "policy_gate",
            "started",
            attributes=action_summary,
        )
        status = "success" if approved else "cancelled"
        self.trace.emit(
            "confirmation.received",
            "policy_gate",
            status,
            attributes={"approved": approved},
            parent_event_id=request_id,
        )
        if not approved:
            return None
        scope = f"{action_summary['restaurant_id']}:{action_summary['reservation_time']}"
        token = hashlib.sha256(f"{self.trace.run_id}:{scope}".encode()).hexdigest()[:24]
        self._tokens[token] = scope
        return token

    def validate(self, token: str | None, restaurant_id: str, reservation_time: str) -> bool:
        if token is None:
            return False
        return self._tokens.get(token) == f"{restaurant_id}:{reservation_time}"
