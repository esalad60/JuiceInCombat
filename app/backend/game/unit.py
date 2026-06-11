from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class UnitCategory(str, Enum):
    INFANTRY  = "infantry"
    VEHICLE   = "vehicle"
    AIRCRAFT  = "aircraft"


@dataclass(frozen=True)
class WeaponPerkRef:
    type: str
    duration: int = 1
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WeaponDef:
    name: str
    type: str
    damage: int
    description: str = ""
    ap: int = 0
    range: int = 1
    cooldown: int = 1
    perks: tuple[WeaponPerkRef, ...] = ()


@dataclass(frozen=True)
class TraitRef:
    type: str
    params: dict[str, Any] = field(default_factory=dict)

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

    traits: tuple[TraitRef, ...]

    requires_tech: Optional[str] = None
    weapons: tuple[WeaponDef, ...] = ()
    model: Optional[str] = None

    def has_trait(self, trait_type: str) -> bool:
        return any(t.type == trait_type for t in self.traits)

    def get_trait(self, trait_type: str) -> Optional[TraitRef]:
        for t in self.traits:
            if t.type == trait_type:
                return t
        return None

    def get_weapon(self, name: str) -> Optional[WeaponDef]:
        for w in self.weapons:
            if w.name == name:
                return w
        return None

    def max_weapon_range(self) -> int:
        if not self.weapons:
            return 0
        return max(w.range for w in self.weapons)


class UnitRegistry:
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

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self.defs

    def __len__(self) -> int:
        return len(self.defs)
