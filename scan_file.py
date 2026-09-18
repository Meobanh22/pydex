import ast
import builtins
import inspect
import sys
from db import get_connection

def find_builtin_call(tree):
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
    return [("builtins", f"{name}") for name in found]

def find_library_call(tree, module_map, func_map, module):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name) and node.func.value.id in module_map and module_map[node.func.value.id] in module:
                found.add((module_map[node.func.value.id], func_name))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in func_map and func_map[func_name][0] in module:
                found.add((func_map[func_name][0], func_map[func_name][1]))
    return list(found)

def build_import_maps(tree):
    module_map = {}
    func_map = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == None:
                    module_map[alias.name] = alias.name
                else:
                    module_map[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname==None:
                    func_map[alias.name] = (node.module, alias.name)
                else:
                    func_map[alias.asname] = (node.module, alias.name)
    return module_map, func_map

def lookup_and_mark(names, conn):
    with conn.cursor() as cur:
        for name in names:
            cur.execute("SELECT f.id, f.discovered FROM functions f LEFT JOIN modules m ON f.module_id = m.id WHERE f.name = %s AND m.name = %s", (name[1], name[0]))
            row = cur.fetchone()
            if row:
                func_id, discovered = row
                if not discovered:
                    cur.execute("UPDATE functions SET discovered = TRUE WHERE id = %s", (func_id,))
                    print(f"'{name}' is discovered!")
            else:
                print(f"Function '{name}' not found.")
    conn.commit()

def scan_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except FileNotFoundError:
        print(f"Error: {file_path} does not exist")
        return None
    except SyntaxError:
        print(f"Error: {file_path} has syntax error")
        return None
    module = {'math', 'random', 'json'}
    builtins = find_builtin_call(tree)
    module_map, func_map = build_import_maps(tree)
    stdlibs =  find_library_call(tree, module_map, func_map, module)
    result = builtins + stdlibs
    return result

if __name__ == "__main__":
    if len(sys.argv) <2:
        print("Usage: python scan_file.py <file_path>") 
        sys.exit(1)
    file_path = sys.argv[1]
    result = scan_file(file_path)
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
