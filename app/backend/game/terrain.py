from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TerrainDef:
    name: str
    defense_mult: float = 1.0 
    move_cost: float = 1.0 
    impassable: bool = False
    description: str = ""


DEFAULT_TERRAIN = TerrainDef(name="plains", defense_mult=1.0, move_cost=1.0)

TERRAIN_REGISTRY: dict[str, TerrainDef] = {
    "plains":    TerrainDef("plains",    defense_mult=1.00, move_cost=1.0,
                            description="Open ground, no cover."),
    "forest":    TerrainDef("forest",    defense_mult=0.80, move_cost=2.0,
                            description="20% less damage taken, slow"),
    "mountains": TerrainDef("mountains", defense_mult=0.75, move_cost=3.0,
                            description="Heavy cover, very slow."),
}


def get_terrain(base: str | None) -> TerrainDef:
    if not base:
        return DEFAULT_TERRAIN
    return TERRAIN_REGISTRY.get(base, DEFAULT_TERRAIN)


def defense_multiplier(base: str | None) -> float:
    return get_terrain(base).defense_mult


def move_cost(base: str | None) -> float:
    return get_terrain(base).move_cost


def is_impassable(base: str | None) -> bool:
    return get_terrain(base).impassable