# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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

from abc import abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import pandas as pd

from benchmarks import BaseBenchmark
from camel.agents import ChatAgent

logger = logging.getLogger(__name__)


class Mode:
    VALID_MODES = {"pass@k", "majority voting"}

    def __init__(self, mode: Literal["pass@k", "majority voting"], k: Optional[int] = None):
        self.mode = mode

        if mode == "pass@k":
            if k is None or k < 1:
                raise ValueError("`k` must be at least 1 for 'pass@k'.")
            self.k = k

        elif mode == "majority voting":
            if k is None or k < 2:
                raise ValueError("`k` must be at least 2 for 'majority voting'.")
            self.k = k

        else:
            raise ValueError(f"Invalid mode '{mode}'. Supported modes: {self.VALID_MODES}")

    def __repr__(self) -> str:
        return f"Mode(mode={self.mode}, k={self.k})"


class MathBenchmark(BaseBenchmark):
    r"""Benchmark class for evaluating mathematical problem-solving capabilities."""

    def __init__(
        self, name: str, data_dir: str, save_to: str, processes: int = 1
    ):
        """Initialize the benchmark."""
        super().__init__(name, data_dir, save_to, processes)

    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        randomize: bool = False,
        subset: Optional[int] = None,
        mode: Mode = Mode("pass@k", 1),
        *args,
        **kwargs,
    ) -> "MathBenchmark":
        """Runs the benchmark, evaluates answers, and saves results as JSON."""

        logger.info(f"Running {mode.mode} evaluation on {on} set with k={mode.k}")

        # Load the dataset
        dataset = getattr(self, on)
        if subset:
            dataset = dataset[:subset]

        # Generate solutions for each question in the dataset
        results = self._generate_solutions(agent, dataset, randomize, *args, **kwargs)

        # Ensure the results are in the expected format
        if isinstance(results, dict):
            results = pd.DataFrame(results)

        if not isinstance(results, pd.DataFrame):
            raise TypeError("Expected results as a pandas DataFrame or dictionary.")

        if "answers" not in results.columns or "solution" not in results.columns:
            raise ValueError("Results must contain 'answers' and 'solution' columns.")

        # Process answers based on mode
        results["correct"] = results.apply(lambda row: self._evaluate(row, mode), axis=1)

        # Save results as JSON
        save_path = Path(self.save_to) / f"{self.name}_results.json"
        results.to_json(save_path, orient="records", indent=2)

        logger.info(f"Results saved to {save_path}")

        self._results = results.to_dict(orient="records")

        return self

    def _evaluate(self, row: pd.Series, mode: Mode) -> bool:
        """Evaluate model predictions based on the chosen evaluation mode."""
        answers = row["answers"]
        solution = row["solution"]

        if not isinstance(answers, list):
            raise ValueError(f"Expected 'answers' to be a list, but got {type(answers)}")

        match mode.mode:
            case "pass@k":
                return any(ans == solution for ans in answers[: mode.k])

            case "majority voting":
                most_common = max(set(answers), key=answers.count)
                return most_common == solution

        return False

    @abstractmethod
    def _generate_solutions(
        self,
        agent: ChatAgent,
        dataset: List[Dict[str, Any]],
        randomize: bool,
        *args,
        **kwargs,
    ) -> Union[pd.DataFrame, Dict[str, List[Any]]]:
        """
        Method to be implemented by subclasses.

        This method should return a pandas DataFrame or a dictionary with:
        - "answers": List of generated answers for each problem.
        - "solution": The correct solution.
        """
        pass