from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from runtime import Executor, PolicyGate, RunContext, RunState, TraceWriter
from tools import ToolError
from tools.sandbox import SandboxEnvironment, build_registry

from .planner import parse_vehicle_request, plan_steps


DEFAULT_UTTERANCE = "帮我就近找家有五人包间的川菜馆，导航过去并帮我同步先预定下包间"
SIMULATED_NOW = datetime(2026, 8, 16, 18, 52, tzinfo=timezone(timedelta(hours=8)))


class VehicleRestaurantAgent:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        digest = hashlib.sha1(scenario.encode()).hexdigest()[:10]
        self.context = RunContext(
            run_id=f"run_{digest}",
            trace_id=f"trace_{digest}",
            scenario=scenario,
            user_input=DEFAULT_UTTERANCE,
        )
        self.trace = TraceWriter(self.context.trace_id, self.context.run_id)
        self.policy_gate = PolicyGate(self.trace)
        self.environment = SandboxEnvironment.for_scenario(scenario)
        self.registry = build_registry(self.environment, self.policy_gate.validate)
        self.executor = Executor(self.registry, self.trace)
        self.started = 0.0

    def run(self, transcript: str = DEFAULT_UTTERANCE) -> dict[str, Any]:
        self.started = time.perf_counter()
        self.trace.emit(
            "run.started",
            "runtime",
            "started",
            attributes={"scenario": self.scenario, "environment": "sandbox"},
        )
        self.trace.emit(
            "input.received",
            "perception",
            "success",
            attributes={"modality": "voice", "audio_ref": "synthetic://voice/utterance_001"},
        )
        self.trace.emit(
            "speech.transcribed",
            "perception",
            "success",
            attributes={"transcript": transcript, "asr_mode": "fixture"},
        )

        intent = parse_vehicle_request(transcript)
        self.context.values["intent"] = intent
        self.trace.emit("intent.parsed", "planner", "success", attributes=intent)
        self._transition(RunState.PARSED)
        steps = plan_steps(intent)
        self.trace.emit("plan.created", "planner", "success", attributes={"steps": steps})

        try:
            location = self.executor.execute("get_current_location")
        except ToolError as exc:
            self._transition(RunState.NEEDS_INPUT)
            return self._finish(
                "needs_input",
                task_completed=False,
                message="无法获取当前位置，请授权定位或告诉我您所在的位置。",
                error_code=exc.code,
            )
        self.context.values["location"] = location
        self._transition(RunState.LOCATED)
        self._transition(RunState.SEARCHING)

        search = self.executor.execute(
            "search_restaurants",
            cuisine=intent["cuisine"],
            location_id=location["location_id"],
            radius_m=6000,
            party_size=intent["party_size"],
            private_room_required=intent["private_room_required"],
        )
        candidates = search["restaurants"]
        if not candidates:
            self._transition(RunState.NEEDS_INPUT)
            return self._finish(
                "needs_input",
                task_completed=False,
                message="附近暂未找到满足条件的川菜馆，要扩大搜索范围吗？",
            )
        self._transition(RunState.SELECTING)

        selected: dict[str, Any] | None = None
        selected_route: dict[str, Any] | None = None
        availability: dict[str, Any] | None = None
        for candidate in candidates:
            self._transition(RunState.PREPARING)
            with ThreadPoolExecutor(max_workers=2) as pool:
                route_future = pool.submit(
                    self.executor.execute,
                    "get_route",
                    origin_location_id=location["location_id"],
                    destination_id=candidate["restaurant_id"],
                )
                availability_future = pool.submit(
                    self.executor.execute,
                    "check_reservation_availability",
                    restaurant_id=candidate["restaurant_id"],
                    party_size=intent["party_size"],
                    arrival_window="estimated_arrival",
                )
                route = route_future.result()
                room = availability_future.result()
            if room["available"]:
                selected, selected_route, availability = candidate, route, room
                break
            self._transition(RunState.SELECTING)

        if selected is None or selected_route is None or availability is None:
            if self.context.state is RunState.PREPARING:
                self._transition(RunState.NEEDS_INPUT)
            return self._finish(
                "needs_input",
                task_completed=False,
                message="附近川菜馆目前都没有五人包间，要改订大厅座位吗？",
            )

        reservation_time = (SIMULATED_NOW + timedelta(minutes=selected_route["eta_minutes"]))
        reservation_time_text = reservation_time.isoformat(timespec="minutes")
        self.context.values.update(
            restaurant=selected,
            route=selected_route,
            availability=availability,
            reservation_time=reservation_time_text,
        )
        self._transition(RunState.CONFIRMING)
        confirmation_summary = {
            "restaurant_id": selected["restaurant_id"],
            "restaurant_name": selected["name"],
            "distance_m": selected_route["distance_m"],
            "eta_minutes": selected_route["eta_minutes"],
            "party_size": intent["party_size"],
            "room_type": availability["room_type"],
            "reservation_time": reservation_time_text,
            "cancellation_policy": availability["cancellation_policy"],
        }
        token = self.policy_gate.request(confirmation_summary, self.environment.user_confirms)
        if token is None:
            self._transition(RunState.CANCELLED)
            return self._finish(
                "cancelled",
                task_completed=False,
                message="已取消，本次没有预订，也没有启动导航。",
                selected_restaurant=selected["name"],
            )

        self._transition(RunState.RESERVING)
        retry_before = self.executor.retry_count
        idempotency_key = hashlib.sha256(
            f"{self.context.run_id}:{selected['restaurant_id']}:{reservation_time_text}".encode()
        ).hexdigest()[:24]
        try:
            reservation = self.executor.execute(
                "create_reservation",
                retries=1,
                restaurant_id=selected["restaurant_id"],
                party_size=intent["party_size"],
                reservation_time=reservation_time_text,
                room_type=availability["room_type"],
                idempotency_key=idempotency_key,
                confirmation_token=token,
            )
        except ToolError as exc:
            self._transition(RunState.FAILED)
            return self._finish(
                "failed",
                task_completed=False,
                message="包间预订失败，未启动导航。",
                error_code=exc.code,
            )
        if self.executor.retry_count > retry_before:
            self._transition(RunState.RECOVERING)
        self._transition(RunState.NAVIGATING)
        navigation = self.executor.execute(
            "start_navigation",
            destination_id=selected["restaurant_id"],
            route_id=selected_route["route_id"],
            reservation_time=reservation_time_text,
            confirmation_token=token,
        )
        self._transition(RunState.COMPLETED)
        message = (
            f"已为 5 人预订{selected['name']}包间，预计 {reservation_time.strftime('%H:%M')} 到达，"
            "导航已开始。"
        )
        return self._finish(
            "success",
            task_completed=True,
            message=message,
            selected_restaurant=selected["name"],
            reservation=reservation,
            navigation=navigation,
        )

    def _transition(self, next_state: RunState) -> None:
        previous, current = self.context.transition(next_state)
        self.trace.emit(
            "state.changed",
            "runtime",
            "success",
            attributes={"from": previous.value, "to": current.value},
        )

    def _finish(self, status: str, *, task_completed: bool, message: str, **details: Any) -> dict[str, Any]:
        duration_ms = int((time.perf_counter() - self.started) * 1000)
        output_status = "success" if status == "success" else status
        self.trace.emit(
            "agent.output",
            "runtime",
            output_status,
            attributes={"message": message},
        )
        result = {
            "scenario": self.scenario,
            "status": status,
            "task_completed": task_completed,
            "reservation_created": bool(self.environment.reservations),
            "navigation_started": bool(self.environment.navigations),
            "unique_reservations": len(self.environment.reservations),
            "tool_calls": self.trace.count("tool.call.started"),
            "retries": self.executor.retry_count,
            "total_duration_ms": duration_ms,
            "message": message,
            **details,
        }
        completion_status = {
            "success": "success",
            "cancelled": "cancelled",
            "needs_input": "needs_input",
            "failed": "failed",
        }[status]
        self.trace.emit(
            "run.completed" if status != "failed" else "run.failed",
            "runtime",
            completion_status,
            duration_ms=duration_ms,
            attributes={k: v for k, v in result.items() if k not in {"reservation", "navigation"}},
        )
        return result


def run_scenario(
    scenario: str,
    output_path: str | Path | None = None,
    transcript: str = DEFAULT_UTTERANCE,
) -> tuple[dict[str, Any], TraceWriter]:
    agent = VehicleRestaurantAgent(scenario)
    result = agent.run(transcript)
    if output_path is not None:
        agent.trace.save(output_path)
    return result, agent.trace
