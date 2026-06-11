"""
perks.py — Weapon-perk registry and resolution.

A "perk" is a status effect a weapon applies to a target on hit (e.g. Mark,
incendiary). Previously the behavior of each perk was hardcoded inside
combat.py (Mark -> x1.25, incendiary -> nothing). This module centralizes
every perk's behavior in one place so combat.py and the engine just look perks
up instead of special-casing them.

How it plugs into the existing system
--------------------------------------
* A weapon carries `WeaponPerkRef`s (type, duration, params) parsed from JSON.
* On a hit, combat.apply_weapon_perk() turns each into an `ActiveStatusEffect`
  attached to the target unit (state.apply_status_effect).
* Each turn, state.tick_status_effects() decrements durations and drops expired
  ones. We add a per-tick damage hook here for effects like incendiary.
* When something attacks a unit, combat.status_damage_multiplier() asks this
  registry how much the unit's active effects scale incoming damage (Mark).

Each perk is described by a PerkDefinition with optional hooks. Adding a new
perk = add one PerkDefinition to PERK_REGISTRY. No changes to combat/engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from .state import ActiveStatusEffect, GameState, Unit

MARK_MULTIPLIER = 1.25
BURN_DAMAGE = 10


@dataclass(frozen=True)
class PerkDefinition:
    type: str
    description: str = ""
    incoming_damage_multiplier: Optional[Callable[["ActiveStatusEffect"], float]] = None
    turn_tick: Optional[Callable[["GameState", "Unit", "ActiveStatusEffect"], Optional[int]]] = None

def mark_multiplier(effect: "ActiveStatusEffect") -> float:
    return float(effect.params.get("multiplier", MARK_MULTIPLIER))

def incendiary_tick(state: "GameState", unit: "Unit", effect: "ActiveStatusEffect") -> Optional[int]:
    return int(effect.params.get("burn_damage", BURN_DAMAGE))

PERK_REGISTRY: dict[str, PerkDefinition] = {
    "Mark": PerkDefinition(
        type="Mark",
        description="Target takes increased damage",
        incoming_damage_multiplier=mark_multiplier,
    ),
    "incendiary": PerkDefinition(
        type="incendiary",
        description="Burns the target",
        turn_tick=incendiary_tick,
    ),
}

def get_perk(perk_type: str) -> Optional[PerkDefinition]:
    return PERK_REGISTRY.get(perk_type)

def damage_multiplier_for_effects(effects: list["ActiveStatusEffect"]) -> float:
    mult = 1.0
    for eff in effects or []:
        perk = PERK_REGISTRY.get(eff.type)
        if perk and perk.incoming_damage_multiplier:
            mult *= perk.incoming_damage_multiplier(eff)
    return mult


def tick_damage_for_unit(state: "GameState", unit: "Unit") -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not getattr(unit, "status_effects", None):
        return events

    for eff in list(unit.status_effects):
        perk = PERK_REGISTRY.get(eff.type)
        if not perk or not perk.turn_tick:
            continue
        dmg = perk.turn_tick(state, unit, eff)
        if not dmg:
            continue
        unit.hp -= int(dmg)
        destroyed = unit.hp <= 0
        events.append({"type": eff.type, "unit_id": unit.id,
                       "damage": int(dmg), "destroyed": destroyed})
        if destroyed:
            state.remove_unit(unit.id)
            break
    return events

## Apply tick damage for 
def apply_tick_damage_for_player(state: "GameState", player_slot: int) -> list[dict[str, Any]]: 
    events: list[dict[str, Any]] = []
    for unit in [u for u in state.units.values() if u.owner_slot == player_slot]:
        if unit.id not in state.units:
            continue  # already removed this tick
        events.extend(tick_damage_for_unit(state, unit))
    return events