def fog_parser(
    game_map: "GameMap",
    unit: "Unit",
    *,
    budget: Optional[float] = None,
) -> dict[tuple[int, int], float]:
    if budget is None:
        budget = float(unit.sight)
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
