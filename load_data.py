import json
from db import get_connection

def load_functions(docs, conn):
    with conn.cursor() as cur:
        for item in docs:
            cur.execute("""
                INSERT INTO functions (name, official_docstring) VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET official_docstring = EXCLUDED.official_docstring
                RETURNING id
            """, (item["name"], item["description"]))

            function_id = cur.fetchone()[0]
            cur.execute("DELETE FROM arguments WHERE function_id = %s", (function_id,))
            for param in item["params"]:
                cur.execute("""
                    INSERT INTO arguments (function_id, name, default_value, required, order_index)
                    VALUES (%s, %s, %s, %s, %s)
                """, (function_id, param["name"], param["default_value"], param["required"], param["order_index"]))
    conn.commit()

if __name__ == "__main__":
    with open("builtin.json", "r", encoding="utf-8") as f:
        docs = json.load(f)

    conn = get_connection()
    load_functions(docs, conn)
    conn.close()
    print("Data loaded successfully!")
