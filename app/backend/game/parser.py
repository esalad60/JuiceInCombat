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

BASE_ARMOR         = 0
BASE_COST          = 0
BASE_WEAPON_AP     = 0
BASE_WEAPON_RANGE  = 1
BASE_STATUS_DURATION = 1

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

    ## Add attack and range
    
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

        ## Add attack and range

        traits=traits,
        model=model,
    )

def parse_trait(
    raw: Any,
) -> TraitRef:
    trait_type = raw["type"]
    params = {k: v for k, v in raw.items() if k != "type"}
    return TraitRef(type=trait_type, params=params)

## Work on load directory function and parsing the actual file

