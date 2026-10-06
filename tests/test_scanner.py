import ast
from pathlib import Path
from scan_file import (
    get_dotted_name,
    find_builtin_call,
    build_import_maps,
    find_library_call,
    get_py_files,
    scan_target
)

def test_get_dotted_name():
    # Test for simple name
    node1 = ast.parse("print('Hello')").body[0].value.func
    assert get_dotted_name(node1) == "print"

    # Test for attribute access
    node2 = ast.parse("os.path.join('a', 'b')").body[0].value.func
    assert get_dotted_name(node2) == "os.path.join"

def test_find_builtin_call():
    code = "len([1,2]); print('Hello'); sum([1,2,3])"
    tree = ast.parse(code)
    calls = find_builtin_call(tree)
    name = {name for mod, name in calls}
    assert "len" in name
    assert "print" in name
    assert "sum" in name

def test_import_variations():
    code = """
import math
math.sqrt(144)

from math import ceil
ceil(3.7)
    
import random as rng
rng.randint(1, 10)
    """
    tree = ast.parse(code)
    module_map, func_map = build_import_maps(tree)
    valid_modules = {"math", "random"}

    calls = set(find_library_call(tree, module_map, func_map, valid_modules))
    assert ("math", "sqrt") in calls
    assert ("math", "ceil") in calls
    assert ("random", "randint") in calls

def test_chained_and_submodule_calls():
    code = """
import os
os.path.join('a', 'b')
    
from os import path
path.exists('a/b')

from os.path import isfile
isfile('a/b')

import datetime
datetime.datetime.now()

from datetime import datetime as dt
dt.now()
    """
    tree = ast.parse(code)
    module_map, func_map = build_import_maps(tree)
    valid_modules = {"os", "os.path", "datetime"}
    calls = set(find_library_call(tree, module_map, func_map, valid_modules))
    assert ("os.path", "join") in calls
    assert ("os.path", "exists") in calls
    assert ("os.path", "isfile") in calls
    assert ("datetime", "datetime") in calls

def test_scan_target_workflow(tmp_path, test_db):
    # Create a temporary Python file
    test_file = tmp_path / "test_script.py"
    test_file.write_text("import math\nmath.sqrt(25)\nprint('ok')", encoding="utf-8")

    # First time scan
    res1 = scan_target(tmp_path, test_db)
    assert res1["status"] == "ok"
    assert res1["file_count"] == 1
    new_funcs = [item["name"] for item in res1["newly_discovered"]]
    assert "sqrt" in new_funcs
    assert "print" in new_funcs

    # Second time scan (should not discover new functions)
    res2 = scan_target(tmp_path, test_db)
    assert len(res2["newly_discovered"]) == 0
    already = [item["name"] for item in res2["already_discovered"]]
    assert "sqrt" in already
    assert "print" in already

def test_get_py_ignores_dirs(tmp_path):
    # Create a temporary directory having venv and __pycache__
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "bad.py").write_text("", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "bad2.py").write_text("", encoding="utf-8")
    (tmp_path / "good.py").write_text("print('Hello')", encoding="utf-8")

    py_files = get_py_files(tmp_path)
    file_name = [f.name for f in py_files]
    assert file_name == ["good.py"]