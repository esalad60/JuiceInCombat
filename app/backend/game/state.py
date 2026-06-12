from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Generator, Optional

from .unit import UnitRegistry, UnitDefinition
from .unit import UnitDefinition  # for type hints

RESOURCE_KEYS: tuple[str, ...] = ("cash",)
BASE_TERRAIN: str = "plains"

class MatchStatus(str, Enum):
    WAITING     = "waiting"
    IN_PROGRESS = "in_progress"
    ENDED       = "ended"

class TimeControl(str, Enum):
    LIVE      = "live"
    ASYNC_24H = "24h"

@dataclass
class Tile:
    x: int
    y: int
    base: str = BASE_TERRAIN
    feature: Optional[str] = None
    height: int = 1
    resource: Optional[str] = None
    building_id: Optional[int] = None
    unit_id: Optional[int] = None

@dataclass
class Ramp:
    tile_a: tuple[int, int]
    tile_b: tuple[int, int]
    type: str

@dataclass
class GameMap:
    width: int
    height: int
    tiles: list[list[Tile]]
    ramps: list[Ramp] = field(default_factory=list)
    name: str = ""
    spawns: list[tuple[int, int]] = field(default_factory=list)

    @classmethod
    def blank_map(cls, width: int, height: int, *, name: str = "") -> "GameMap":
        tiles: list[list[Tile]] = []
        for y in range(height):
            row: list[Tile] = []
            for x in range(width):
                row.append(Tile(x=x, y=y))
            tiles.append(row)
        return cls(width=width, height=height, tiles=tiles, name=name)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, x: int, y: int) -> Tile:
        return self.tiles[y][x]

    def iter_tiles(self) -> Generator[Tile, None, None]:
        for row in self.tiles:
            for tile in row:
                yield tile

    def ramp_between(self, a: tuple[int, int], b: tuple[int, int]) -> Optional[Ramp]:
        for r in self.ramps:
            if (r.tile_a == a and r.tile_b == b) or (r.tile_a == b and r.tile_b == a):
                return r
        return None

    def to_saved_map_dict(self) -> dict:
        tiles_data = [
            {
                "x": tile.x,
                "y": tile.y,
                "base": tile.base,
                "feature": tile.feature,
                "height": tile.height,
                "resource": tile.resource,
            }
            for tile in self.iter_tiles()
        ]

        ramps_data = [
            {"from": list(r.tile_a), "to": list(r.tile_b), "type": r.type}
            for r in self.ramps
        ]

        spawn_data = [{"x": s[0], "y": s[1]} for s in self.spawns]

        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tiles": tiles_data,
            "ramps": ramps_data,
            "spawns": spawn_data,
        }

    @classmethod
    def from_saved_map_dict(cls, d: dict) -> "GameMap":
        width  = int(d["width"])
        height = int(d["height"])

        tiles: list[list[Tile]] = []
        for y in range(height):
            row: list[Tile] = []
            for x in range(width):
                row.append(Tile(x=x, y=y))
            tiles.append(row)

        for tile_data in d["tiles"]:
            x = int(tile_data["x"])
            y = int(tile_data["y"])
            tiles[y][x] = Tile(
                x=x,
                y=y,
                base=tile_data.get("base", BASE_TERRAIN),
                feature=tile_data.get("feature"),
                height=int(tile_data.get("height", 1)),
                resource=tile_data.get("resource"),
            )

        ramps = [
            Ramp(
                tile_a=tuple(rd["from"]),
                tile_b=tuple(rd["to"]),
                type=rd["type"],
            )
            for rd in d.get("ramps", [])
        ]

        spawns = [
            (int(s["x"]), int(s["y"]))
            for s in d.get("spawns", [])
        ]

        return cls(
            width=width,
            height=height,
            tiles=tiles,
            ramps=ramps,
            name=d.get("name", ""),
            spawns=spawns,
        )

@dataclass
class WeaponPerkApplication:
    type: str
    duration: int = 1
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class Weapon:
    name: str
    type: str
    damage: int
    ap: int = 0
    range: int = 1
    description: str = ""
    perks: list[WeaponPerkApplication] = field(default_factory=list)

@dataclass
class UnitTrait:
    type: str
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class ActiveStatusEffect:
    type: str
    duration: int
    source_slot: int
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class Unit:
    id: int
    type: str
    owner_slot: int
    x: int
    y: int
    hp: int
    sight: int
    armor: int = 0
    max_hp: int = 0
    model: Optional[str] = None
    weapons: list[Weapon] = field(default_factory=list)
    traits: list[UnitTrait] = field(default_factory=list)
    status_effects: list[ActiveStatusEffect] = field(default_factory=list)
    veterancy: int = 0
    has_moved: bool = False
    has_fired_weapon: bool = False
    movement_remaining: int = 0
    max_movement: int = 0
    moved_last_turn: bool = False
    fired_last_turn: bool = False

@dataclass
class Building:
    id: int
    type: str
    owner_slot: int
    x: int
    y: int
    hp: int
    armor: int = 0
    is_capital: bool = False

def _default_resources() -> dict[str, int]:
    return {k: 0 for k in RESOURCE_KEYS}

@dataclass
class Player:
    slot: int
    faction: str
    color: str = "#ffffff"
    user_id: Optional[int] = None
    resources: dict[str, int] = field(default_factory=_default_resources)
    capital_building_id: Optional[int] = None
    visible_tiles: set[tuple[int, int]] = field(default_factory=set)
    explored_tiles: set[tuple[int, int]] = field(default_factory=set)
    time_remaining_seconds: float = 0.0
    turn_started_at: Optional[float] = None
    turn_deadline_ts: Optional[float] = None
    consecutive_timeouts: int = 0

@dataclass
class GameState:
    match_id: int
    map_id: int
    game_map: GameMap
    players: list[Player]
    time_control: TimeControl = TimeControl.LIVE
    starting_time_bank: float = 300.0
    time_increment: float = 120.0
    deadline_hours: float = 24.0
    timeout_forfeit_limit: int = 3
    turn: int = 0
    current_player_slot: int = 0
    status: MatchStatus = MatchStatus.WAITING
    winner_slot: Optional[int] = None
    units: dict[int, Unit] = field(default_factory=dict)
    buildings: dict[int, Building] = field(default_factory=dict)
    action_log: list[dict[str, Any]] = field(default_factory=list)
    _next_unit_id: int = field(default=1)
    _next_building_id: int = field(default=1)

    def next_unit_id(self) -> int:
        i = self._next_unit_id
        self._next_unit_id += 1
        return i

    def next_building_id(self) -> int:
        i = self._next_building_id
        self._next_building_id += 1
        return i

    def get_unit(self, unit_id: int) -> Optional[Unit]:
        return self.units.get(unit_id)

    def get_building(self, building_id: int) -> Optional[Building]:
        return self.buildings.get(building_id)

    def get_player(self, slot: int) -> Player:
        return self.players[slot]

    def get_capital(self, player_slot: int) -> Optional[Building]:
        cid = self.players[player_slot].capital_building_id
        return self.buildings.get(cid) if cid is not None else None

    def unit_at(self, x: int, y: int) -> Optional[Unit]:
        tile = self.game_map.tile_at(x, y)
        return self.units.get(tile.unit_id) if tile.unit_id is not None else None

    def building_at(self, x: int, y: int) -> Optional[Building]:
        tile = self.game_map.tile_at(x, y)
        return self.buildings.get(tile.building_id) if tile.building_id is not None else None

    def units_for(self, player_slot: int) -> Generator[Unit, None, None]:
        return (u for u in self.units.values() if u.owner_slot == player_slot)

    def buildings_for(self, player_slot: int) -> Generator[Building, None, None]:
        return (b for b in self.buildings.values() if b.owner_slot == player_slot)

    def place_unit(self, unit: Unit) -> int:
        if unit.id == 0:
            unit.id = self.next_unit_id()
        tile = self.game_map.tile_at(unit.x, unit.y)
        if tile.unit_id is not None:
            pass
        self.units[unit.id] = unit
        tile.unit_id = unit.id
        return unit.id

    def remove_unit(self, unit_id: int) -> None:
        unit = self.units.pop(unit_id, None)
        if unit is None:
            return
        tile = self.game_map.tile_at(unit.x, unit.y)
        if tile.unit_id == unit_id:
            tile.unit_id = None

    def move_unit(self, unit_id: int, to_x: int, to_y: int) -> None:
        unit = self.units[unit_id]
        dest = self.game_map.tile_at(to_x, to_y)
        if dest.unit_id is not None and dest.unit_id != unit_id:
            pass
        old = self.game_map.tile_at(unit.x, unit.y)
        if old.unit_id == unit_id:
            old.unit_id = None
        unit.x = to_x
        unit.y = to_y
        dest.unit_id = unit_id

    def spawn_unit_from_definition(
        self,
        definition: UnitDefinition,
        *,
        owner_slot: int,
        x: int,
        y: int,
    ) -> Unit:
        weapons = [
            Weapon(
                name=w.name, type=w.type, damage=w.damage,
                ap=w.ap, range=w.range, description=w.description,
                perks=[
                    WeaponPerkApplication(
                        type=p.type, duration=p.duration,
                        params=dict(p.params),
                    )
                    for p in w.perks
                ],
            )
            for w in definition.weapons
        ]
        traits = [
            UnitTrait(type=t.type, params=dict(t.params))
            for t in definition.traits
        ]
        unit = Unit(
            id=0,
            type=definition.unit_type,
            owner_slot=owner_slot,
            x=x, y=y,
            sight=definition.sight,
            hp=definition.health,
            armor=definition.armor,
            max_hp=definition.health,
            model=definition.model,
            weapons=weapons,
            traits=traits,
            movement_remaining=definition.movement,
            max_movement=definition.movement,
        )
        self.place_unit(unit)
        return unit

    def place_building(self, building: Building) -> int:
        if building.id == 0:
            building.id = self.next_building_id()
        tile = self.game_map.tile_at(building.x, building.y)
        if tile.building_id is not None:
            pass
        self.buildings[building.id] = building
        tile.building_id = building.id
        return building.id

    def remove_building(self, building_id: int) -> None:
        building = self.buildings.pop(building_id, None)
        if building is None:
            return
        tile = self.game_map.tile_at(building.x, building.y)
        if tile.building_id == building_id:
            tile.building_id = None

    def transfer_building(self, building_id: int, new_owner_slot: int) -> None:
        self.buildings[building_id].owner_slot = new_owner_slot

    def apply_status_effect(self, target_unit_id: int, effect: ActiveStatusEffect) -> None:
        unit = self.units[target_unit_id]
        for existing in unit.status_effects:
            if existing.type == effect.type:
                existing.duration = max(existing.duration, effect.duration)
                existing.params = effect.params
                existing.source_slot = effect.source_slot
                return
        unit.status_effects.append(effect)

    def tick_status_effects(self, player_slot: int) -> None:
        for unit in self.units.values():
            if unit.owner_slot != player_slot:
                continue
            if not unit.status_effects:
                continue
            kept: list[ActiveStatusEffect] = []
            for effect in unit.status_effects:
                effect.duration -= 1
                if effect.duration > 0:
                    kept.append(effect)
            unit.status_effects = kept

    def record_action(self, player_slot: int, action: dict[str, Any]) -> None:
        self.action_log.append({
            "turn": self.turn,
            "slot": player_slot,
            "action": action,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id":              self.match_id,
            "map_id":                self.map_id,
            "game_map":              self.game_map.to_saved_map_dict(),
            "players":               [player_to_dict(p) for p in self.players],
            "time_control":          self.time_control.value,
            "starting_time_bank":    self.starting_time_bank,
            "time_increment":        self.time_increment,
            "deadline_hours":        self.deadline_hours,
            "timeout_forfeit_limit": self.timeout_forfeit_limit,
            "turn":                  self.turn,
            "current_player_slot":   self.current_player_slot,
            "status":                self.status.value,
            "winner_slot":           self.winner_slot,
            "units":                 {str(uid): unit_to_dict(u) for uid, u in self.units.items()},
            "buildings":             {str(bid): asdict(b) for bid, b in self.buildings.items()},
            "action_log":            self.action_log,
            "_next_unit_id":         self._next_unit_id,
            "_next_building_id":     self._next_building_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GameState":
        return cls(
            match_id=d["match_id"],
            map_id=d["map_id"],
            game_map=GameMap.from_saved_map_dict(d["game_map"]),
            players=[player_from_dict(p) for p in d["players"]],
            time_control=TimeControl(d.get("time_control", "live")),
            starting_time_bank=d.get("starting_time_bank", 300.0),
            time_increment=d.get("time_increment", 120.0),
            deadline_hours=d.get("deadline_hours", 24.0),
            timeout_forfeit_limit=d.get("timeout_forfeit_limit", 3),
            turn=d.get("turn", 0),
            current_player_slot=d.get("current_player_slot", 0),
            status=MatchStatus(d.get("status", "waiting")),
            winner_slot=d.get("winner_slot"),
            units={
                int(uid): unit_from_dict(u)
                for uid, u in d.get("units", {}).items()
            },
            buildings={
                int(bid): Building(**b)
                for bid, b in d.get("buildings", {}).items()
            },
            action_log=d.get("action_log", []),
            _next_unit_id=d.get("_next_unit_id", 1),
            _next_building_id=d.get("_next_building_id", 1),
        )

def unit_to_dict(u: Unit) -> dict[str, Any]:
    return {
        "id":                u.id,
        "type":              u.type,
        "owner_slot":        u.owner_slot,
        "x":                 u.x,
        "y":                 u.y,
        "hp":                u.hp,
        "sight":             u.sight,
        "armor":             u.armor,
        "max_hp":            u.max_hp,
        "model":             u.model,
        "weapons": [
            {
                "name": w.name, "type": w.type, "damage": w.damage,
                "ap": w.ap, "range": w.range, "description": w.description,
                "perks": [asdict(p) for p in w.perks],
            }
            for w in u.weapons
        ],
        "traits":            [asdict(t) for t in u.traits],
        "status_effects":    [asdict(e) for e in u.status_effects],
        "veterancy":         u.veterancy,
        "has_moved":         u.has_moved,
        "has_fired_weapon":  u.has_fired_weapon,
        "movement_remaining": u.movement_remaining,
        "max_movement":      u.max_movement,
        "moved_last_turn":   u.moved_last_turn,
        "fired_last_turn":   u.fired_last_turn,
    }

def unit_from_dict(d: dict[str, Any]) -> Unit:
    weapons = [
        Weapon(
            name=w["name"], type=w["type"], damage=w["damage"],
            ap=w.get("ap", 0), range=w.get("range", 1),
            description=w.get("description", ""),
            perks=[
                WeaponPerkApplication(
                    type=p["type"], duration=p.get("duration", 1),
                    params=p.get("params", {}),
                )
                for p in w.get("perks", [])
            ],
        )
        for w in d.get("weapons", [])
    ]
    traits = [
        UnitTrait(type=t["type"], params=t.get("params", {}))
        for t in d.get("traits", [])
    ]
    status_effects = [
        ActiveStatusEffect(
            type=e["type"], duration=e["duration"],
            source_slot=e["source_slot"], params=e.get("params", {}),
        )
        for e in d.get("status_effects", [])
    ]
    return Unit(
        id=d["id"], type=d["type"], owner_slot=d["owner_slot"],
        x=d["x"], y=d["y"], hp=d["hp"],
        sight=d.get("sight", 1),
        armor=d.get("armor", 0),
        max_hp=d.get("max_hp", d["hp"]),
        model=d.get("model"),
        weapons=weapons, traits=traits, status_effects=status_effects,
        veterancy=d.get("veterancy", 0),
        has_moved=d.get("has_moved", False),
        has_fired_weapon=d.get("has_fired_weapon", False),
        movement_remaining=d.get("movement_remaining", 0),
        max_movement=d.get("max_movement", 0),
        moved_last_turn=d.get("moved_last_turn", False),
        fired_last_turn=d.get("fired_last_turn", False),
    )

def player_to_dict(p: Player) -> dict[str, Any]:
    return {
        "slot":                    p.slot,
        "faction":                 p.faction,
        "color":                   p.color,
        "user_id":                 p.user_id,
        "resources":               dict(p.resources),
        "capital_building_id":     p.capital_building_id,
        "visible_tiles":           [list(t) for t in p.visible_tiles],
        "explored_tiles":          [list(t) for t in p.explored_tiles],
        "time_remaining_seconds":  p.time_remaining_seconds,
        "turn_started_at":         p.turn_started_at,
        "turn_deadline_ts":        p.turn_deadline_ts,
        "consecutive_timeouts":    p.consecutive_timeouts,
    }

def player_from_dict(d: dict[str, Any]) -> Player:
    return Player(
        slot=d["slot"], faction=d["faction"],
        color=d.get("color", "#ffffff"),
        user_id=d.get("user_id"),
        resources=dict(d.get("resources") or {k: 0 for k in RESOURCE_KEYS}),
        capital_building_id=d.get("capital_building_id"),
        visible_tiles={tuple(t) for t in d.get("visible_tiles", [])},
        explored_tiles={tuple(t) for t in d.get("explored_tiles", [])},
        time_remaining_seconds=d.get("time_remaining_seconds", 0.0),
        turn_started_at=d.get("turn_started_at"),
        turn_deadline_ts=d.get("turn_deadline_ts"),
        consecutive_timeouts=d.get("consecutive_timeouts", 0),
    )

DEFAULT_CAPITALS: dict[str, str] = {
    "presia": "presia_hq",
    "doon":   "doon_hq",
}
DEFAULT_COLORS: tuple[str, ...] = ("#367055", "#CBBD93")
CAPITAL_STARTING_HP    = 200
CAPITAL_STARTING_ARMOR = 3
DEFAULT_STARTING_UNIT = "riflemen"   # unit type to spawn at start

def create_match(
    *,
    match_id: int,
    map_id: int,
    game_map: GameMap,
    player_specs: list[dict[str, Any]],
    unit_registry: "UnitRegistry",   # <-- added parameter
    time_control: TimeControl = TimeControl.LIVE,
    starting_time_bank: float = 300.0,
    time_increment: float = 120.0,
    deadline_hours: float = 24.0,
    timeout_forfeit_limit: int = 3,
    capital_types: Optional[dict[str, str]] = None,
) -> GameState:
    game_map = copy.deepcopy(game_map)
    capitals = capital_types or DEFAULT_CAPITALS

    players: list[Player] = []
    for slot, spec in enumerate(player_specs):
        faction = spec["faction"]
        players.append(Player(
            slot=slot,
            faction=faction,
            color=spec.get("color", DEFAULT_COLORS[slot % len(DEFAULT_COLORS)]),
            user_id=spec.get("user_id"),
            time_remaining_seconds=(
                starting_time_bank if time_control is TimeControl.LIVE else 0.0
            ),
        ))

    state = GameState(
        match_id=match_id, map_id=map_id, game_map=game_map,
        players=players, time_control=time_control,
        starting_time_bank=starting_time_bank,
        time_increment=time_increment,
        deadline_hours=deadline_hours,
        timeout_forfeit_limit=timeout_forfeit_limit,
    )

    for slot, (sx, sy) in enumerate(game_map.spawns):
        faction = players[slot].faction
        capital_type = capitals.get(faction, f"{faction}_hq")
        building = Building(
            id=0, type=capital_type, owner_slot=slot,
            x=sx, y=sy,
            hp=CAPITAL_STARTING_HP, armor=CAPITAL_STARTING_ARMOR,
            is_capital=True,
        )
        bid = state.place_building(building)
        players[slot].capital_building_id = bid

        unit_def = unit_registry.get(faction, DEFAULT_STARTING_UNIT)
        if unit_def:
            spawn_xy = (sx, sy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = sx + dx, sy + dy
                if game_map.in_bounds(nx, ny):
                    t = game_map.tile_at(nx, ny)
                    if t.unit_id is None and t.building_id is None:
                        spawn_xy = (nx, ny)
                        break
            state.spawn_unit_from_definition(
                unit_def, owner_slot=slot, x=spawn_xy[0], y=spawn_xy[1]
            )
        else:
            print(f"Warning: no unit definition for {faction}/{DEFAULT_STARTING_UNIT}")

    return state