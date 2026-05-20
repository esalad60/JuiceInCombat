from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

class UnitCategory(str, Enum):
    INFANTRY  = "infantry"
    VEHICLE   = "vehicle"
    AIRCRAFT  = "aircraft"

@dataclass(frozen=True) ## immutable
class TraitRef:
    type: str
    params: dict[str, Any] = field(default_factory=dict) ## When creating this class, new dict for each instance

@dataclass(frozen=True)
class UnitDefinition:

    unit_type: str
    faction: str

    name: str
    category: UnitCategory
    price: int

    health: int
    armor: int
    sight: int
    movement: int

    attack: int
    range: int

    traits: tuple[TraitRef, ...]

    model: Optional[str] = None

    def has_trait(self, trait_type: str) -> bool:
        return any(t.type == trait_type for t in self.traits)

    def get_trait(self, trait_type: str) -> Optional[TraitRef]:
        for t in self.traits:
            if t.type == trait_type:
                return t
        return None
    
class UnitRegistry: ## Specific to each faction
    def __init__(self) -> None:
        self.defs: dict[tuple[str, str], UnitDefinition] = {}

    def register(self, definition: UnitDefinition) -> None:
        key = (definition.faction, definition.unit_type)
        self.defs[key] = definition

    def get(self, faction: str, unit_type: str) -> Optional[UnitDefinition]:
        return self.defs.get((faction, unit_type))

    def all(self) -> list[UnitDefinition]:
        return list(self.defs.values())

    def for_faction(self, faction: str) -> list[UnitDefinition]:
        return [d for (f, _), d in self.defs.items() if f == faction]

    ## Bottom easier for frontend

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self.defs

    def __len__(self) -> int:
        return len(self.defs)