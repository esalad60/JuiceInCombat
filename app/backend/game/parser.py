from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .unit import (
    TraitRef,
    UnitCategory,
    UnitDefinition,
    UnitRegistry,
    WeaponDef,
    WeaponPerkRef,
)

def parse_unit_dict(
    raw: dict[str, Any],
    *,
    unit_type: str,
    faction: str,
) -> UnitDefinition:
    def fetch(key: str) -> Any:
        return raw[key]

    name     = fetch("name")
    category = UnitCategory(fetch("type"))

    price    = fetch("cost")

    health   = fetch("health")
    armor    = fetch("armor")
    sight    = fetch("sight")
    movement = fetch("movement")

    weapons_raw = raw.get("weapons", [])
    weapons = tuple(parse_weapon(w) for w in weapons_raw)

    traits_raw = raw.get("traits", [])
    traits = tuple(parse_trait(t) for t in traits_raw)

    model = raw.get("model")

    return UnitDefinition(
        unit_type=unit_type,
        faction=faction,
        name=name,
        category=category,
        price=price,
        health=health,
        armor=armor,
        sight=sight,
        movement=movement,
        traits=traits,
        weapons=weapons,
        model=model,
    )


def parse_weapon(raw: dict[str, Any]) -> WeaponDef:
    def fetch(key: str) -> Any:
        return raw[key]

    name        = fetch("name")
    description = raw.get("description", "")
    weapon_type = fetch("type")
    damage      = fetch("damage")
    ap          = fetch("ap")
    rng         = fetch("range")
    cd          = fetch("cooldown")

    perks_raw = raw.get("perks", [])
    perks = tuple(parse_weapon_perk(p) for p in perks_raw)

    return WeaponDef(
        name=name,
        description=description,
        type=weapon_type,
        damage=damage,
        ap=ap,
        range=rng,
        perks=perks,
    )


def parse_weapon_perk(raw: dict[str, Any]) -> WeaponPerkRef:
    def fetch(key: str) -> Any:
        return raw[key]

    perk     = fetch("type")
    duration = int(fetch("duration"))

    params = {k: v for k, v in raw.items() if k not in ("type", "duration")}

    return WeaponPerkRef(type=perk, duration=duration, params=params)


def parse_trait(raw: dict[str, Any]) -> TraitRef:
    trait_type = raw["type"]
    params = {k: v for k, v in raw.items() if k != "type"}
    return TraitRef(type=trait_type, params=params)


def parse_unit_file(path: str) -> UnitDefinition:
    path = Path(path)
    with path.open() as f:
        raw = json.load(f)

    unit_type = path.stem
    faction   = path.parent.name

    return parse_unit_dict(raw, unit_type=unit_type, faction=faction)


def register_units(root: str) -> UnitRegistry:
    root = Path(root)
    registry = UnitRegistry()

    for faction_dir in sorted(root.iterdir()):
        if not faction_dir.is_dir():
            continue
        for json_path in sorted(faction_dir.iterdir()):
            if json_path.suffix.lower() != ".json":
                continue
            definition = parse_unit_file(json_path)
            registry.register(definition)

    return registry
