# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========


def test_all_exports_from_camel():
    # Simulate `from camel import *` and capture the resulting namespace
    ns = {}
    exec("from camel import *", ns)

    assert 'set_log_level' in ns
    assert 'enable_logging' in ns
    assert 'disable_logging' in ns
    assert 'camel' not in ns


def test_all_exports_type():
    import camel

    assert isinstance(camel.__all__, list)

    for item in camel.__all__:
        assert isinstance(item, str)


def _assigned_names(target, out):
    import ast

    if isinstance(target, ast.Name):
        out.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            _assigned_names(element, out)


def _module_names(tree):
    """Names the module body binds, without importing anything."""
    import ast

    bound = set()
    star_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    star_import = True
                else:
                    bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                _assigned_names(target, bound)
        elif isinstance(node, ast.AnnAssign):
            _assigned_names(node.target, bound)
    return bound, star_import


def _dunder_all(tree):
    import ast

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return []
        return [
            e.value for e in node.value.elts if isinstance(e, ast.Constant)
        ]
    return []


def test_every_dunder_all_entry_is_defined():
    """`__all__` is a runtime contract: a star import resolves every entry.

    Checked without importing, so modules that need heavy optional
    dependencies are covered too. A package whose `__init__` uses a star
    import is skipped, because its names cannot be known statically.
    """
    import ast
    from pathlib import Path

    import camel

    root = Path(camel.__file__).parent
    offenders = []
    for init in sorted(root.rglob("__init__.py")):
        tree = ast.parse(init.read_text(encoding="utf-8"))
        advertised = _dunder_all(tree)
        if not advertised:
            continue
        bound, star_import = _module_names(tree)
        if star_import:
            continue
        missing = [n for n in advertised if n not in bound]
        if missing:
            rel = init.relative_to(root.parent)
            offenders.append(f"{rel}: {missing}")

    assert offenders == [], (
        "`__all__` advertises names the module never binds: "
        + "; ".join(offenders)
    )
