from __future__ import annotations

from typing import Optional, Union

from .state import Building, Unit
from .state import Weapon


DEFAULT_MULTIPLIER = 1.0

MATCHUPS: dict[tuple[str, str], float] = {
    ("infantry", "heat"):   0.50,
    ("infantry", "he"):     1.25,
    ("vehicle",  "heat"):   1.25,
    ("vehicle",  "bullet"): 0.85,
}


def _target_category(target: Union["Unit", "Building"]) -> Optional[str]:
    cat = getattr(target, "category", None)
    if cat is None:
        return None
    val = getattr(cat, "value", cat)
    return str(val).lower()


def type_advantage_multiplier(
    target: Union["Unit", "Building"],
    weapon: "Weapon",
) -> float:
    category = _target_category(target)
    if category is None:
        return DEFAULT_MULTIPLIER

    weapon_type = getattr(weapon, "type", None)
    if not weapon_type:
        return DEFAULT_MULTIPLIER

    return MATCHUPS.get((category, str(weapon_type).lower()), DEFAULT_MULTIPLIER)