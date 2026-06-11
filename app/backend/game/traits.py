from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
from .state import GameState, Unit, UnitTrait

REGEN_AMOUNT = 15


@dataclass(frozen=True)
class TraitDefinition:
    type: str
    description: str = ""
    turn_tick: Optional[Callable[["GameState", "Unit", "UnitTrait"], Optional[int]]] = None
    ignores_climb: bool = False
    movement_modifier: Optional[Callable[["UnitTrait"], float]] = None ## For future slow perk etc


def _regen_tick(state: "GameState", unit: "Unit", trait: "UnitTrait") -> Optional[int]:
    return int(trait.params.get("amount", REGEN_AMOUNT))

TRAIT_REGISTRY: dict[str, TraitDefinition] = {
    "Regen": TraitDefinition(
        type="Regen",
        description="Heals HP at the start of each turn.",
        turn_tick=_regen_tick,
    ),
    "Climb": TraitDefinition(
        type="Climb",
        description="Ignores cliff restrictions and climb movement cost.",
        ignores_climb=True,
    ),
    "Radio": TraitDefinition(
        type="Radio",
        description="Baboom",
        ## Not implemented yet
    ),
}

def get_trait(trait_type: str) -> Optional[TraitDefinition]:
    return TRAIT_REGISTRY.get(trait_type)

def unit_ignores_climb(unit: "Unit") -> bool:
    for t in getattr(unit, "traits", []) or []:
        d = TRAIT_REGISTRY.get(t.type)
        if d and d.ignores_climb:
            return True
    return False


def movement_multiplier_for_unit(unit: "Unit") -> float:
    mult = 1.0
    for t in getattr(unit, "traits", []) or []:
        d = TRAIT_REGISTRY.get(t.type)
        if d and d.movement_modifier:
            mult *= d.movement_modifier(t)
    return mult


def tick_traits_for_unit(state: "GameState", unit: "Unit") -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for t in getattr(unit, "traits", []) or []:
        d = TRAIT_REGISTRY.get(t.type)
        if not d or not d.turn_tick:
            continue
        delta = d.turn_tick(state, unit, t)
        if not delta:
            continue
        before = unit.hp
        unit.hp += int(delta)
        if unit.max_hp and unit.hp > unit.max_hp:
            unit.hp = unit.max_hp
        if unit.hp != before:
            events.append({"type": t.type, "unit_id": unit.id,
                           "hp_delta": unit.hp - before, "new_hp": unit.hp})
    return events


def apply_turn_traits_for_player(state: "GameState", player_slot: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for unit in [u for u in state.units.values() if u.owner_slot == player_slot]:
        if unit.id not in state.units:
            continue
        events.extend(tick_traits_for_unit(state, unit))
    return events