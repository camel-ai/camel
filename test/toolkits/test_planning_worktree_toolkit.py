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

import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

import pytest

from camel.toolkits.planning_worktree_toolkit import (
    PlanningWorktreeToolkit,
)

# ── helpers ──────────────────────────────────────────────────────────


def _init_git_repo(path: Path) -> None:
    """Create a minimal git repo with one commit at *path*."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )


# ── plan-mode tests ─────────────────────────────────────────────────


def test_plan_mode_round_trip():
    """Enter → write plan → exit: plan content is returned correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        toolkit = PlanningWorktreeToolkit(working_directory=temp_dir)
        entered = toolkit.planning_enter_plan_mode()

        plan_file = Path(entered["plan_file_path"])
        plan_file.write_text("# Plan\n\n- Step 1\n", encoding="utf-8")
        exited = toolkit.planning_exit_plan_mode(
            allowed_prompts=[{"tool": "Bash", "prompt": "run tests"}]
        )

        assert entered["plan_mode"] is True
        assert exited["plan_mode"] is False
        assert "Step 1" in exited["plan_content"]
        assert exited["allowed_prompts"][0]["tool"] == "Bash"


def test_exit_plan_mode_without_enter_returns_error():
    """Exiting plan mode before entering it must return an error."""
    toolkit = PlanningWorktreeToolkit()
    result = toolkit.planning_exit_plan_mode()
    assert "error" in result


# ── worktree tests ───────────────────────────────────────────────────


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_worktree_create_and_remove_lifecycle():
    """Create a worktree, verify it exists, remove it, verify cleanup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir) / "repo"
        _init_git_repo(repo)

        toolkit = PlanningWorktreeToolkit(working_directory=str(repo))
        enter_result = toolkit.worktree_enter_worktree("feature-search")

        assert enter_result["branch"].startswith("camel/feature-search")
        worktree_path = Path(enter_result["worktree_path"])
        assert worktree_path.exists()
        assert toolkit.working_directory == worktree_path

        remove_result = toolkit.worktree_remove_worktree()
        assert "error" not in remove_result
        assert remove_result["removed_worktree"] == str(worktree_path)
        assert toolkit.current_worktree_path is None
        assert toolkit.working_directory == repo.resolve()
        assert not worktree_path.exists()


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_worktree_name_collision_increments_suffix():
    """When a branch/dir already exists, the suffix should increment."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir) / "repo"
        _init_git_repo(repo)

        toolkit = PlanningWorktreeToolkit(working_directory=str(repo))
        r1 = toolkit.worktree_enter_worktree("dup")
        assert r1["branch"] == "camel/dup"

        # Reset toolkit state so we can create another worktree
        toolkit.current_worktree_path = None
        toolkit.working_directory = repo.resolve()

        r2 = toolkit.worktree_enter_worktree("dup")
        assert r2["branch"] == "camel/dup-1"

        # Cleanup both worktrees
        subprocess.run(
            ["git", "worktree", "remove", "--force", r1["worktree_path"]],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "remove", "--force", r2["worktree_path"]],
            cwd=repo,
            capture_output=True,
        )


def test_remove_worktree_without_enter_returns_error():
    """Removing a worktree when none is active must return an error."""
    toolkit = PlanningWorktreeToolkit()
    result = toolkit.worktree_remove_worktree()
    assert "error" in result


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_worktree_in_non_git_directory_returns_error():
    """Attempting to create a worktree outside a git repo must fail."""
    with tempfile.TemporaryDirectory() as temp_dir:
        toolkit = PlanningWorktreeToolkit(working_directory=temp_dir)
        result = toolkit.worktree_enter_worktree("should-fail")
        assert "error" in result


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_worktree_reentry_returns_error():
    """Entering a worktree while already inside one must return an error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir) / "repo"
        _init_git_repo(repo)

        toolkit = PlanningWorktreeToolkit(working_directory=str(repo))
        r1 = toolkit.worktree_enter_worktree("first")
        assert "error" not in r1

        r2 = toolkit.worktree_enter_worktree("second")
        assert "error" in r2

        # Cleanup
        toolkit.worktree_remove_worktree()


def test_worktree_remove_failure_preserves_state(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    worktree = tmp_path / "repo-worktree"
    repo.mkdir()
    worktree.mkdir()

    toolkit = PlanningWorktreeToolkit(working_directory=str(worktree))
    toolkit.current_worktree_path = worktree

    def fake_run_git(*args, cwd=None):
        if args == ("rev-parse", "--show-toplevel"):
            return subprocess.CompletedProcess(args, 0, f"{repo}\n", "")
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return subprocess.CompletedProcess(args, 0, "camel/test\n", "")
        if args == ("worktree", "list", "--porcelain"):
            return subprocess.CompletedProcess(
                args, 0, f"worktree {repo}\nworktree {worktree}\n", ""
            )
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 1, "", "remove failed")
        if args[:2] == ("branch", "-d"):
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(f"unexpected git call: {args} cwd={cwd}")

    monkeypatch.setattr(toolkit, "_run_git", fake_run_git)

    result = toolkit.worktree_remove_worktree()

    assert "error" in result
    assert toolkit.current_worktree_path == worktree
    assert toolkit.working_directory == worktree.resolve()


def test_concurrent_plan_mode_enter_exit():
    """Multiple agents can independently enter and exit plan mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        errors: list = []

        def agent_work(agent_id: int) -> None:
            try:
                # Each agent uses its own plan file to avoid cross-write races
                tk = PlanningWorktreeToolkit(
                    working_directory=temp_dir,
                    plan_file_name=f".camel-plan-{agent_id}.md",
                )
                entered = tk.planning_enter_plan_mode()
                assert entered["plan_mode"] is True

                plan_file = Path(entered["plan_file_path"])
                plan_file.write_text(
                    f"# Plan from agent {agent_id}\n", encoding="utf-8"
                )

                exited = tk.planning_exit_plan_mode()
                assert exited["plan_mode"] is False
                assert exited["plan_content"] == (
                    f"# Plan from agent {agent_id}\n"
                )
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=agent_work, args=(i,)) for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent plan-mode errors: {errors}"
