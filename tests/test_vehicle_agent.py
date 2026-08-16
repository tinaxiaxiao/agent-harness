from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from examples.in_car_restaurant_agent import VehicleRestaurantAgent, run_scenario
from runtime.models import RunContext, RunState
from tools import ToolError


class VehicleAgentTests(unittest.TestCase):
    def test_happy_path_reserves_and_navigates(self) -> None:
        result, trace = run_scenario("happy_path")
        self.assertTrue(result["task_completed"])
        self.assertTrue(result["reservation_created"])
        self.assertTrue(result["navigation_started"])
        self.assertEqual(result["unique_reservations"], 1)
        self.assertEqual(trace.events[-1]["event_type"], "run.completed")

    def test_fallback_uses_second_restaurant(self) -> None:
        result, _ = run_scenario("fallback_restaurant")
        self.assertEqual(result["selected_restaurant"], "锦城里")
        self.assertTrue(result["task_completed"])

    def test_timeout_retry_is_idempotent(self) -> None:
        result, trace = run_scenario("reservation_retry")
        self.assertEqual(result["retries"], 1)
        self.assertEqual(result["unique_reservations"], 1)
        self.assertTrue(result["reservation"]["deduplicated"])
        failures = [event for event in trace.events if event["event_type"] == "tool.call.failed"]
        self.assertEqual(failures[0]["attributes"]["code"], "upstream_timeout")

    def test_rejection_has_no_side_effects(self) -> None:
        result, trace = run_scenario("user_rejects")
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(result["reservation_created"])
        self.assertFalse(result["navigation_started"])
        self.assertFalse(any(event["event_type"] == "side_effect.committed" for event in trace.events))

    def test_location_denied_requests_input(self) -> None:
        result, _ = run_scenario("location_denied")
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["error_code"], "permission_denied")

    def test_side_effect_requires_confirmation_token(self) -> None:
        agent = VehicleRestaurantAgent("happy_path")
        with self.assertRaisesRegex(ToolError, "confirmation"):
            agent.registry.get("create_reservation").invoke(
                restaurant_id="rest_001",
                party_size=5,
                reservation_time="2026-08-16T19:10+08:00",
                room_type="private_room",
                idempotency_key="test-key",
                confirmation_token=None,
            )

    def test_trace_is_contiguous_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.jsonl"
            _, trace = run_scenario("happy_path", path)
            self.assertEqual([event["sequence"] for event in trace.events], list(range(1, len(trace.events) + 1)))
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), len(trace.events))

    def test_invalid_state_transition_is_rejected(self) -> None:
        context = RunContext("run", "trace", "test", "input")
        with self.assertRaisesRegex(ValueError, "invalid state transition"):
            context.transition(RunState.NAVIGATING)


if __name__ == "__main__":
    unittest.main()
