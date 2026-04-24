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

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class PlanningWorktreeToolkit(BaseToolkit):
    r"""Toolkit for plan-mode state and git worktree management.

    Each toolkit instance owns an independent plan file determined by
    *working_directory* and *plan_file_name*.  A class-level lock registry
    ensures that concurrent agents sharing the same plan file do not
    corrupt each other's writes.

    Args:
        working_directory (Optional[str]): The directory to use as the
            working root. Falls back to the ``CAMEL_WORKDIR`` environment
            variable, then the current working directory.
            (default: :obj:`None`)
        timeout (Optional[float]): The timeout for the toolkit.
            (default: :obj:`None`)
        plan_file_name (str): Name of the Markdown plan file created inside
            *working_directory*. (default: :obj:`".camel-plan.md"`)
        switch_process_cwd (bool): If :obj:`True`, ``os.chdir`` will be
            called when entering/leaving a worktree so the whole process
            sees the new directory. (default: :obj:`False`)
    """

    _plan_locks: ClassVar[Dict[str, threading.Lock]] = {}
    _plan_locks_guard = threading.Lock()

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        plan_file_name: str = ".camel-plan.md",
        switch_process_cwd: bool = False,
    ) -> None:
        super().__init__(timeout=timeout)
        if working_directory is not None:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir).resolve()
            else:
                self.working_directory = Path.cwd().resolve()
        self.plan_file_name = plan_file_name
        self.switch_process_cwd = switch_process_cwd
        self.plan_mode_active = False
        self.current_worktree_path: Optional[Path] = None

    def _plan_file_path(self) -> Path:
        return self.working_directory / self.plan_file_name

    def _plan_lock(self) -> threading.Lock:
        key = str(self._plan_file_path())
        with PlanningWorktreeToolkit._plan_locks_guard:
            if key not in PlanningWorktreeToolkit._plan_locks:
                PlanningWorktreeToolkit._plan_locks[key] = threading.Lock()
            return PlanningWorktreeToolkit._plan_locks[key]

    def _error_result(self, message: str, **payload: Any) -> Dict[str, Any]:
        logger.warning(message)
        result: Dict[str, Any] = {"error": f"Error: {message}"}
        result.update(payload)
        return result

    def _run_git(
        self,
        *args: str,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.working_directory,
            capture_output=True,
            text=True,
            check=False,
        )

    def planning_enter_plan_mode(self) -> Dict[str, Any]:
        r"""Mark the toolkit as being in plan mode.

        Returns:
            Dict[str, Any]: Plan mode status and plan file location.
        """
        with self._plan_lock():
            plan_file = self._plan_file_path()
            try:
                if not plan_file.exists():
                    plan_file.write_text(
                        "# Plan\n\n- Objective:\n- Constraints:\n- Steps:\n",
                        encoding="utf-8",
                    )
            except OSError as exc:
                self.plan_mode_active = False
                return self._error_result(
                    f"Failed to initialize plan file '{plan_file}': {exc}",
                    plan_mode=False,
                    plan_file_path=str(plan_file),
                    working_directory=str(self.working_directory),
                )
            self.plan_mode_active = True
            return {
                "plan_mode": True,
                "plan_file_path": str(plan_file),
                "working_directory": str(self.working_directory),
            }

    def planning_exit_plan_mode(
        self,
        allowed_prompts: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        r"""Exit plan mode and return the current plan for approval.

        Args:
            allowed_prompts (Optional[List[Dict[str, str]]]): Optional list of
                tool/prompt pairs that are allowed after plan approval.

        Returns:
            Dict[str, Any]: Current plan content together with the supplied
                allowed prompts.
        """
        with self._plan_lock():
            if not self.plan_mode_active:
                return self._error_result(
                    "Plan mode is not active.",
                    plan_mode=False,
                    plan_file_path=str(self._plan_file_path()),
                    allowed_prompts=allowed_prompts or [],
                )

            plan_file = self._plan_file_path()
            try:
                plan_content = (
                    plan_file.read_text(encoding="utf-8")
                    if plan_file.exists()
                    else ""
                )
            except OSError as exc:
                self.plan_mode_active = False
                return self._error_result(
                    f"Failed to read plan file '{plan_file}': {exc}",
                    plan_mode=False,
                    plan_file_path=str(plan_file),
                    allowed_prompts=allowed_prompts or [],
                )
            self.plan_mode_active = False
            return {
                "plan_mode": False,
                "plan_file_path": str(plan_file),
                "plan_content": plan_content,
                "allowed_prompts": allowed_prompts or [],
            }

    def worktree_enter_worktree(
        self,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Create and switch this toolkit to a dedicated git worktree.

        Args:
            name (Optional[str]): Optional worktree name seed.

        Returns:
            Dict[str, Any]: Created branch name, worktree path, and active
                working directory.
        """
        if self.current_worktree_path is not None:
            return self._error_result(
                "Already inside a worktree. Call "
                "worktree_remove_worktree() first.",
                working_directory=str(self.working_directory),
                current_worktree=str(self.current_worktree_path),
            )

        try:
            repo_root_result = self._run_git(
                "rev-parse",
                "--show-toplevel",
                cwd=self.working_directory,
            )
            if repo_root_result.returncode != 0:
                return self._error_result(
                    repo_root_result.stderr.strip()
                    or repo_root_result.stdout.strip()
                    or "Failed to determine the git repository root.",
                    working_directory=str(self.working_directory),
                )
            repo_root = Path(repo_root_result.stdout.strip()).resolve()

            safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name or "").strip("-")
            if not safe_name:
                safe_name = f"session-{time.strftime('%Y%m%d-%H%M%S')}"

            worktree_base = repo_root.parent / f".{repo_root.name}_worktrees"
            worktree_base.mkdir(parents=True, exist_ok=True)

            max_suffix = 100
            suffix = 0
            while suffix <= max_suffix:
                candidate_name = (
                    safe_name if suffix == 0 else f"{safe_name}-{suffix}"
                )
                branch_name = f"camel/{candidate_name}"
                worktree_path = worktree_base / candidate_name
                branch_exists = (
                    self._run_git(
                        "show-ref",
                        "--verify",
                        "--quiet",
                        f"refs/heads/{branch_name}",
                        cwd=repo_root,
                    ).returncode
                    == 0
                )
                if not branch_exists and not worktree_path.exists():
                    break
                suffix += 1
            else:
                return self._error_result(
                    f"Too many worktree name collisions for '{safe_name}'.",
                    working_directory=str(self.working_directory),
                )

            add_result = self._run_git(
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                "HEAD",
                cwd=repo_root,
            )
            if add_result.returncode != 0:
                return self._error_result(
                    add_result.stderr.strip()
                    or add_result.stdout.strip()
                    or "Failed to create git worktree.",
                    working_directory=str(self.working_directory),
                )

            self.current_worktree_path = worktree_path.resolve()
            self.working_directory = self.current_worktree_path
            if self.switch_process_cwd:
                os.chdir(self.current_worktree_path)

            return {
                "branch": branch_name,
                "worktree_path": str(self.current_worktree_path),
                "working_directory": str(self.working_directory),
                "process_cwd_switched": self.switch_process_cwd,
            }
        except Exception as exc:
            return self._error_result(
                f"Failed to create worktree: {exc}",
                working_directory=str(self.working_directory),
            )

    def worktree_remove_worktree(self) -> Dict[str, Any]:
        r"""Remove the current worktree and its branch, restoring the
        original working directory.

        Returns:
            Dict[str, Any]: Removal status and restored working directory.
        """
        if self.current_worktree_path is None:
            return self._error_result(
                "No active worktree to remove.",
                working_directory=str(self.working_directory),
            )

        worktree_path = self.current_worktree_path
        try:
            repo_root_result = self._run_git(
                "rev-parse",
                "--show-toplevel",
                cwd=worktree_path,
            )
            if repo_root_result.returncode != 0:
                return self._error_result(
                    repo_root_result.stderr.strip()
                    or "Failed to determine repository root from worktree.",
                    working_directory=str(self.working_directory),
                )

            branch_result = self._run_git(
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
                cwd=worktree_path,
            )
            branch_name = branch_result.stdout.strip()

            main_repo_result = self._run_git(
                "worktree",
                "list",
                "--porcelain",
                cwd=worktree_path,
            )
            # The first "worktree ..." entry is always the main repo.
            main_repo_path: Optional[Path] = None
            for line in main_repo_result.stdout.splitlines():
                if line.startswith("worktree "):
                    main_repo_path = Path(line.split(" ", 1)[1]).resolve()
                    break

            if main_repo_path is None:
                return self._error_result(
                    "Could not determine the main repository path.",
                    working_directory=str(self.working_directory),
                )

            remove_result = self._run_git(
                "worktree",
                "remove",
                str(worktree_path),
                "--force",
                cwd=main_repo_path,
            )
            if remove_result.returncode != 0:
                return self._error_result(
                    remove_result.stderr.strip()
                    or "Failed to remove worktree.",
                    working_directory=str(self.working_directory),
                )

            self.working_directory = main_repo_path
            self.current_worktree_path = None
            if self.switch_process_cwd:
                os.chdir(main_repo_path)

            if branch_name:
                branch_delete_result = self._run_git(
                    "branch",
                    "-d",
                    branch_name,
                    cwd=main_repo_path,
                )
                if branch_delete_result.returncode != 0:
                    return self._error_result(
                        branch_delete_result.stderr.strip()
                        or branch_delete_result.stdout.strip()
                        or f"Failed to delete branch '{branch_name}'.",
                        removed_worktree=str(worktree_path),
                        remaining_branch=branch_name,
                        working_directory=str(self.working_directory),
                    )

            return {
                "removed_worktree": str(worktree_path),
                "removed_branch": branch_name,
                "working_directory": str(self.working_directory),
            }
        except Exception as exc:
            return self._error_result(
                f"Failed to remove worktree: {exc}",
                working_directory=str(self.working_directory),
            )

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.planning_enter_plan_mode),
            FunctionTool(self.planning_exit_plan_mode),
            FunctionTool(self.worktree_enter_worktree),
            FunctionTool(self.worktree_remove_worktree),
        ]
