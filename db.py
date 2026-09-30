import sqlite3
from pathlib import Path

CURRENT_DATA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    description TEXT,
    my_notes TEXT,
    discovered BOOLEAN DEFAULT 0,
    is_important BOOLEAN DEFAULT 0,
    CONSTRAINT uq_func UNIQUE (module_id, name)
);

CREATE TABLE IF NOT EXISTS signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    raw_signature TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS arguments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signature_id INTEGER NOT NULL REFERENCES signatures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    default_value TEXT,
    required BOOLEAN DEFAULT 1
);
"""

def get_db_path() -> Path:
    pydex_dir = Path.home() / ".pydex"
    pydex_dir.mkdir(parents=True, exist_ok=True)
    return pydex_dir / "pydex.db"

def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_SQL)

    cur = conn.cursor()
    try:
        cur.execute("PRAGMA user_version")
        db_version = cur.fetchone()[0]
        if db_version < CURRENT_DATA_VERSION:
            seed_file = Path(__file__).parent / "seed.sql"
            if seed_file.exists():
                with open(seed_file, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            cur.execute(f"PRAGMA user_version = {CURRENT_DATA_VERSION}")
            conn.commit()
    finally:
        cur.close()
    return conn

if __name__ == "__main__":
    try:
        conn = get_connection()
        print(f"Connected successfully to SQLite at: {get_db_path()}")
        conn.close()
    except Exception as e:
        print(f"Connection error: {e}")