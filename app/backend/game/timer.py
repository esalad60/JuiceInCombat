
from __future__ import annotations

from .state import GameState


def start_turn_clock(state: "GameState", player_slot: int, now: float) -> None:
    player = state.get_player(player_slot)

    if is_live(state):
        player.turn_started_at = now
        player.turn_deadline_ts = None
    else:
        deadline = now + (state.deadline_hours * 3600.0)
        player.turn_deadline_ts = deadline
        player.turn_started_at = now


def end_turn_clock(state: "GameState", player_slot: int, now: float) -> None:
    player = state.get_player(player_slot)

    if is_live(state):
        if player.turn_started_at is None:
            return

        elapsed = max(0.0, now - player.turn_started_at)
        new_bank = player.time_remaining_seconds - elapsed + state.time_increment
        player.time_remaining_seconds = max(0.0, new_bank)
        player.turn_started_at = None
    else:
        player.turn_deadline_ts = None
        player.turn_started_at = None
        if not getattr(player, "_ending_via_timeout", False):
            player.consecutive_timeouts = 0


def has_expired(state: "GameState", player_slot: int, now: float) -> bool:
    player = state.get_player(player_slot)

    if is_live(state):
        if player.turn_started_at is None:
            return False
        elapsed = now - player.turn_started_at
        return elapsed >= player.time_remaining_seconds
    else:
        if player.turn_deadline_ts is None:
            return False
        return now > player.turn_deadline_ts


def effective_time_remaining(
    state: "GameState",
    player_slot: int,
    now: float,
) -> float:
    player = state.get_player(player_slot)

    if is_live(state):
        if player.turn_started_at is None:
            return player.time_remaining_seconds
        elapsed = now - player.turn_started_at
        return max(0.0, player.time_remaining_seconds - elapsed)
    else:
        if player.turn_deadline_ts is None:
            return 0.0
        return player.turn_deadline_ts - now

def is_live(state: "GameState") -> bool:
    return state.time_control.value == "live"