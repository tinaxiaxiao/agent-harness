from __future__ import annotations

import time
from typing import Any, Callable

from tools import Tool, ToolError, ToolRegistry

from .environment import RESTAURANTS, SandboxEnvironment


class FunctionTool(Tool):
    def __init__(self, name: str, fn: Callable[..., dict[str, Any]], *, side_effect: bool = False) -> None:
        self.name = name
        self.fn = fn
        self.side_effect = side_effect

    def invoke(self, **arguments: Any) -> dict[str, Any]:
        return self.fn(**arguments)


def build_registry(environment: SandboxEnvironment, confirmation_validator: Callable[[str | None, str, str], bool]) -> ToolRegistry:
    registry = ToolRegistry()

    def get_current_location() -> dict[str, Any]:
        _latency(6)
        if environment.scenario == "location_denied":
            raise ToolError("permission_denied", "vehicle location permission is unavailable")
        return {
            "location_id": "vehicle_location_001",
            "district": "上海市徐汇区",
            "coordinates_ref": "synthetic://location/001",
        }

    def search_restaurants(
        cuisine: str,
        location_id: str,
        radius_m: int,
        party_size: int,
        private_room_required: bool,
    ) -> dict[str, Any]:
        _latency(12)
        matches = [
            dict(item)
            for item in RESTAURANTS
            if item["cuisine"] == cuisine
            and item["distance_m"] <= radius_m
            and item["open_now"]
            and (not private_room_required or item["private_room_capacity"] >= party_size)
        ]
        matches.sort(key=lambda item: (item["distance_m"], -item["rating"]))
        return {"location_id": location_id, "restaurants": matches}

    def get_route(origin_location_id: str, destination_id: str) -> dict[str, Any]:
        _latency(9)
        restaurant = _restaurant(destination_id)
        minutes = max(8, round(restaurant["distance_m"] / 180))
        return {
            "route_id": f"route_{destination_id}",
            "origin_location_id": origin_location_id,
            "destination_id": destination_id,
            "distance_m": restaurant["distance_m"],
            "eta_minutes": minutes,
        }

    def check_reservation_availability(
        restaurant_id: str,
        party_size: int,
        arrival_window: str,
    ) -> dict[str, Any]:
        _latency(11)
        return {
            "restaurant_id": restaurant_id,
            "party_size": party_size,
            "arrival_window": arrival_window,
            "available": environment.room_available(restaurant_id),
            "room_type": "private_room",
            "cancellation_policy": "提前 30 分钟可取消",
        }

    def create_reservation(
        restaurant_id: str,
        party_size: int,
        reservation_time: str,
        room_type: str,
        idempotency_key: str,
        confirmation_token: str | None,
    ) -> dict[str, Any]:
        _latency(14)
        if not confirmation_validator(confirmation_token, restaurant_id, reservation_time):
            raise ToolError("confirmation_required", "reservation requires a matching confirmation token")
        with environment.lock:
            if idempotency_key in environment.reservations:
                return {**environment.reservations[idempotency_key], "deduplicated": True}
            reservation = {
                "reservation_id": f"booking_{len(environment.reservations) + 1:03d}",
                "restaurant_id": restaurant_id,
                "party_size": party_size,
                "reservation_time": reservation_time,
                "room_type": room_type,
                "status": "confirmed",
                "deduplicated": False,
            }
            environment.reservations[idempotency_key] = reservation
            attempt = environment.reservation_attempts.get(idempotency_key, 0) + 1
            environment.reservation_attempts[idempotency_key] = attempt
            if environment.scenario == "reservation_retry" and attempt == 1:
                raise ToolError(
                    "upstream_timeout",
                    "reservation outcome unknown after upstream timeout",
                    transient=True,
                )
            return reservation

    def start_navigation(
        destination_id: str,
        route_id: str,
        reservation_time: str,
        confirmation_token: str | None,
    ) -> dict[str, Any]:
        _latency(5)
        if not confirmation_validator(confirmation_token, destination_id, reservation_time):
            raise ToolError("confirmation_required", "navigation requires a matching confirmation token")
        navigation = {
            "navigation_id": f"nav_{len(environment.navigations) + 1:03d}",
            "destination_id": destination_id,
            "route_id": route_id,
            "status": "started",
        }
        environment.navigations.append(navigation)
        return navigation

    registry.register(FunctionTool("get_current_location", get_current_location))
    registry.register(FunctionTool("search_restaurants", search_restaurants))
    registry.register(FunctionTool("get_route", get_route))
    registry.register(FunctionTool("check_reservation_availability", check_reservation_availability))
    registry.register(FunctionTool("create_reservation", create_reservation, side_effect=True))
    registry.register(FunctionTool("start_navigation", start_navigation, side_effect=True))
    return registry


def _restaurant(restaurant_id: str) -> dict[str, Any]:
    for restaurant in RESTAURANTS:
        if restaurant["restaurant_id"] == restaurant_id:
            return restaurant
    raise ToolError("not_found", f"unknown restaurant: {restaurant_id}")


def _latency(milliseconds: int) -> None:
    time.sleep(milliseconds / 1000)
