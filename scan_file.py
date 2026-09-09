import ast
import builtins
import inspect
import sys
from db import get_connection

def find_builtin_call(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except FileNotFoundError:
        print(f"Error: {file_path} does not exist")
        return None
    except SyntaxError:
        print(f"Error: {file_path} has syntax error")
        return None
    builtins_name = {
        name for name, obj in builtins.__dict__.items()
        if (inspect.isbuiltin(obj) or inspect.isclass(obj))
        and not (isinstance(obj, type) and issubclass(obj, BaseException))
    }
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in builtins_name:
                found.add(func_name)
    return found
def lookup_and_mark(names, conn):
    with conn.cursor() as cur:
        for name in names:
            cur.execute("SELECT id,discovered FROM functions WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                func_id, discovered = row
                if not discovered:
                    cur.execute("UPDATE functions SET discovered = TRUE WHERE id = %s", (func_id,))
                    print(f"'{name}' is discovered!")
            else:
                print(f"Function '{name}' not found.")
    conn.commit()
if __name__ == "__main__":
    if len(sys.argv) <2:
        print("Usage: python scan_file.py <file_path>") 
        sys.exit(1)
    file_path = sys.argv[1]
    result = find_builtin_call(file_path)
    if result is None:
        sys.exit(1)
    if not result:
        print("No built-in functions found in file")
        sys.exit(1)
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Can't connect to database: {e}")
        sys.exit(1)
    lookup_and_mark(result, conn)
    conn.close()
    print("Scan completed!")
