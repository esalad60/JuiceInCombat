from __future__ import annotations

from typing import Optional

import networkx as nx
import heapq

from . import elevation
from .state import GameMap, Tile, Unit

# Add different terrain costs later
DEFAULT_TERRAIN_COST = 1.0


def base_terrain_cost(tile: "Tile") -> float:
    return DEFAULT_TERRAIN_COST

# 4 Directions (maybe do 8 later on)
# rn looks like diamond vs square
OFFSETS_4 = ((0, -1), (1, 0), (0, 1), (-1, 0))

def legal_neighbors(
    game_map: "GameMap",
    from_tile: "Tile",
    unit: Optional["Unit"],
) -> list[tuple["Tile", float]]: ## Return tile and cost for pathfinding algorithm
    out: list[tuple["Tile", float]] = []
    for dx, dy in OFFSETS_4:
        nx_ = from_tile.x + dx
        ny_ =  from_tile.y + dy
        if not game_map.in_bounds(nx_, ny_):
            continue
        nbr = game_map.tile_at(nx_, ny_)

        reason = elevation.can_step(
            game_map, from_tile, nbr,
            unit=unit,
            is_diagonal=False,
        )
        if not reason.is_ok():
            continue

        cost = elevation.step_cost(
            game_map, from_tile, nbr,
            base_terrain_cost=base_terrain_cost(nbr),
            unit=unit,
        )
        out.append((nbr, cost))
    return out

def find_path(
    game_map: "GameMap",
    unit: "Unit",
    dest_x: int,
    dest_y: int,
) -> Optional[list[tuple[int, int]]]: # List of waypoints
    if not game_map.in_bounds(dest_x, dest_y):
        return None
    if (unit.x, unit.y) == (dest_x, dest_y):
        return []

    # Build a directed graph over reachable tiles for pathfinding
    g = nx.DiGraph()
    start = (unit.x, unit.y)
    goal  = (dest_x, dest_y)

    # check if tile is occupied
    dest_tile = game_map.tile_at(dest_x, dest_y)
    if dest_tile.unit_id not in (None, unit.id):
        return None

    visited: set[tuple[int, int]] = set()
    frontier: list[tuple[int, int]] = [start]
    g.add_node(start)

    while frontier:
        pos = frontier.pop()
        if pos in visited:
            continue
        visited.add(pos)
        cur = game_map.tile_at(*pos)

        for nbr, cost in legal_neighbors(game_map, cur, unit):
            npos = (nbr.x, nbr.y)
            # Skip neighbors that have a unit on them
            if nbr.unit_id not in (None, unit.id):
                continue

            g.add_edge(pos, npos, weight=cost)
            if npos not in visited:
                frontier.append(npos)

    if goal not in g:
        return None

    # Manhattan heuristic (think distance between two points but in 4 directions)
    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    try:
        path = nx.astar_path(g, start, goal, heuristic=heuristic, weight="weight")
    except nx.NetworkXNoPath:
        return None
    return path

def reachable_tiles(
    game_map: "GameMap",
    unit: "Unit",
    *,
    budget: Optional[float] = None,
) -> dict[tuple[int, int], float]:
    if budget is None:
        budget = float(unit.movement_remaining)
    if budget < 0:
        return {(unit.x, unit.y): 0.0} # exit if no move

    start = (unit.x, unit.y)
    costs: dict[tuple[int, int], float] = {start: 0.0}

    # Min-heap by cost. heapq doesn't have a decrease-key, so just insert duplicate entries and skip stale ones when popping.
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]

    while heap:
        cur_cost, pos = heapq.heappop(heap) # Get cheapest tile --> remove
        if cur_cost > costs.get(pos, float("inf")):
            continue  # stale entry --> pop

        cur_tile = game_map.tile_at(*pos) # Get all args
        for nbr, step_cost in legal_neighbors(game_map, cur_tile, unit):
            # Can't end a move on an occupied tile
            if nbr.unit_id not in (None, unit.id):
                continue

            npos = (nbr.x, nbr.y)
            new_cost = cur_cost + step_cost
            if new_cost > budget: # Too expensive --> exit
                continue
            if new_cost < costs.get(npos, float("inf")):
                costs[npos] = new_cost
                heapq.heappush(heap, (new_cost, npos))

    return costs

def fog_parser(
    game_map: "GameMap",
    unit: "Unit",
    *,
    budget: Optional[float] = None,
) -> dict[tuple[int, int], float]:
    budget = float(unit.sight)

    start = (unit.x, unit.y)
    costs: dict[tuple[int, int], float] = {start: 0.0}

    # Min-heap by cost. heapq doesn't have a decrease-key, so just insert duplicate entries and skip stale ones when popping.
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]

    while heap:
        cur_cost, pos = heapq.heappop(heap) # Get cheapest tile --> remove
        if cur_cost > costs.get(pos, float("inf")):
            continue  # stale entry --> pop

        cur_tile = game_map.tile_at(*pos) # Get all args
        for nbr, step_cost in legal_neighbors(game_map, cur_tile, unit):
            # Can't end a move on an occupied tile
            if nbr.unit_id not in (None, unit.id):
                continue

            npos = (nbr.x, nbr.y)
            new_cost = cur_cost + step_cost
            if new_cost > budget: # Too expensive --> exit
                continue
            if new_cost < costs.get(npos, float("inf")):
                costs[npos] = new_cost
                heapq.heappush(heap, (new_cost, npos))

    return costs

# Helper Methods
def path_cost(
    game_map: "GameMap",
    unit: "Unit",
    path: list[tuple[int, int]],
) -> float: # Return total cost
    if len(path) < 2:
        return 0.0

    total = 0.0
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        a = game_map.tile_at(ax, ay)
        b = game_map.tile_at(bx, by)
        total += elevation.step_cost(
            game_map, a, b,
            base_terrain_cost=base_terrain_cost(b),
            unit=unit,
        )
    return total
