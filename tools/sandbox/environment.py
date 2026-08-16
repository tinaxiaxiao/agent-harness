from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


RESTAURANTS = [
    {
        "restaurant_id": "rest_001",
        "name": "蜀香小院",
        "cuisine": "川菜",
        "distance_m": 3200,
        "rating": 4.6,
        "private_room_capacity": 6,
        "open_now": True,
    },
    {
        "restaurant_id": "rest_002",
        "name": "锦城里",
        "cuisine": "川菜",
        "distance_m": 4100,
        "rating": 4.7,
        "private_room_capacity": 8,
        "open_now": True,
    },
    {
        "restaurant_id": "rest_003",
        "name": "椒香公馆",
        "cuisine": "川菜",
        "distance_m": 5600,
        "rating": 4.5,
        "private_room_capacity": 5,
        "open_now": True,
    },
    {
        "restaurant_id": "rest_004",
        "name": "江南小馆",
        "cuisine": "本帮菜",
        "distance_m": 1800,
        "rating": 4.8,
        "private_room_capacity": 6,
        "open_now": True,
    },
    {
        "restaurant_id": "rest_005",
        "name": "川味食堂",
        "cuisine": "川菜",
        "distance_m": 2100,
        "rating": 4.2,
        "private_room_capacity": 4,
        "open_now": True,
    },
]


@dataclass
class SandboxEnvironment:
    scenario: str
    user_confirms: bool = True
    reservations: dict[str, dict[str, Any]] = field(default_factory=dict)
    reservation_attempts: dict[str, int] = field(default_factory=dict)
    navigations: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def for_scenario(cls, scenario: str) -> "SandboxEnvironment":
        known = {
            "happy_path",
            "fallback_restaurant",
            "reservation_retry",
            "user_rejects",
            "location_denied",
        }
        if scenario not in known:
            raise ValueError(f"unknown scenario: {scenario}")
        return cls(scenario=scenario, user_confirms=scenario != "user_rejects")

    def room_available(self, restaurant_id: str) -> bool:
        if self.scenario == "fallback_restaurant" and restaurant_id == "rest_001":
            return False
        return restaurant_id in {"rest_001", "rest_002", "rest_003"}
