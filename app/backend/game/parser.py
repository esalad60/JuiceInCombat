from __future__ import annotations

import json
import logging
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
        parse_trait(t, idx=i, source_path=source_path)
        for i, t in enumerate(traits_raw)
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
    params = {k: v for k, v in raw.items() if k != "type"}
    return TraitRef(type=trait_type, params=params)

## Work on load directory function and parsing the actual file

def parse_file(str: path):
    data = open(path).read().strip().split("/n")

    return data


if __name__ == "__main__":
    parse_file("../../data/rifleman.json")


