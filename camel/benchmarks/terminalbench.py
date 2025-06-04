# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import os
import random
import shutil
from typing import Any, Dict, List, Optional

import yaml
from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.interpreters.subprocess_interpreter import SubprocessInterpreter
from camel.logger import get_logger
from camel.utils import download_github_subdirectory

logger = get_logger(__name__)


class TerminalBenchBenchmark(BaseBenchmark):
    r"""Benchmark for evaluating AI agents on Terminal-Bench tasks."""

    REPO_URL = "https://github.com/Terminal-Bench/terminal-bench-core.git"

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        processes: int = 1,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        require_confirm: bool = False,
        force_download: bool = False,
    ) -> None:
        super().__init__("terminalbench", data_dir, save_to, processes)
        self.category = category
        self.difficulty = difficulty
        self.require_confirm = require_confirm
        self.force_download = force_download
        self.interpreter = SubprocessInterpreter(
            require_confirm=require_confirm
        )
        self.tasks: List[str] = []

    def download(self) -> "TerminalBenchBenchmark":
        # Only skip clone if tasks directory already present and not forcing download
        tasks_dir = os.path.join(self.data_dir, "tasks")
        if os.path.isdir(tasks_dir) and not self.force_download:
            logger.info("Terminal-Bench dataset already exists.")
            return self
        # Remove any existing incomplete or old dataset
        if os.path.exists(self.data_dir):
            logger.info(
                f"Removing existing incomplete dataset at {self.data_dir}"
            )
            shutil.rmtree(self.data_dir)
        cmd = f"git clone --depth 1 {self.REPO_URL} {self.data_dir}"
        logger.info(f"Cloning Terminal-Bench dataset from {self.REPO_URL} ...")
        output = self.interpreter.run(cmd, code_type="bash")
        logger.info(output)
        # Fallback: ensure tasks metadata if clone failed
        if not os.path.isdir(tasks_dir):
            logger.warning(
                "Tasks directory missing after clone; fetching via GitHub subdirectory..."
            )
            download_github_subdirectory(
                "Terminal-Bench/terminal-bench-core",
                "tasks",
                tasks_dir,
            )
        return self

    def load(self, force_download: bool = False) -> "TerminalBenchBenchmark":
        if force_download:
            self.download()
        tasks_dir = os.path.join(self.data_dir, "tasks")
        if not os.path.isdir(tasks_dir):
            raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")
        self.tasks = []
        for name in os.listdir(tasks_dir):
            path = os.path.join(tasks_dir, name, "task.yaml")
            if not os.path.isfile(path):
                continue
            info = yaml.safe_load(open(path))
            if self.category and self.category not in info.get("tags", []):
                continue
            if self.difficulty and info.get("difficulty") != self.difficulty:
                continue
            self.tasks.append(name)
        logger.info(f"Loaded {len(self.tasks)} tasks.")
        return self

    def run(
        self,
        agent: ChatAgent,
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:  # type: ignore[override]
        self.download()
        self.load(force_download=self.force_download)
        task_list = list(self.tasks)
        if randomize:
            random.shuffle(task_list)
        if subset:
            task_list = task_list[:subset]
        self._results = []
        with open(self.save_to, "w") as f:
            for task_id in tqdm(task_list, desc="TerminalBench"):
                result = self._run_task(task_id)
                self._results.append(result)
                f.write(json.dumps(result) + "\n")
                f.flush()
        total = len(self._results)
        success = sum(r["success"] for r in self._results)
        metrics = {
            "total": total,
            "success": success,
            "failure": total - success,
            "success_rate": success / total if total else 0,
        }
        return metrics

    def _run_task(self, task_id: str) -> Dict[str, Any]:
        cmd = (
            f"tb run "
            f"--dataset-name terminal-bench-core "
            f"--dataset-version 0.1.0 "
            f"--agent-import-path camel.agents.chat_agent:ChatAgent "
            f"--task-id {task_id}"
        )
        logger.info(f"Running task: {task_id}")
        output = self.interpreter.run(cmd, code_type="bash")
        success = "SUCCESS" in output
        logger.info(f"Task {task_id}: {'PASS' if success else 'FAIL'}")
        return {"task_id": task_id, "success": success, "output": output}

    def report(self, results: Any = None) -> None:
        total = len(self._results)
        success = sum(r["success"] for r in self._results)
        logger.info(
            f"TerminalBench: {success}/{total} passed ({success/total:.1%})"
        )
