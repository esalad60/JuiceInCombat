from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from . import terrain as terrain_mod
from . import type_advantages
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

    terrain_def_mod = terrain_mod.defense_multiplier(target_tile.feature)
    veterancy_mod   = 1.0  ## maybe implement

    status_mod = status_damage_multiplier(target)

    type_mod = type_advantages.type_advantage_multiplier(target, weapon)

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
        * type_mod
    )

    final_damage = max(MINIMUM_DAMAGE_AFTER_ARMOR, int(round(final_damage_f)))

    target.hp -= final_damage
    destroyed = target.hp <= 0

    perks_applied: list[str] = []
    is_unit_target = is_unit(state, target)

    explode_perks = [p for p in weapon.perks if p.type == "explode"]
    other_perks   = [p for p in weapon.perks if p.type != "explode"]

    if explode_perks:
        explosion_dmg = weapon.damage
        apply_explosion(
            state=state,
            attacker=attacker,
            target=target,
            explosion_damage=explosion_dmg,
        )
        perks_applied.append("explode")
        if is_unit_target and target.id not in state.units:
            destroyed = True

    if is_unit_target and not destroyed:
        for perk_app in other_perks:
            apply_weapon_perk(
                state=state,
                attacker=attacker,
                target=target,
                perk_type=perk_app.type,
                duration=perk_app.duration,
                params=perk_app.params,
            )
            perks_applied.append(perk_app.type)

    if destroyed:
        if is_unit_target:
            if target.id in state.units:
                state.remove_unit(target.id)
        else:
            if target.id in state.buildings:
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


def apply_explosion(
    *,
    state: GameState,
    attacker: Unit,
    target: Union[Unit, Building],
    explosion_damage: int,
) -> None:
    blast = max(1, int(explosion_damage))

    # Tiles affected: attacker's own tile + target tile + target's neighbors.
    affected: set[tuple[int, int]] = set()
    affected.add((attacker.x, attacker.y))
    tx, ty = target.x, target.y
    affected.add((tx, ty))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = tx + dx, ty + dy
        if state.game_map.in_bounds(nx, ny):
            affected.add((nx, ny))

    victims = [
        u for u in list(state.units.values())
        if (u.x, u.y) in affected and u.id != attacker.id
    ]
    for u in victims:
        u.hp -= blast
        if u.hp <= 0 and u.id in state.units:
            state.remove_unit(u.id)

    for b in list(state.buildings.values()):
        if (b.x, b.y) in affected:
            b.hp -= blast
            if b.hp <= 0 and b.id in state.buildings:
                state.remove_building(b.id)

    if attacker.id in state.units:
        state.remove_unit(attacker.id)


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