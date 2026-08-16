from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RunState(StrEnum):
    RECEIVED = "received"
    PARSED = "parsed"
    LOCATED = "located"
    SEARCHING = "searching"
    SELECTING = "selecting"
    PREPARING = "preparing"
    CONFIRMING = "confirming"
    RESERVING = "reserving"
    RECOVERING = "recovering"
    NAVIGATING = "navigating"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.RECEIVED: {RunState.PARSED},
    RunState.PARSED: {RunState.LOCATED, RunState.NEEDS_INPUT},
    RunState.LOCATED: {RunState.SEARCHING},
    RunState.SEARCHING: {RunState.SELECTING, RunState.NEEDS_INPUT},
    RunState.SELECTING: {RunState.PREPARING, RunState.NEEDS_INPUT},
    RunState.PREPARING: {RunState.SELECTING, RunState.CONFIRMING, RunState.NEEDS_INPUT},
    RunState.CONFIRMING: {RunState.RESERVING, RunState.CANCELLED},
    RunState.RESERVING: {RunState.RECOVERING, RunState.NAVIGATING, RunState.FAILED},
    RunState.RECOVERING: {RunState.RESERVING, RunState.NAVIGATING, RunState.FAILED},
    RunState.NAVIGATING: {RunState.COMPLETED, RunState.FAILED},
    RunState.COMPLETED: set(),
    RunState.CANCELLED: set(),
    RunState.NEEDS_INPUT: set(),
    RunState.FAILED: set(),
}


@dataclass
class RunContext:
    run_id: str
    trace_id: str
    scenario: str
    user_input: str
    state: RunState = RunState.RECEIVED
    values: dict[str, Any] = field(default_factory=dict)

    def transition(self, next_state: RunState) -> tuple[RunState, RunState]:
        if next_state not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid state transition: {self.state} -> {next_state}")
        previous = self.state
        self.state = next_state
        return previous, next_state
