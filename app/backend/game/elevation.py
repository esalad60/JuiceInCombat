from __future__ import annotations

from enum import Enum
from typing import Optional

from .state import GameMap, Ramp, Tile, Unit


DEFAULT_MAX_HEIGHT_DELTA = 1
DEFAULT_EXTRA_COST_UP    = 1
DEFAULT_EXTRA_COST_DOWN  = 0


class StepReason(str, Enum):
    OK                  = "ok"
    CLIFF_NO_RAMP       = "cliff_no_ramp"
    RAMP_DELTA_EXCEEDED = "ramp_delta_exceeded"

    def is_ok(self) -> bool:
        return self is StepReason.OK


def can_step(
    game_map: GameMap,
    from_tile: Tile,
    to_tile: Tile,
    *,
    unit: Optional[Unit] = None,
    is_diagonal: bool = False,
) -> StepReason:
    delta = abs(to_tile.height - from_tile.height)
    if delta == 0:
        return StepReason.OK

    # # Climb trait: ignore height restrictions entirely.
    # if unit is not None and has_climb_trait(unit):
    #     return StepReason.OK

    ramp = game_map.ramp_between(
        (from_tile.x, from_tile.y),
        (to_tile.x,   to_tile.y),
    )
    if ramp is None:
        return StepReason.CLIFF_NO_RAMP

    if delta > ramp_max_delta(ramp):
        return StepReason.RAMP_DELTA_EXCEEDED

    return StepReason.OK


def step_cost(
    game_map: GameMap,
    from_tile: Tile,
    to_tile: Tile,
    *,
    base_terrain_cost: float = 1.0,
    unit: Optional[Unit] = None,
) -> float:
    delta = to_tile.height - from_tile.height
    if delta == 0:
        return base_terrain_cost

    # # Climb trait: no extra cost.
    # if unit is not None and has_climb_trait(unit):
    #     return base_terrain_cost

    ramp = game_map.ramp_between(
        (from_tile.x, from_tile.y),
        (to_tile.x,   to_tile.y),
    )
    if ramp is None:
        return base_terrain_cost + DEFAULT_EXTRA_COST_UP

    if delta > 0:
        return base_terrain_cost + ramp_extra_cost_up(ramp)
    else:
        return base_terrain_cost + ramp_extra_cost_down(ramp)


def height_delta(from_tile: Tile, to_tile: Tile) -> int:
    return to_tile.height - from_tile.height


def has_climb_trait(unit: Unit) -> bool:
    return any(t.type == "Climb" for t in unit.traits)


def ramp_max_delta(ramp: Ramp) -> int:
    return DEFAULT_MAX_HEIGHT_DELTA


def ramp_extra_cost_up(ramp: Ramp) -> float:
    return DEFAULT_EXTRA_COST_UP


def ramp_extra_cost_down(ramp: Ramp) -> float:
    return DEFAULT_EXTRA_COST_DOWN