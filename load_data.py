import json
from db import get_connection

def load_functions(module_name, docs, conn, module_desc=""):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO modules (name, description) VALUES (?, ?)
            ON CONFLICT (name) DO UPDATE SET description = excluded.description
            RETURNING id
        """, (module_name, module_desc))
        module_id = cur.fetchone()[0]

        for item in docs:
            cur.execute("""
                INSERT INTO functions (module_id, name, description) VALUES (?, ?, ?)
                ON CONFLICT (module_id, name) DO UPDATE SET description = excluded.description
                RETURNING id
            """, (module_id, item["name"], item["description"]))
            function_id = cur.fetchone()[0]

            cur.execute("DELETE FROM signatures WHERE function_id = ?", (function_id,))
            for sig in item["signatures"]:
                cur.execute("""
                    INSERT INTO signatures (function_id, raw_signature)
                    VALUES (?, ?) RETURNING id
                """, (function_id, sig["raw_signature"]))
                signature_id = cur.fetchone()[0]

                for param in sig["params"]:
                    req_val = 1 if param.get("required", True) else 0
                    cur.execute("""
                        INSERT INTO arguments (signature_id, name, default_value, required, order_index)
                        VALUES (?, ?, ?, ?, ?)
                    """, (signature_id, param["name"], param["default_value"], req_val, param["order_index"]))
        conn.commit()
    finally:
        cur.close()

if __name__ == "__main__":
    with open("builtin.json", "r", encoding="utf-8") as f:
        docs = json.load(f)

    conn = get_connection()
    load_functions("builtins", docs, conn, "Python Built-in Functions")
    conn.close()
    print("Data loaded successfully into SQLite!")
