from __future__ import annotations

from enum import Enum

from .state import GameState, Unit
from .unit import UnitDefinition

class Reason(str, Enum):
    OK                  = "ok"
    ALREADY_MOVED       = "already_moved"
    ALREADY_FIRED       = "already_fired"
    NO_MOVES_REMAINING  = "no_moves_remaining"
    NO_WEAPONS          = "no_weapons"
    # SETUP_LOCKED      = "setup_locked"
    # OVERWATCH_LOCKED  = "overwatch_locked"

    def is_ok(self) -> bool:
        return self is Reason.OK

def reset_unit_budgets(state: GameState, player_slot: int) -> None:
    for unit in state.units_for(player_slot):
        unit.moved_last_turn  = unit.has_moved
        unit.fired_last_turn  = unit.has_fired_weapon

        unit.has_moved        = False
        unit.has_fired_weapon = False

        unit.movement_remaining = unit.max_movement


def can_move(
    unit: Unit,
    definition: UnitDefinition,
    *,
    distance: int = 1,
) -> Reason:
    # if has_setup_trait(definition) and unit.has_fired_weapon:
    #     return Reason.SETUP_LOCKED
    # if has_overwatch_trait(definition) and unit.has_fired_weapon:
    #     return Reason.OVERWATCH_LOCKED

    if unit.movement_remaining < distance:
        return Reason.NO_MOVES_REMAINING

    return Reason.OK


def can_fire(
    unit: Unit,
    definition: UnitDefinition,
) -> Reason:
    if not unit.weapons:
        return Reason.NO_WEAPONS

    if unit.has_fired_weapon:
        return Reason.ALREADY_FIRED

    # if has_setup_trait(definition) and unit.has_moved:
    #     return Reason.SETUP_LOCKED

    return Reason.OK


def commit_move(unit: Unit, *, distance: int = 1) -> None:
    unit.movement_remaining = max(0, unit.movement_remaining - distance)
    unit.has_moved = True


def commit_fire(unit: Unit) -> None:
    unit.has_fired_weapon = True