from __future__ import annotations
from . import fog

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Optional

from .state import GameState, MatchStatus as StateMatchStatus
from . import actions
from . import turn_order
from . import economy
from . import timer
from .unit import UnitRegistry
from .parser import register_units
from . import traits, perks


class EventType(str, Enum):
    MATCH_STARTED  = "match_started"
    TURN_STARTED   = "turn_started"
    ACTION_APPLIED = "action_applied"
    TURN_ENDED     = "turn_ended"
    PLAYER_TIMEOUT = "player_timeout"
    PLAYER_FORFEIT = "player_forfeit"
    MATCH_ENDED    = "match_ended"


@dataclass
class Event:
    type: EventType
    turn: int
    player_slot: Optional[int]
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


class MatchStatus(str, Enum):
    WAITING     = "waiting"
    IN_PROGRESS = "in_progress"
    ENDED       = "ended"


class MatchEngine:
    def __init__(
        self,
        state: GameState,
        *,
        now_fn: Callable[[], float] = time.time,
        unit_registry: Optional[UnitRegistry] = None,
    ):
        self.state = state
        self._now = now_fn
        self._events: list[Event] = []
        self.status = MatchStatus.WAITING
        
        if unit_registry is not None:
            actions.set_unit_registry(unit_registry)
            self.unit_registry = unit_registry
        else:
            self.unit_registry = register_units("data/units")
            actions.set_unit_registry(self.unit_registry)

    def start(self) -> None:
        if self.status is not MatchStatus.WAITING:
            return

        self.status = MatchStatus.IN_PROGRESS
        self.state.turn = 1
        self.state.current_player_slot = 0
        self.state.status = StateMatchStatus.IN_PROGRESS

        fog.update_all_fog(self.state)

        tc = getattr(self.state, "time_control", "live")
        self.emit(EventType.MATCH_STARTED, player_slot=None, payload={
            "map_id": getattr(self.state, "map_id", None),
            "players": [self.player_summary(s) for s in self.player_slots()],
            "time_control": tc.value if hasattr(tc, "value") else tc,
        })

        self.start_turn(0)

    def submit_action(self, player_slot: int, action: dict[str, Any]) -> None:
        self.require_in_progress()
        self.require_known_player(player_slot)

        if player_slot != self.state.current_player_slot:
            raise ValueError(f"Not your turn (player {player_slot}, current {self.state.current_player_slot})")

        actions.validate(self.state, player_slot, action)
        result = actions.apply(self.state, player_slot, action)

        fog.update_all_fog(self.state)

        self.state.record_action(player_slot, action)

        self.emit(EventType.ACTION_APPLIED, player_slot=player_slot, payload={
            "action": action,
            "result": result or {},
        })

        winner = self.check_win_condition()
        if winner is not None:
            self.end_match(winner_slot=winner, reason="capital_captured")

    def end_turn(self, player_slot: int) -> None:
        self.require_in_progress()
        self.require_known_player(player_slot)

        if player_slot != self.state.current_player_slot:
            raise ValueError(f"Not your turn (player {player_slot}, current {self.state.current_player_slot})")

        self.resolve_end_of_turn(player_slot)
        self.finalize_timer(player_slot)

        next_slot = self.next_slot(player_slot)

        self.emit(EventType.TURN_ENDED, player_slot=player_slot, payload={
            "next_slot": next_slot,
        })

        if next_slot == 0:
            self.state.turn += 1

        self.state.current_player_slot = next_slot
        self.start_turn(next_slot)

    def forfeit(self, player_slot: int, *, reason: str = "resigned") -> None:
        self.require_in_progress()
        self.require_known_player(player_slot)

        self.emit(EventType.PLAYER_FORFEIT, player_slot=player_slot, payload={
            "reason": reason,
        })

        winner = self.next_slot(player_slot)
        self.end_match(winner_slot=winner, reason=f"forfeit:{reason}")

    def tick(self, now: Optional[float] = None) -> None:
        if self.status is not MatchStatus.IN_PROGRESS:
            return

        now = now or self._now()
        current = self.state.current_player_slot

        if timer.has_expired(self.state, current, now):
            self.on_timer_expired(current)

    def get_state(self) -> GameState:
        return self.state

    def get_status(self) -> MatchStatus:
        return self.status

    def is_ended(self) -> bool:
        return self.status is MatchStatus.ENDED

    def current_player(self) -> int:
        return self.state.current_player_slot

    def drain_events(self) -> list[Event]:
        events, self._events = self._events, []
        return events

    def start_turn(self, player_slot: int) -> None:
        economy.tick_income(self.state, player_slot)
        turn_order.reset_unit_budgets(self.state, player_slot)
        timer.start_turn_clock(self.state, player_slot, self._now())

        heal_events = traits.apply_turn_traits_for_player(self.state, player_slot)
        for ev in heal_events:
            self.emit(EventType.ACTION_APPLIED, player_slot=player_slot, payload={
                "kind": "trait_tick",
                "trait": ev["type"],
                "unit_id": ev["unit_id"],
                "hp_delta": ev["hp_delta"],
                "new_hp": ev["new_hp"],
            })

        burn_events = perks.apply_tick_damage_for_player(self.state, player_slot)
        for ev in burn_events:
            self.emit(EventType.ACTION_APPLIED, player_slot=player_slot, payload={
                "kind": "perk_tick",
                "perk": ev["type"],
                "unit_id": ev["unit_id"],
                "damage": ev["damage"],
                "destroyed": ev["destroyed"],
            })

        fog.update_all_fog(self.state)

        self.emit(EventType.TURN_STARTED, player_slot=player_slot, payload={
            "turn": self.state.turn,
            "resources": self.player_resources(player_slot),
        })
    def resolve_end_of_turn(self, player_slot: int) -> None:
        self.state.tick_status_effects(player_slot)

    def finalize_timer(self, player_slot: int) -> None:
        timer.end_turn_clock(self.state, player_slot, self._now())

    def on_timer_expired(self, player_slot: int) -> None:
        self.emit(EventType.PLAYER_TIMEOUT, player_slot=player_slot, payload={
            "time_control": getattr(self.state, "time_control", "live"),
        })

        if getattr(self.state, "time_control", "live") == "24h":
            player = self.state.players[player_slot]
            player.consecutive_timeouts = getattr(player, "consecutive_timeouts", 0) + 1
            limit = getattr(self.state, "timeout_forfeit_limit", 3)
            if player.consecutive_timeouts >= limit:
                self.forfeit(player_slot, reason="timeouts")
                return

        self.end_turn(player_slot)

    def check_win_condition(self) -> Optional[int]:
        for slot in range(len(self.state.players)):
            capital_id = self.state.players[slot].capital_building_id

            # if a player loses their capital they lose
            if capital_id is not None and capital_id not in self.state.buildings:
                return self.next_slot(slot)

            capital = self.state.get_capital(slot)

            if capital is None:
                continue

            if capital.owner_slot != slot:
                return capital.owner_slot

        return None

    def end_match(self, *, winner_slot: int, reason: str) -> None:
        if self.status is MatchStatus.ENDED:
            return

        self.status = MatchStatus.ENDED
        self.state.status = StateMatchStatus.ENDED
        self.state.winner_slot = winner_slot

        self.emit(EventType.MATCH_ENDED, player_slot=None, payload={
            "winner_slot": winner_slot,
            "reason": reason,
            "final_turn": self.state.turn,
        })

    def require_in_progress(self) -> None:
        if self.status is not MatchStatus.IN_PROGRESS:
            raise RuntimeError("Match is not in progress")

    def require_known_player(self, player_slot: int) -> None:
        if player_slot not in range(len(self.state.players)):
            raise ValueError(f"Invalid player slot {player_slot}")

    def emit(
        self,
        event_type: EventType,
        *,
        player_slot: Optional[int],
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        self._events.append(Event(
            type=event_type,
            turn=self.state.turn,
            player_slot=player_slot,
            payload=payload or {},
        ))

    def player_slots(self) -> Iterable[int]:
        return range(len(self.state.players))

    def next_slot(self, slot: int) -> int:
        return (slot + 1) % len(self.state.players)

    def player_summary(self, slot: int) -> dict[str, Any]:
        p = self.state.players[slot]
        return {
            "slot": slot,
            "faction": getattr(p, "faction", None),
            "user_id": getattr(p, "user_id", None),
        }

    def player_resources(self, slot: int) -> dict[str, int]:
        return dict(self.state.players[slot].resources)
