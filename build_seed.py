import argparse
import json
import sqlite3
from pathlib import Path
from db import SCHEMA_SQL, get_db_path
from extract_stdlib import extract_module
from load_data import load_functions

# Danh sách 119 hàm cốt lõi của 18 module
CORE_FUNCTIONS = {
    'builtins': [
        'abs', 'all', 'any', 'compile', 'dict', 'enumerate', 'filter', 'input',
        'int', 'isinstance', 'len', 'list', 'map', 'max', 'min', 'open', 'pow',
        'print', 'range', 'round', 'set', 'sorted', 'str', 'sum', 'super', 'type', 'zip'
    ],
    'math': [
        'ceil', 'cos', 'degrees', 'exp', 'factorial', 'floor', 'gcd', 'log',
        'log10', 'pow', 'radians', 'sin', 'sqrt', 'tan'
    ],
    'random': ['choice', 'choices', 'randint', 'random', 'sample', 'shuffle', 'uniform'],
    'json': ['dump', 'dumps', 'load', 'loads'],
    'os': ['chdir', 'getcwd', 'getenv', 'listdir', 'makedirs', 'mkdir', 'open', 'remove', 'rename', 'rmdir', 'system'],
    'os.path': ['abspath', 'basename', 'dirname', 'exists', 'isdir', 'isfile', 'join', 'split', 'splitext'],
    'time': ['perf_counter', 'sleep', 'strftime', 'strptime', 'time'],
    're': ['compile', 'findall', 'match', 'search', 'split', 'sub'],
    'shutil': ['copy', 'copy2', 'copytree', 'move', 'rmtree', 'which'],
    'csv': ['reader', 'writer'],
    'hashlib': ['md5', 'sha1', 'sha256'],
    'datetime': ['date', 'datetime', 'time', 'timedelta'],
    'collections': ['Counter', 'defaultdict', 'deque', 'namedtuple'],
    'itertools': ['chain', 'combinations', 'cycle', 'islice', 'permutations', 'product'],
    'functools': ['cache', 'lru_cache', 'namedtuple', 'partial', 'reduce', 'wraps'],
    'pathlib': ['Path'],
    'copy': ['copy', 'deepcopy'],
    'sys': ['exit', 'getsizeof'],
}

TARGET_MODULES = [
    'math', 'random', 'json', 'os', 'os.path', 'time', 're', 'shutil', 'csv', 'hashlib',
    'datetime', 'collections', 'itertools', 'functools', 'pathlib', 'copy', 'sys'
]

def build_in_memory_db():
    print("⏳ Initializing in-memory database...")
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_SQL)

    # 1. Load builtins
    print("📦 Loading builtins...")
    with open("builtin.json", "r", encoding="utf-8") as f:
        docs = json.load(f)
    load_functions("builtins", docs, conn, "Python Built-in Functions")

    # 2. Load standard libraries
    for mod_name in TARGET_MODULES:
        print(f"📦 Extracting & loading {mod_name}...")
        mod_docs = extract_module(mod_name)
        load_functions(mod_name, mod_docs, conn, f"Python {mod_name} standard library")

    # 3. Mark core functions
    print("⭐ Tagging core functions (is_important = 1)...")
    cur = conn.cursor()
    total_marked = 0
    for mod_name, funcs in CORE_FUNCTIONS.items():
        for fname in funcs:
            cur.execute("""
                UPDATE functions 
                SET is_important = 1 
                WHERE module_id = (SELECT id FROM modules WHERE name = ?) AND name = ?
            """, (mod_name, fname))
            total_marked += cur.rowcount
    conn.commit()
    print(f"✔ Tagged {total_marked} core functions!")
    return conn

def sql_quote(val):
    if val is None:
        return "NULL"
    clean = str(val).replace("'", "''")
    return f"'{clean}'"

def export_seed_sql(conn, output_path="seed.sql"):
    print(f"💾 Exporting clean seed data to {output_path}...")
    cur = conn.cursor()
    lines = [
        "-- PyDex Seed Data (Standard Library Definitions)",
        "BEGIN TRANSACTION;",
    ]

    # Modules
    cur.execute("SELECT id, name, description FROM modules ORDER BY id")
    for mod_id, name, desc in cur.fetchall():
        desc_val = sql_quote(desc)
        lines.append(f"INSERT OR IGNORE INTO modules (id, name, description) VALUES ({mod_id}, '{name}', {desc_val});")

    # Functions (reset discovered=0 and my_notes=NULL for clean distribution)
    cur.execute("SELECT id, name, module_id, description, is_important FROM functions ORDER BY id")
    for func_id, name, module_id, desc, is_important in cur.fetchall():
        desc_val = sql_quote(desc)
        lines.append(f"INSERT OR IGNORE INTO functions (id, name, module_id, description, my_notes, discovered, is_important) VALUES ({func_id}, '{name}', {module_id}, {desc_val}, NULL, 0, {is_important});")

    # Signatures
    cur.execute("SELECT id, function_id, raw_signature FROM signatures ORDER BY id")
    for sig_id, func_id, raw_sig in cur.fetchall():
        sig_val = raw_sig.replace("'", "''")
        lines.append(f"INSERT OR IGNORE INTO signatures (id, function_id, raw_signature) VALUES ({sig_id}, {func_id}, '{sig_val}');")

    # Arguments
    cur.execute("SELECT id, signature_id, name, order_index, default_value, required FROM arguments ORDER BY id")
    for arg_id, sig_id, name, order_idx, default_val, req in cur.fetchall():
        name_val = name.replace("'", "''")
        def_val = sql_quote(default_val)
        lines.append(f"INSERT OR IGNORE INTO arguments (id, signature_id, name, order_index, default_value, required) VALUES ({arg_id}, {sig_id}, '{name_val}', {order_idx}, {def_val}, {req});")

    lines.append("COMMIT;")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✔ Successfully written {len(lines)} lines to {output_path}!")

def reset_local_db(seed_path="seed.sql"):
    db_path = get_db_path()
    print(f"🔄 Resetting local database at {db_path}...")
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        with open(seed_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.execute("PRAGMA user_version = 2;")
        conn.commit()
    finally:
        conn.close()
    print("✔ Local database reset and initialized with fresh seed data!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyDex Master Seed Builder")
    parser.add_argument("--reset-local", action="store_true", help="Reset local ~/.pydex/pydex.db with fresh seed")
    args = parser.parse_args()

    # Chạy pipeline tạo DB trong RAM và xuất seed.sql
    mem_conn = build_in_memory_db()
    export_seed_sql(mem_conn, "seed.sql")
    mem_conn.close()

    if args.reset_local:
        reset_local_db("seed.sql")

    print("\n✨ All operations completed successfully!")