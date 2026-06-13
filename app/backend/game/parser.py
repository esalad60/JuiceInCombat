from __future__ import annotations

import json
import sys
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


REQUIRED_UNIT_KEYS = (
    "name",
    "type",
    "cost",
    "health",
    "armor",
    "sight",
    "movement",
)


class UnitParseError(ValueError):
    pass


def require_keys(raw: dict[str, Any], keys: tuple[str, ...], *, path: Path) -> None:
    missing = [key for key in keys if key not in raw]

    if missing:
        raise UnitParseError(
            f"{path}: missing required unit keys: {', '.join(missing)}"
        )


def parse_unit_dict(
    raw: dict[str, Any],
    *,
    unit_type: str,
    faction: str,
    path: Path | None = None,
) -> UnitDefinition:
    if path is not None:
        require_keys(raw, REQUIRED_UNIT_KEYS, path=path)

    def fetch(key: str) -> Any:
        return raw[key]

    name = str(fetch("name"))
    category = UnitCategory(fetch("type"))

    price = int(fetch("cost"))
    health = int(fetch("health"))
    armor = int(fetch("armor"))
    sight = int(fetch("sight"))
    movement = int(fetch("movement"))

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

    name = str(fetch("name"))
    description = raw.get("description", "")
    weapon_type = fetch("type")
    damage = int(fetch("damage"))
    ap = int(raw.get("ap", 0))
    rng = int(raw.get("range", 1))
    cd = int(raw.get("cooldown", 1))

    perks_raw = raw.get("perks", [])
    perks = tuple(parse_weapon_perk(p) for p in perks_raw)

    return WeaponDef(
        name=name,
        description=description,
        type=weapon_type,
        damage=damage,
        ap=ap,
        range=rng,
        cooldown=cd,
        perks=perks,
    )


def parse_weapon_perk(raw: dict[str, Any]) -> WeaponPerkRef:
    def fetch(key: str) -> Any:
        return raw[key]

    perk = fetch("type")
    duration = int(fetch("duration"))

    params = {
        k: v
        for k, v in raw.items()
        if k not in ("type", "duration")
    }

    return WeaponPerkRef(
        type=perk,
        duration=duration,
        params=params,
    )


def parse_trait(raw: dict[str, Any]) -> TraitRef:
    trait_type = raw["type"]
    params = {
        k: v
        for k, v in raw.items()
        if k != "type"
    }

    return TraitRef(
        type=trait_type,
        params=params,
    )


def parse_unit_file(path: str | Path) -> UnitDefinition:
    path = Path(path)

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise UnitParseError(f"{path}: invalid JSON: {e}") from e

    if not isinstance(raw, dict):
        raise UnitParseError(f"{path}: unit file must contain a JSON object")

    unit_type = path.stem
    faction = path.parent.name

    return parse_unit_dict(
        raw,
        unit_type=unit_type,
        faction=faction,
        path=path,
    )


def register_units(
    root: str | Path,
    *,
    strict: bool = False,
) -> UnitRegistry:
    root = Path(root)
    registry = UnitRegistry()

    if not root.exists():
        message = f"Unit directory does not exist: {root}"

        if strict:
            raise FileNotFoundError(message)

        print(f"[unit parser] WARNING: {message}", file=sys.stderr)
        return registry

    for faction_dir in sorted(root.iterdir()):
        if not faction_dir.is_dir():
            continue

        for json_path in sorted(faction_dir.iterdir()):
            if json_path.suffix.lower() != ".json":
                continue

            try:
                definition = parse_unit_file(json_path)
            except Exception as e:
                message = f"[unit parser] Skipping invalid unit file {json_path}: {e}"

                if strict:
                    raise UnitParseError(message) from e

                print(message, file=sys.stderr)
                continue

            registry.register(definition)

    return registry