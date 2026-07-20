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

import importlib
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

SKILL_CREATOR_DIR = (
    Path(__file__).resolve().parents[2] / ".camel" / "skills" / "skill-creator"
)
sys.path.insert(0, str(SKILL_CREATOR_DIR))
improve_description = importlib.import_module("scripts.improve_description")
package_skill = importlib.import_module("scripts.package_skill")
quick_validate = importlib.import_module("scripts.quick_validate")
run_eval = importlib.import_module("scripts.run_eval")
run_loop = importlib.import_module("scripts.run_loop")
utils = importlib.import_module("scripts.utils")


EXPECTED_BUNDLE_FILES = {
    "LICENSE.txt",
    "SKILL.md",
    "agents/analyzer.md",
    "agents/comparator.md",
    "agents/grader.md",
    "assets/eval_review.html",
    "eval-viewer/generate_review.py",
    "eval-viewer/viewer.html",
    "references/schemas.md",
    "scripts/__init__.py",
    "scripts/aggregate_benchmark.py",
    "scripts/generate_report.py",
    "scripts/improve_description.py",
    "scripts/package_skill.py",
    "scripts/quick_validate.py",
    "scripts/run_eval.py",
    "scripts/run_loop.py",
    "scripts/utils.py",
}


def test_skill_creator_validator_accepts_shipped_bundle():
    r"""Test the vendored bundle passes its upstream validator."""
    valid, message = quick_validate.validate_skill(SKILL_CREATOR_DIR)

    assert valid
    assert message == "Skill is valid!"


def test_skill_creator_package_contains_expected_bundle(tmp_path):
    r"""Test the package archive contains every shipped resource once."""
    archive_path = package_skill.package_skill(SKILL_CREATOR_DIR, tmp_path)

    assert archive_path == tmp_path / "skill-creator.skill"
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {
            f"skill-creator/{path}" for path in EXPECTED_BUNDLE_FILES
        }


def test_skill_creator_package_excludes_local_artifacts(tmp_path):
    r"""Test packaging excludes local artifacts and retains skill content."""
    skill_path = tmp_path / "valid-skill"
    skill_path.mkdir()
    (skill_path / "SKILL.md").write_text(
        "---\nname: valid-skill\ndescription: A valid test skill.\n---\n"
    )

    included_paths = {
        "references/guide.md": "Guide",
        "nested/evals/keep.md": "Nested eval resource",
    }
    excluded_paths = {
        ".DS_Store": "",
        ".git/config": "config",
        ".gitignore": "ignored",
        ".gitattributes": "attributes",
        ".env": "SECRET=value",
        "__pycache__/module.pyc": "bytecode",
        "module.pyo": "bytecode",
        "module.pyd": "binary",
        "module.so": "binary",
        "package.egg-info/PKG-INFO": "metadata",
        ".eggs/package/info": "metadata",
        ".pytest_cache/state": "cache",
        ".mypy_cache/state": "cache",
        ".ruff_cache/state": "cache",
        ".coverage": "coverage",
        ".venv/bin/python": "environment",
        "venv/bin/python": "environment",
        ".idea/workspace.xml": "IDE settings",
        ".vscode/settings.json": "IDE settings",
        "node_modules/package/index.js": "dependency",
        ".tox/py/test": "environment",
        "dist/archive.txt": "build output",
        "build/output.txt": "build output",
        "debug.log": "log",
        "evals/result.json": "root eval result",
    }
    for relative_path, content in (
        included_paths.items() | excluded_paths.items()
    ):
        path = skill_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    archive_path = package_skill.package_skill(skill_path, tmp_path)

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert {
        f"valid-skill/{relative_path}" for relative_path in included_paths
    } <= names
    assert (
        not {
            f"valid-skill/{relative_path}" for relative_path in excluded_paths
        }
        & names
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "", "Name cannot be empty"),
        ("name", "   ", "Name cannot be empty"),
        ("description", "", "Description cannot be empty"),
        ("description", "   ", "Description cannot be empty"),
    ],
)
def test_skill_creator_validator_rejects_empty_required_fields(
    tmp_path,
    field,
    value,
    message,
):
    r"""Test required frontmatter fields cannot be empty or whitespace."""
    values = {"name": "valid-skill", "description": "A valid test skill."}
    values[field] = value
    (tmp_path / "SKILL.md").write_text(
        "---\n"
        f"name: {values['name']!r}\n"
        f"description: {values['description']!r}\n"
        "---\n"
    )

    valid, result = quick_validate.validate_skill(tmp_path)

    assert not valid
    assert result == message


def test_run_single_query_requires_claude_cli_before_writing_files(
    monkeypatch,
    tmp_path,
):
    r"""Test a missing CLI fails before the evaluation creates resources."""
    monkeypatch.setattr(utils.shutil, "which", lambda _: None)

    with pytest.raises(RuntimeError, match="Claude CLI was not found on PATH"):
        run_eval.run_single_query(
            query="Create a skill",
            skill_name="skill-creator",
            skill_description="Create skills",
            timeout=1,
            project_root=str(tmp_path),
        )

    assert not (tmp_path / ".claude").exists()


def test_run_eval_requires_claude_cli_before_starting_workers(
    monkeypatch,
    tmp_path,
):
    r"""Test a missing CLI fails before the evaluation starts workers."""
    monkeypatch.setattr(utils.shutil, "which", lambda _: None)

    with pytest.raises(RuntimeError, match="Claude CLI was not found on PATH"):
        run_eval.run_eval(
            eval_set=[],
            skill_name="skill-creator",
            description="Create skills",
            num_workers=1,
            timeout=1,
            project_root=tmp_path,
        )


def test_run_loop_requires_claude_cli_before_creating_resources(
    monkeypatch,
    tmp_path,
):
    r"""Test a missing CLI fails before the loop creates any resources."""
    eval_set_path = tmp_path / "eval-set.json"
    eval_set_path.write_text("[]")
    report_path = tmp_path / "report.html"
    results_dir = tmp_path / "results"

    monkeypatch.setattr(utils.shutil, "which", lambda _: None)
    browser_open = MagicMock()
    loop_runner = MagicMock()
    process_pool = MagicMock()
    popen = MagicMock()
    subprocess_run = MagicMock()
    monkeypatch.setattr(run_loop.webbrowser, "open", browser_open)
    monkeypatch.setattr(run_loop, "run_loop", loop_runner)
    monkeypatch.setattr(run_eval, "ProcessPoolExecutor", process_pool)
    monkeypatch.setattr(run_eval.subprocess, "Popen", popen)
    monkeypatch.setattr(improve_description.subprocess, "run", subprocess_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_loop.py",
            "--eval-set",
            str(eval_set_path),
            "--skill-path",
            str(SKILL_CREATOR_DIR),
            "--model",
            "claude-sonnet",
            "--report",
            str(report_path),
            "--results-dir",
            str(results_dir),
        ],
    )

    with pytest.raises(RuntimeError, match="Claude CLI was not found on PATH"):
        run_loop.main()

    assert not report_path.exists()
    assert not results_dir.exists()
    browser_open.assert_not_called()
    loop_runner.assert_not_called()
    process_pool.assert_not_called()
    popen.assert_not_called()
    subprocess_run.assert_not_called()


def test_improve_description_requires_claude_cli(monkeypatch):
    r"""Test a missing CLI fails before starting the optimizer process."""
    monkeypatch.setattr(utils.shutil, "which", lambda _: None)
    subprocess_run = MagicMock()
    monkeypatch.setattr(improve_description.subprocess, "run", subprocess_run)

    with pytest.raises(RuntimeError, match="Claude CLI was not found on PATH"):
        improve_description._call_claude("Improve this description.", None)

    subprocess_run.assert_not_called()


def test_improve_description_uses_claude_cli_when_available(monkeypatch):
    r"""Test the compatibility check preserves the upstream CLI command."""
    monkeypatch.setattr(utils.shutil, "which", lambda _: "/usr/bin/claude")
    subprocess_run = MagicMock(
        return_value=SimpleNamespace(
            returncode=0,
            stdout="Improved description",
            stderr="",
        )
    )
    monkeypatch.setattr(improve_description.subprocess, "run", subprocess_run)

    response = improve_description._call_claude(
        "Improve this description.",
        "claude-sonnet",
        timeout=42,
    )

    assert response == "Improved description"
    (command,) = subprocess_run.call_args.args
    kwargs = subprocess_run.call_args.kwargs
    assert command == [
        "claude",
        "-p",
        "--output-format",
        "text",
        "--model",
        "claude-sonnet",
    ]
    assert kwargs["input"] == "Improve this description."
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert "CLAUDECODE" not in kwargs["env"]
    assert kwargs["timeout"] == 42
