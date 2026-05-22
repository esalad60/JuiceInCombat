from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .unit import (
    TraitRef,
    UnitCategory,
    UnitDefinition,
    UnitRegistry,
)

logger = logging.getLogger(__name__)

def parse_unit_dict(
    raw: dict[str, Any],
    *,
    unit_type: str, ## Mainly for id purposes
    faction: str,
    source_path: str = "<unknown>",
) -> UnitDefinition:
    
    def fetch(key: str) -> Any:
        return raw[key]
    
    name = fetch("name")
    category = fetch("type")
    price = fetch("price")
    
    health   = fetch("health")
    armor = fetch("armor")
    sight = fetch("sight")
    movement = fetch("movement")

    attack = fetch("attack")
    range = fetch("range")
    
    traits_raw = raw.get("traits", [])
    traits = tuple(
        parse_trait(t)
        for t in enumerate(traits_raw)
    )

    model = fetch("model") or None ## Not sure if correct syntax

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

        attack=attack,
        range=range,

        traits=traits,
        model=model,
    )

def parse_trait(raw: Any,) -> TraitRef:
    trait_type = raw["type"]
    params = {}
    for k, v in raw.items():
        if k != "type":
            params[k] = v
    return TraitRef(type=trait_type, params=params)

def parse_unit_file(path: str) -> UnitDefinition:
    path = Path(path)
    with path.open() as f:
        raw = json.load(f)

    unit_type = path.stem
    faction = path.parent.name

    return parse_unit_dict(
        raw,
        unit_type=unit_type,
        faction=faction,
        source_path=str(path),
    )

def register_units(root: str) -> UnitRegistry:
    root = Path(root)
    registry = UnitRegistry()
    faction_units: dict[str, int] = {}

    for faction_dir in sorted(root.iterdir()):
        if not faction_dir.is_dir():
            continue
        faction = faction_dir.name
        faction_units.setdefault(faction, 0)

        for json_path in sorted(faction_dir.iterdir()):
            if json_path.suffix.lower() != ".json":
                continue
            definition = parse_unit_file(json_path)
            registry.register(definition)
            faction_units[faction] += 1

    return registry




