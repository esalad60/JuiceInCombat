from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .state import (
    ActiveStatusEffect,
    Building,
    GameState,
    Unit,
    Weapon,
)

ARMOR_DAMAGE_REDUCTION_PER_POINT = 2

HEIGHT_ATK_BONUS_PER_LEVEL    = 0.25
HEIGHT_DEF_REDUCTION_PER_LEVEL = 0.20

MINIMUM_DAMAGE_AFTER_ARMOR = 1


@dataclass
class FireResult:
    attacker_id:     int
    target_id:       int
    target_kind:     str # "unit" or "building"
    weapon_name:     str
    raw_damage:      int
    final_damage:    int
    target_destroyed: bool
    perks_applied:   list[str]


def fire_weapon(
    state: GameState,
    *,
    attacker: Unit,
    weapon: Weapon,
    target: Union[Unit, Building],
) -> FireResult:
    attacker_tile = state.game_map.tile_at(attacker.x, attacker.y)
    target_tile   = state.game_map.tile_at(target.x,   target.y)

    height_mod    = height_modifier(
        attacker_height=attacker_tile.height,
        target_height=target_tile.height,
    )

    # Placeholders until terrain_features.json and veterancy are implemented
    terrain_def_mod = 1.0
    veterancy_mod   = 1.0

    status_mod = status_damage_multiplier(target)

    raw_damage = apply_armor_formula(
        weapon_damage=weapon.damage,
        weapon_ap=weapon.ap,
        target_armor=target.armor,
    )

    final_damage_f = (
        raw_damage
        * terrain_def_mod
        * height_mod
        * veterancy_mod
        * status_mod
    )

    final_damage = max(MINIMUM_DAMAGE_AFTER_ARMOR, int(round(final_damage_f)))

    target.hp -= final_damage
    destroyed = target.hp <= 0

    perks_applied: list[str] = []
    is_unit_target = is_unit(state, target)

    if is_unit_target and not destroyed:
        for perk_app in weapon.perks:
            apply_weapon_perk(
                state=state,
                attacker=attacker,
                target=target, # type: ignore[arg-type]
                perk_type=perk_app.type,
                duration=perk_app.duration,
                params=perk_app.params,
            )
            perks_applied.append(perk_app.type)

    if destroyed:
        if is_unit_target:
            state.remove_unit(target.id)
        else:
            state.remove_building(target.id)

    return FireResult(
        attacker_id=attacker.id,
        target_id=target.id,
        target_kind="unit" if is_unit_target else "building",
        weapon_name=weapon.name,
        raw_damage=raw_damage,
        final_damage=final_damage,
        target_destroyed=destroyed,
        perks_applied=perks_applied,
    )


def apply_armor_formula(
    *,
    weapon_damage: int,
    weapon_ap: int,
    target_armor: int,
) -> int:
    if target_armor == 0:
        return weapon_damage

    net_armor = max(0, target_armor - weapon_ap)
    return weapon_damage - (ARMOR_DAMAGE_REDUCTION_PER_POINT * net_armor)


def height_modifier(*, attacker_height: int, target_height: int) -> float:
    if attacker_height > target_height:
        levels = attacker_height - target_height
        return 1.0 + HEIGHT_ATK_BONUS_PER_LEVEL * levels
    elif target_height > attacker_height:
        levels = target_height - attacker_height
        return max(0.0, 1.0 - HEIGHT_DEF_REDUCTION_PER_LEVEL * levels)
    return 1.0


def status_damage_multiplier(target: Union[Unit, Building]) -> float:
    effects = getattr(target, "status_effects", None)
    if not effects:
        return 1.0
    from . import perks
    return perks.damage_multiplier_for_effects(effects)


def apply_weapon_perk(
    *,
    state: GameState,
    attacker: Unit,
    target: Unit,
    perk_type: str,
    duration: int,
    params: dict,
) -> None:
    effect = ActiveStatusEffect(
        type=perk_type,
        duration=duration,
        source_slot=attacker.owner_slot,
        params=dict(params),
    )
    state.apply_status_effect(target.id, effect)


def is_unit(state: GameState, target: Union[Unit, Building]) -> bool:
    return target.id in state.units