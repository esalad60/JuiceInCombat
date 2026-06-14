from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from . import combat, elevation, pathfinding, turn_order, economy, fog
from .state import Building, GameState, Unit

from .unit import UnitRegistry


class ActionError(ValueError):
    """Raised when an action is illegal. The socket layer
    catches this and emits a clean error to the client."""

UNIT_REGISTRY: "UnitRegistry | None" = None

def set_unit_registry(registry: "UnitRegistry") -> None:
    global UNIT_REGISTRY
    UNIT_REGISTRY = registry


def validate(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> None:
    action_type = get_action_type(action)
    validator = VALIDATORS.get(action_type)
    if validator is None:
        raise ActionError(f"Unknown action type: {action_type!r}")
    validator(state, player_slot, action)


def apply(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> dict[str, Any]:
    action_type = get_action_type(action)
    applier = APPLIERS.get(action_type)
    if applier is None:
        raise ActionError(f"Unknown action type: {action_type!r}")
    result = applier(state, player_slot, action)
    for k in [key for key in action if key.startswith("_resolved")]:
        action.pop(k, None)
    return result


def get_action_type(action: dict[str, Any]) -> str:
    if "type" not in action:
        raise ActionError("Action missing 'type'")
    return action["type"]


def fetch(action: dict[str, Any], key: str) -> int:
    return action[key]


def get_xy(action: dict[str, Any], key: str) -> tuple[int, int]:
    x, y = action[key]
    return x, y


def require_unit(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> "Unit":
    unit_id = fetch(action, "unit_id")
    unit = state.get_unit(unit_id)
    if unit is None:
        raise ActionError(f"No such unit: {unit_id}")
    if unit.owner_slot != player_slot:
        raise ActionError(f"Unit {unit_id} is not yours")
    return unit


def validate_move(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> None:
    unit = require_unit(state, player_slot, action)
    to_x, to_y = get_xy(action, "to")

    if not state.game_map.in_bounds(to_x, to_y):
        raise ActionError(f"Destination ({to_x},{to_y}) out of bounds")

    dest_tile = state.game_map.tile_at(to_x, to_y)

    if dest_tile.unit_id is not None and dest_tile.unit_id != unit.id:
        raise ActionError("Destination is occupied by another unit")

    if dest_tile.building_id is not None:
        building = state.get_building(dest_tile.building_id)
        if building is not None:
            if building.owner_slot != player_slot and not building.is_capital:
                raise ActionError("Cannot move onto an enemy building")

    # Check path
    path = pathfinding.find_path(state.game_map, unit, to_x, to_y)
    if not path:
        raise ActionError("No legal path to destination")

    cost = pathfinding.path_cost(state.game_map, unit, path)
    if cost > unit.movement_remaining:
        raise ActionError(
            f"Not enough movement ({cost} needed, {unit.movement_remaining} left)"
        )

    # Store resolved data for apply
    action["_resolved_path"] = path
    action["_resolved_cost"] = cost


def apply_move(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> dict[str, Any]:
    unit = state.get_unit(action["unit_id"])
    if unit is None:
        raise RuntimeError("Unit disappeared")  # should not happen
    to_x, to_y = action["to"]
    path = action["_resolved_path"]
    cost = action["_resolved_cost"]

    dest_tile = state.game_map.tile_at(to_x, to_y)
    captured_building_id: int | None = None

    if dest_tile.building_id is not None:
        building = state.get_building(dest_tile.building_id)
        if building is not None and building.is_capital and building.owner_slot != player_slot:
            state.transfer_building(building.id, player_slot)
            captured_building_id = building.id

    state.move_unit(unit.id, to_x, to_y)
    turn_order.commit_move(unit, distance=int(cost))

    result: dict[str, Any] = {
        "path": [list(p) for p in path],
        "cost": cost,
        "unit_id": unit.id,
        "to": [to_x, to_y],
        "movement_remaining": unit.movement_remaining,
    }
    if captured_building_id is not None:
        result["captured_building_id"] = captured_building_id
        result["captured_from_slot"] = next(
            (i for i, p in enumerate(state.players) if p.capital_building_id == captured_building_id),
            None,
        )
    return result


def validate_fire(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> None:
    unit = require_unit(state, player_slot, action)
    target_x, target_y = get_xy(action, "target_xy")

    if not state.game_map.in_bounds(target_x, target_y):
        raise ActionError(f"Target ({target_x},{target_y}) out of bounds")

    weapon_name = action.get("weapon_name")
    weapon = next((w for w in unit.weapons if w.name == weapon_name), None)
    if weapon is None:
        raise ActionError(f"Unit has no weapon named {weapon_name!r}")

    if unit.has_fired_weapon:
        raise ActionError("Unit has already fired this turn")

    dx = abs(target_x - unit.x)
    dy = abs(target_y - unit.y)
    distance = dx + dy
    if distance > weapon.range:
        raise ActionError(f"Target out of range ({distance} > {weapon.range})")

    target_tile = state.game_map.tile_at(target_x, target_y)
    target_kind, target = resolve_target_on_tile(state, target_tile)

    action["_resolved_target_kind"] = target_kind
    action["_resolved_target_id"] = target.id if target is not None else None
    action["_resolved_target_xy"] = [target_x, target_y]


def apply_fire(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> dict[str, Any]:
    unit = state.get_unit(action["unit_id"])
    if unit is None:
        pass
    weapon_name = action["weapon_name"]
    weapon = next(w for w in unit.weapons if w.name == weapon_name)

    target_kind = action["_resolved_target_kind"]
    target_id = action["_resolved_target_id"]
    if target_kind == "unit":
        target = state.get_unit(target_id)
    elif target_kind == "building":
        target = state.get_building(target_id)
    else:
        target = None
        
    if target is None:
        turn_order.commit_fire(unit)

        return {
            "attacker_id": unit.id,
            "target_id": None,
            "target_kind": None,
            "weapon_name": weapon.name,
            "target_xy": [target_x, target_y],
            "result": "miss",
            "raw_damage": 0,
            "final_damage": 0,
            "target_destroyed": False,
            "perks_applied": [],
        }

    fire_result = combat.fire_weapon(
        state, attacker=unit, weapon=weapon, target=target,
    )
    turn_order.commit_fire(unit)

    return {
        "attacker_id": fire_result.attacker_id,
        "target_id": fire_result.target_id,
        "target_kind": fire_result.target_kind,
        "weapon_name": fire_result.weapon_name,
        "raw_damage": fire_result.raw_damage,
        "final_damage": fire_result.final_damage,
        "target_destroyed": fire_result.target_destroyed,
        "perks_applied": fire_result.perks_applied,
    }


def validate_recruit(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> None:
    unit_type = action.get("unit_type")
    if not unit_type:
        raise ActionError("Recruit action missing 'unit_type'")

    x, y = get_xy(action, "to")

    if not state.game_map.in_bounds(x, y):
        raise ActionError(f"Spawn tile ({x},{y}) out of bounds")

    tile = state.game_map.tile_at(x, y)

    if tile.unit_id is not None:
        raise ActionError("Spawn tile is already occupied")

    # find player's HQ / capital
    player = state.get_player(player_slot)

    if player.capital_building_id is None:
        raise ActionError("No HQ found")

    hq = state.get_building(player.capital_building_id)

    if hq is None:
        raise ActionError("HQ building missing")

    dx = abs(x - hq.x)
    dy = abs(y - hq.y)

    if max(dx, dy) != 1:
        raise ActionError("Recruit tile must be adjacent to HQ")

    hq_tile = state.game_map.tile_at(hq.x, hq.y)

    if tile.height != hq_tile.height:
        raise ActionError(
            "Recruit tile must be on same elevation as HQ"
        )

    if tile.base == "ocean":
        raise ActionError("Cannot recruit on water")

    if UNIT_REGISTRY is None:
        raise ActionError("Unit registry not initialized")

    faction = state.get_player(player_slot).faction
    definition = UNIT_REGISTRY.get(faction, unit_type)

    if definition is None:
        raise ActionError(
            f"No such unit '{unit_type}' for faction '{faction}'"
        )

    # money
    if not economy.can_afford(
        state,
        player_slot,
        definition.price
    ):
        raise ActionError(
            f"Not enough cash ({definition.price} needed)"
        )

    action["_resolved_definition"] = definition
    action["_resolved_cost"] = definition.price


def apply_recruit(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> dict[str, Any]:
    definition = action["_resolved_definition"]
    cost = action["_resolved_cost"]
    x, y = action["to"]

    # Deduct cost
    economy.spend(state, player_slot, cost)

    # Spawn unit
    unit = state.spawn_unit_from_definition(
        definition, owner_slot=player_slot, x=x, y=y
    )

    return {
        "unit_id": unit.id,
        "unit_type": definition.unit_type,
        "position": [x, y],
        "cost": cost,
    }


def validate_end_turn(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> None:
    pass


def apply_end_turn(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> dict[str, Any]:
    return {"ended": True}


def resolve_target_on_tile(
    state: "GameState",
    tile,
):
    if tile.unit_id is not None:
        unit = state.get_unit(tile.unit_id)
        if unit is not None and unit.owner_slot != attacker_slot:
            return unit, state.get_unit(tile.unit_id)
    if tile.building_id is not None:
        b = state.get_building(tile.building_id)
        if b is not None and b.owner_slot != attacker_slot:
            return b, state.get_building(tile.building_id)
    return None, None



def validate_capture(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> None:
    unit_id = action.get("unit_id")
    if unit_id is None:
        raise ActionError("Capture action missing 'unit_id'")

    unit = state.get_unit(unit_id)
    if unit is None:
        raise ActionError("Capturing unit not found")
    if unit.owner_slot != player_slot:
        raise ActionError("Cannot capture with an enemy unit")

    if unit.has_moved:
        raise ActionError("Unit has already moved; cannot capture this turn")

    building_id = action.get("building_id")
    if building_id is not None:
        building = state.get_building(building_id)
    else:
        building = None

    if building is None:
        raise ActionError("Target building not found")

    dist = abs(building.x - unit.x) + abs(building.y - unit.y)
    if dist != 1:
        raise ActionError("Unit must be adjacent to the building to capture it")

    if building.owner_slot == player_slot:
        raise ActionError("You already own this building")

    action["_resolved_building_id"] = building.id


def apply_capture(
    state: "GameState",
    player_slot: int,
    action: dict[str, Any],
) -> dict[str, Any]:
    unit = state.get_unit(action["unit_id"])
    building_id = action.get("_resolved_building_id", action.get("building_id"))
    building = state.get_building(building_id)

    prev_owner = building.owner_slot
    state.transfer_building(building.id, player_slot)

    unit.has_moved = True
    unit.movement_remaining = 0

    return {
        "captured_building_id": building.id,
        "captured_from_slot": prev_owner,
        "unit_id": unit.id,
        "by_slot": player_slot,
    }


VALIDATORS: dict[str, Callable[..., None]] = {
    "move": validate_move,
    "fire": validate_fire,
    "recruit": validate_recruit,
    "capture": validate_capture,
    "end_turn": validate_end_turn,
}

APPLIERS: dict[str, Callable[..., dict[str, Any]]] = {
    "move": apply_move,
    "fire": apply_fire,
    "recruit": apply_recruit,
    "capture": apply_capture,
    "end_turn": apply_end_turn,
}