import sqlite3

DB_FILE = "data.db"
db = sqlite3.connect(DB_FILE)
c = db.cursor()

TABLES = """
    PRAGMA journal_mode = WAL; -- Let's read and write at same time
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT    NOT NULL, -- Do this so we cant see password (good practice)
        elo           INTEGER NOT NULL DEFAULT 1000
    );
"""


c.executescript(TABLES);
# lwk gotta make this handle connections individually. Don't make it single db connection
