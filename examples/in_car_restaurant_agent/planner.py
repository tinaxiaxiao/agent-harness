from __future__ import annotations


def parse_vehicle_request(transcript: str) -> dict:
    """Extract the constrained intent used by the week-one vehicle demo."""
    normalized = transcript.replace(" ", "")
    return {
        "intent": "find_reserve_and_navigate",
        "cuisine": "川菜" if "川菜" in normalized else "unknown",
        "party_size": 5 if "五人" in normalized or "5人" in normalized else None,
        "private_room_required": "包间" in normalized,
        "location_strategy": "near_current_location" if "就近" in normalized else "unspecified",
        "reservation_time_strategy": "estimated_arrival_time",
        "navigation_required": "导航" in normalized,
    }


def plan_steps(intent: dict) -> list[str]:
    if intent["intent"] != "find_reserve_and_navigate":
        raise ValueError("unsupported intent")
    return [
        "get_current_location",
        "search_restaurants",
        "select_candidate",
        "get_route || check_reservation_availability",
        "request_confirmation",
        "create_reservation",
        "start_navigation",
    ]
