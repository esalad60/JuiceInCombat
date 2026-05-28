import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Any, Dict, List
import argparse

SCHEMA_VERSION = 1

TABLES = """
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;

    -- Users
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        password      TEXT    NOT NULL,
        elo           INTEGER NOT NULL DEFAULT 1000,
        is_admin      INTEGER NOT NULL DEFAULT 0,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Map definitions
    CREATE TABLE IF NOT EXISTS maps (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT    NOT NULL UNIQUE,
        width         INTEGER NOT NULL,
        height        INTEGER NOT NULL,
        json_data     TEXT    NOT NULL,   -- Full GameMap.to_saved_map_dict() JSON
        author_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS matches (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        map_id        INTEGER NOT NULL REFERENCES maps(id),
        time_control  TEXT    NOT NULL DEFAULT 'live',   -- 'live' or '24h'
        status        TEXT    NOT NULL DEFAULT 'waiting', -- 'waiting', 'in_progress', 'ended'
        winner_slot   INTEGER,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at    TIMESTAMP,
        ended_at      TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS match_players (
        match_id      INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
        slot          INTEGER NOT NULL,   -- 0 or 1
        user_id       INTEGER NOT NULL REFERENCES users(id),
        faction       TEXT    NOT NULL,   -- 'presia', 'doon'
        color         TEXT,
        PRIMARY KEY (match_id, slot),
        UNIQUE (match_id, user_id)        -- A user can't be both slots
    );

    -- Game state snapshots (for validation)
    CREATE TABLE IF NOT EXISTS match_snapshots (
        match_id      INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
        turn          INTEGER NOT NULL,
        snapshot      TEXT    NOT NULL,   -- Full GameState.to_dict() JSON
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (match_id, turn)
    );

    -- Not too sure if needed rn
    CREATE TABLE IF NOT EXISTS schema_version (
        version       INTEGER PRIMARY KEY,
        applied_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""

INDICES = """
    CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
    CREATE INDEX IF NOT EXISTS idx_match_players_user ON match_players(user_id);
    CREATE INDEX IF NOT EXISTS idx_snapshots_match ON match_snapshots(match_id);
"""

DB_PATH = Path(__file__).resolve().parents[2] / "data.db"

def get_db_path() -> Path:
    return DB_PATH.resolve()

def init_db(force: bool = False) -> None:
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(TABLES)
    conn.executescript(INDICES)
    
    current = conn.cursor()
    current.execute("SELECT version FROM schema_version LIMIT 1")
    if not current.fetchone():
        current.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        current = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = current.fetchone()
        return dict(row) if row else None

def create_user(username: str, password_hash: str, is_admin: bool = False) -> int:
    with get_db() as conn:
        current = conn.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
            (username, password_hash, 1 if is_admin else 0)
        )
        return current.lastrowid

def create_map(name: str, width: int, height: int, json_data: str, author_id: Optional[int] = None) -> int:
    with get_db() as conn:
        current = conn.execute(
            "INSERT INTO maps (name, width, height, json_data, author_id) VALUES (?, ?, ?, ?, ?)",
            (name, width, height, json_data, author_id)
        )
        return current.lastrowid

def get_map(map_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        current = conn.execute("SELECT * FROM maps WHERE id = ?", (map_id,))
        row = current.fetchone()
        return dict(row) if row else None

def create_match(map_id: int, time_control: str = "live") -> int:
    with get_db() as conn:
        current = conn.execute(
            "INSERT INTO matches (map_id, time_control, status) VALUES (?, ?, ?)",
            (map_id, time_control, 'waiting')
        )
        return current.lastrowid

def add_match_player(match_id: int, slot: int, user_id: int, faction: str, color: str = "#ffffff") -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO match_players (match_id, slot, user_id, faction, color) VALUES (?, ?, ?, ?, ?)",
            (match_id, slot, user_id, faction, color)
        )

def save_match_state(match_id: int, turn: int, game_state_dict: dict) -> None:
    snapshot_json = json.dumps(game_state_dict)
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO match_snapshots (match_id, turn, snapshot) VALUES (?, ?, ?)",
            (match_id, turn, snapshot_json)
        )

def load_latest_match_state(match_id: int) -> Optional[dict]:
    with get_db() as conn:
        current = conn.execute(
            "SELECT snapshot FROM match_snapshots WHERE match_id = ? ORDER BY turn DESC LIMIT 1",
            (match_id,)
        )
        row = current.fetchone()
        return json.loads(row["snapshot"]) if row else None

def close_db_connections() -> None:
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Game database setup")
    parser.add_argument("--force", action="store_true", help="Delete existing DB and recreate")
    args = parser.parse_args()
    
    init_db(force=args.force)