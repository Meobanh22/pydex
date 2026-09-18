import inspect
import importlib
from db import get_connection
from load_data import load_functions

def extract_module(module_name):
    mod = importlib.import_module(module_name)
    all_func_mod = []
    functions = [
        (name, obj) for name, obj in inspect.getmembers(mod, inspect.isroutine)
        if not name.startswith("_")
    ]
    for function in functions:
        name, obj=function
        try:
            sig = inspect.signature(obj)
            raw_sig = f"{name}{sig}"
            params = []
            idx = 1
            for param_name, param in sig.parameters.items():
                has_default = param.default is not inspect.Parameter.empty
                default_val = str(param.default) if has_default else None
                required = not has_default
                params.append({
                    "name": param_name,
                    "default_value": default_val,
                    "required": required,
                    "order_index": idx
                })
                idx+=1
        except (ValueError, TypeError):
            raw_sig = f"{name}()"
            params = []
        doc = obj.__doc__ or ""
        first_line = doc.strip().split("\n")[0] if doc else "No description available"
        signatures=[{
            "raw_signature": raw_sig,
            "params": params
        }]
        all_func_mod.append({
            "name": name,
            "signatures": signatures,
            "description": first_line
        })
    return all_func_mod

if __name__ == "__main__":
    target_modules = ["math", "random", "json"]
    conn = get_connection()
    for mod_name in target_modules:
        print(f"{mod_name}")
        docs = extract_module(mod_name)
        load_functions(mod_name, docs, conn, f"Python {mod_name} standard library")
        print(f"Load {len(docs)} functions from {mod_name}!")
    conn.close()