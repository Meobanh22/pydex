import sqlite3
import pytest
from pathlib import Path
from db import SCHEMA_SQL

@pytest.fixture
def test_db():
    # Create an in-memory SQLite database for testing
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_SQL)

    # Seed the database with initial data from seed_data.sql if it exists
    seed_data_path = Path(__file__).parent.parent / "seed.sql"
    if seed_data_path.exists():
        with open(seed_data_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

    yield conn
    conn.close()