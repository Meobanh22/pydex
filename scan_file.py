import ast
import builtins
import inspect
import sys
from db import get_connection
import os
from pathlib import Path

IGNORED_DIRS = {
    "venv", ".venv", "env", ".env",
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", ".nox", ".vscode", ".idea",
    "build", "dist", "node_modules",
} 

def get_py_files(target_path):
    target = Path(target_path)
    if not target.exists():
        return []
    if target.is_file():
        return [target] if target.suffix == ".py" else []
    py_file = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [
            d for d in dirs if d not in IGNORED_DIRS
            and not d.startswith(".")
            and not d.endswith(".egg-info")
        ]
        for file in files:
            if file.endswith(".py"):
                py_file.append(Path(root) / file)
    return sorted(py_file)

def get_dotted_name(node):
    parts = []
    curr = node
    while isinstance(curr, ast.Attribute):
        parts.append(curr.attr)
        curr = curr.value
    if isinstance(curr, ast.Name):
        parts.append(curr.id)
        return ".".join(reversed(parts))
    return None

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
    return tuple(("builtins", f"{name}") for name in found)

def find_library_call(tree, module_map, func_map, valid_modules):
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        dotted_name = get_dotted_name(node.func)
        if not dotted_name:
            continue
        if "." not in dotted_name:
            if dotted_name in func_map:
                mod_name, func_name = func_map[dotted_name]
                if mod_name in valid_modules:
                    found.add((mod_name, func_name))
        else:
            prefix, func_name = dotted_name.rsplit(".", 1)
            if prefix in module_map and module_map[prefix] in valid_modules:
                found.add((module_map[prefix], func_name))
            elif "." in prefix:
                top_pkg, sub_part = prefix.split(".", 1)
                if top_pkg in module_map:
                    resolved_mod = f"{module_map[top_pkg]}.{sub_part}"
                    if resolved_mod in valid_modules:
                        found.add((resolved_mod, func_name))
                    elif module_map[top_pkg] in valid_modules:
                        sub_cls = sub_part.split(".", 1)[0]
                        found.add((module_map[top_pkg], sub_cls))
            elif prefix in func_map:
                parent_mod, parent_name = func_map[prefix]
                if parent_mod in valid_modules:
                    found.add((parent_mod, parent_name))
    return tuple(found)

def build_import_maps(tree):
    module_map = {}
    func_map = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.asname if alias.asname is not None else alias.name
                module_map[target] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                target = alias.asname if alias.asname is not None else alias.name
                func_map[target] = (node.module, alias.name)
                # submodule import, e.g., from os import path
                full_submod = f"{node.module}.{alias.name}"
                module_map[target] = full_submod
    return module_map, func_map

def scan_target(target_path, conn):
    target = Path(target_path)
    if not target.exists():
        return {"status": "not_found", "target": str(target_path)}

    py_files = get_py_files(target)
    if not py_files:
        return {"status": "no_files", "target": str(target_path)}

    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM modules WHERE name != 'builtins'")
        valid_modules = { row[0] for row in cur.fetchall()}
    finally:
        cur.close()
    total_calls = 0
    detected_pairs = []
    for fpath in py_files:
        calls = scan_file(fpath, valid_modules)
        total_calls += len(calls)
        detected_pairs.extend(calls)
    unique_pairs = sorted(set(detected_pairs))
    newly_discovered = []
    already_discovered = []
    if unique_pairs:
        cur = conn.cursor()
        try:
            for mod_name, func_name in unique_pairs:
                cur.execute("""SELECT f.id, f.discovered, f.is_important
                            FROM functions f JOIN modules m ON f.module_id = m.id
                            WHERE m.name = ? AND f.name = ?""", (mod_name, func_name))
                row = cur.fetchone()
                if row:
                    func_id, discorved, is_important = row
                    item = {
                        "id": func_id,
                        "module": mod_name,
                        "name": func_name,
                        "is_important": bool(is_important)
                    }
                    if not discorved:
                        cur.execute("UPDATE functions SET discovered = 1 WHERE id = ?", (func_id,))
                        newly_discovered.append(item)
                    else:
                        already_discovered.append(item)
            conn.commit()
        finally:
            cur.close()
    return {
        "status": "ok",
        "target": str(target_path),
        "file_count": len(py_files),
        "total_calls": total_calls,
        "newly_discovered": newly_discovered,
        "already_discovered": already_discovered,
    }

def scan_file(file_path, valid_modules=None):
    if valid_modules is None:
        valid_modules = {"math", "random", "json", "os",
                         "time", "re", "shutil", "csv", "hashlib"}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (FileNotFoundError, SyntaxError, UnicodeDecodeError):
        return []
    builtins = find_builtin_call(tree)
    module_map, func_map = build_import_maps(tree)
    stdlibs =  find_library_call(tree, module_map, func_map, valid_modules)
    return builtins + stdlibs

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Cannot connect to pydex: {e}")
        sys.exit(1)
    result = scan_target(target, conn)
    conn.close()

    if result["status"] == "not_found":
        print(f"Target path does not exist: {target}")
        sys.exit(1)
    if result["status"] == "no_files":
        print(f"No Python files found in: {target}")
        sys.exit(1)
    
    for item in result["newly_discovered"]:
        star = "★ " if item["is_important"] else "✦ "
        print(f"{star}Discovered: {item['module']}.{item['name']}()")
    print(f"\nScan completed! Scanned {result['file_count']} file(s).")
    print(f"Total calls: {result['total_calls']}, New: {len(result['newly_discovered'])}, Already known: {len(result['already_discovered'])}")
    print("Scan completed!")