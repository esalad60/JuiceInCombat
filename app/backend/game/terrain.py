from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureDef:
    name: str
    defense_mult: float = 1.0 
    move_cost: float = 1.0    
    impassable: bool = False
    description: str = ""


OPEN_GROUND = FeatureDef(name="none", defense_mult=1.0, move_cost=1.0)

FEATURE_REGISTRY: dict[str, FeatureDef] = {
    "forest":   FeatureDef("forest",   defense_mult=0.80, move_cost=2.0,
                           description="Tree cover: -20% damage taken, slow."),
    "mountain": FeatureDef("mountain", defense_mult=0.75, move_cost=3.0,
                           description="Heavy cover, very slow to cross."),
    "ramp":     FeatureDef("ramp",     defense_mult=1.0,  move_cost=1.0,
                           description="Slope connecting two height levels."),
    "building": FeatureDef("building", defense_mult=1.0,  move_cost=1.0,
                           description="A structure occupies this tile."),
}


def get_feature(feature: str | None) -> FeatureDef:
    if not feature:
        return OPEN_GROUND
    return FEATURE_REGISTRY.get(feature, OPEN_GROUND)


def defense_multiplier(feature: str | None) -> float:
    return get_feature(feature).defense_mult


def move_cost(feature: str | None) -> float:
    return get_feature(feature).move_cost


def is_impassable(feature: str | None) -> bool:
    return get_feature(feature).impassable


def is_ramp(feature: str | None) -> bool:
    return feature == "ramp"