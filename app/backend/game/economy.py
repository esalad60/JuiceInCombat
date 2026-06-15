from __future__ import annotations

from .state import GameState


FLAT_INCOME_PER_TURN: dict[str, int] = {
    "cash": 50,
}

BUILDING_INCOME: dict[str, dict[str, int]] = {
    "presia_hq": {"cash": 50},
    "doon_hq":   {"cash": 50},
}


def preview_income(state: GameState, player_slot: int) -> dict[str, int]:
    tick: dict[str, int] = {}
    for resource, amount in FLAT_INCOME_PER_TURN.items():
        tick[resource] = tick.get(resource, 0) + amount
    for building in state.buildings_for(player_slot):
        amount = getattr(building, "income", 0)
        if amount:
            tick["cash"] = tick.get("cash", 0) + amount
            continue
        per_building = BUILDING_INCOME.get(building.type)
        if not per_building:
            continue
        for resource, amt in per_building.items():
            tick[resource] = tick.get(resource, 0) + amt
    return tick


def tick_income(state: GameState, player_slot: int) -> dict[str, int]:
    player = state.get_player(player_slot)
    tick: dict[str, int] = {}

    for resource, amount in FLAT_INCOME_PER_TURN.items():
        tick[resource] = tick.get(resource, 0) + amount

    for building in state.buildings_for(player_slot):
        amount = getattr(building, "income", 0)
        if amount:
            tick["cash"] = tick.get("cash", 0) + amount
            continue

        per_building = BUILDING_INCOME.get(building.type)
        if not per_building:
            continue
        for resource, amt in per_building.items():
            tick[resource] = tick.get(resource, 0) + amt

    for resource, amount in tick.items():
        player.resources[resource] = player.resources.get(resource, 0) + amount

    return tick


def can_afford(state: GameState, player_slot: int, cost: int) -> bool:
    return state.get_player(player_slot).resources.get("cash", 0) >= cost


def spend(state: GameState, player_slot: int, cost: int) -> None:
    player = state.get_player(player_slot)
    if player.resources.get("cash", 0) < cost:
        raise ValueError(f"Cannot afford {cost} cash")
    player.resources["cash"] -= cost