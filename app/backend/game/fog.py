from __future__ import annotations

import heapq
from typing import Any
from dataclasses import asdict

from .state import GameState, GameMap, Tile, Unit, Building, unit_to_dict
from . import economy


OFFSETS_4 = ((0, -1), (1, 0), (0, 1), (-1, 0))


def vision_neighbors(game_map: GameMap, from_tile: Tile) -> list[tuple[Tile, float]]:
    out: list[tuple[Tile, float]] = []

    for dx, dy in OFFSETS_4:
        nx = from_tile.x + dx
        ny = from_tile.y + dy

        if not game_map.in_bounds(nx, ny):
            continue

        tile = game_map.tile_at(nx, ny)

        out.append((tile, 1.0))

    return out


def visible_tiles_from_unit(
    game_map: GameMap,
    unit: Unit,
) -> set[tuple[int, int]]:
    
    sight_budget = float(unit.sight)

    if sight_budget < 0:
        return {(unit.x, unit.y)}

    start = (unit.x, unit.y)
    costs: dict[tuple[int, int], float] = {start: 0.0}
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]

    while heap:
        cur_cost, pos = heapq.heappop(heap)

        if cur_cost > costs.get(pos, float("inf")):
            continue

        cur_tile = game_map.tile_at(*pos)

        for nbr, step_cost in vision_neighbors(game_map, cur_tile):
            npos = (nbr.x, nbr.y)
            new_cost = cur_cost + step_cost

            if new_cost > sight_budget:
                continue

            if new_cost < costs.get(npos, float("inf")):
                costs[npos] = new_cost
                heapq.heappush(heap, (new_cost, npos))

    return set(costs.keys())


def visible_tiles_from_building(
    game_map: GameMap,
    building: Building,
    *,
    sight: int = 1,
) -> set[tuple[int, int]]:
    visible: set[tuple[int, int]] = set()

    for y in range(building.y - sight, building.y + sight + 1):
        for x in range(building.x - sight, building.x + sight + 1):
            if not game_map.in_bounds(x, y):
                continue

            distance = abs(x - building.x) + abs(y - building.y)

            if distance <= sight:
                visible.add((x, y))

    return visible


def compute_visible_tiles_for_player(
    state: GameState,
    player_slot: int,
) -> set[tuple[int, int]]:
    visible: set[tuple[int, int]] = set()

    for unit in state.units_for(player_slot):
        visible |= visible_tiles_from_unit(state.game_map, unit)

    for building in state.buildings_for(player_slot):
        visible |= visible_tiles_from_building(state.game_map, building)

    return visible


def update_player_fog(
    state: GameState,
    player_slot: int,
) -> None:
    player = state.get_player(player_slot)

    visible = compute_visible_tiles_for_player(state, player_slot)

    player.visible_tiles = visible
    player.explored_tiles |= visible


def update_all_fog(state: GameState) -> None:
    for player in state.players:
        update_player_fog(state, player.slot)


def tile_to_player_view(
    state: GameState,
    tile: Tile,
    viewer_slot: int,
) -> dict[str, Any]:
    viewer = state.get_player(viewer_slot)
    pos = (tile.x, tile.y)

    is_visible = pos in viewer.visible_tiles
    is_explored = pos in viewer.explored_tiles

    if is_visible:
        return {
            "x": tile.x,
            "y": tile.y,
            "fog": "visible",
            "base": tile.base,
            "feature": tile.feature,
            "height": tile.height,
            "resource": tile.resource,
            "building_id": tile.building_id,
            "unit_id": tile.unit_id,
        }

    if is_explored:
        return {
            "x": tile.x,
            "y": tile.y,
            "fog": "explored",
            "base": tile.base,
            "feature": tile.feature,
            "height": tile.height,
            "resource": tile.resource,
            "building_id": tile.building_id,
            "unit_id": None,
        }

    return {
        "x": tile.x,
        "y": tile.y,
        "fog": "unexplored",
        "base": tile.base,
        "height": tile.height,
        "feature": None,
        "resource": None,
        "building_id": None,
        "unit_id": None,
    }


def unit_visible_to_player(
    state: GameState,
    unit: Unit,
    viewer_slot: int,
) -> bool:
    if unit.owner_slot == viewer_slot:
        return True

    viewer = state.get_player(viewer_slot)
    return (unit.x, unit.y) in viewer.visible_tiles


def building_visible_to_player(
    state: GameState,
    building: Building,
    viewer_slot: int,
) -> bool:
    if building.owner_slot == viewer_slot:
        return True

    viewer = state.get_player(viewer_slot)
    pos = (building.x, building.y)
    return pos in viewer.explored_tiles 


def state_to_player_view(
    state: GameState,
    viewer_slot: int,
) -> dict[str, Any]:
    update_player_fog(state, viewer_slot)

    viewer = state.get_player(viewer_slot)

    tiles = [
        tile_to_player_view(state, tile, viewer_slot)
        for tile in state.game_map.iter_tiles()
    ]

    units: dict[str, Any] = {}

    for unit_id, unit in state.units.items():
        if unit_visible_to_player(state, unit, viewer_slot):
            units[str(unit_id)] = unit_to_dict(unit)

    buildings: dict[str, Any] = {}

    for building_id, building in state.buildings.items():
        if building_visible_to_player(state, building, viewer_slot):
            buildings[str(building_id)] = asdict(building)

    return {
        "match_id": state.match_id,
        "map_id": state.map_id,
        "turn": state.turn,
        "current_player_slot": state.current_player_slot,
        "status": state.status.value,
        "winner_slot": state.winner_slot,

        "viewer_slot": viewer_slot,
        "visible_tiles": [list(t) for t in viewer.visible_tiles],
        "explored_tiles": [list(t) for t in viewer.explored_tiles],

        "game_map": {
            "width": state.game_map.width,
            "height": state.game_map.height,
            "name": state.game_map.name,
            "tiles": tiles,
            "ramps": [
                {
                    "tile_a": list(r.tile_a),
                    "tile_b": list(r.tile_b),
                    "type": r.type,
                }
                for r in state.game_map.ramps
            ],
        },

        "players": [
            {
                "slot": p.slot,
                "faction": p.faction,
                "color": p.color,
                "resources": dict(p.resources) if p.slot == viewer_slot else {},
                "income_per_turn": (
                    economy.preview_income(state, p.slot)
                    if p.slot == viewer_slot else {}
                ),
            }
            for p in state.players
        ],

        "units": units,
        "buildings": buildings,
    }


def can_player_see_tile(
    state: GameState,
    player_slot: int,
    x: int,
    y: int,
) -> bool:
    if not state.game_map.in_bounds(x, y):
        return False

    update_player_fog(state, player_slot)
    return (x, y) in state.get_player(player_slot).visible_tiles