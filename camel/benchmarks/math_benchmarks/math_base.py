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

from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.logger import get_logger

logger = get_logger(__name__)


class Mode:
    r"""
    Defines different evaluation modes for benchmarking.

    Attributes:
        VALID_MODES (set): Supported evaluation modes.
        mode (Literal["pass@k", "majority voting"]): Selected evaluation mode.
        k (Optional[int]): Parameter defining attempts or votes required.
    """

    VALID_MODES: ClassVar[set[str]] = {"pass@k", "majority voting"}

    def __init__(
        self,
        mode: Literal["pass@k", "majority voting"],
        k: Optional[int] = None,
    ):
        r"""
        Initializes a Mode object.

        Args:
            mode (Literal["pass@k", "majority voting"]): The evaluation mode.
            k (Optional[int]): Number of attempts (for "pass@k") or votes
                (for "majority voting").

        Raises:
            ValueError: If `k` is not valid for the selected mode.
        """
        self.mode = mode

        if mode == "pass@k":
            if k is None or k < 1:
                raise ValueError("`k` must be at least 1 for 'pass@k'.")
            self.k = k

        elif mode == "majority voting":
            if k is None or k < 2:
                raise ValueError(
                    "`k` must be at least 2 for 'majority voting'."
                )
            self.k = k

        else:
            raise ValueError(
                f"Invalid mode '{mode}'. Supported modes: {self.VALID_MODES}"
            )

    def __repr__(self) -> str:
        r"""Returns a string representation of the Mode instance."""
        return f"Mode(mode={self.mode}, k={self.k})"


class MathBenchmark(BaseBenchmark):
    import numpy as np
    import pandas as pd

    r"""
    Benchmark class for evaluating mathematical problem-solving capabilities.

    Inherits from:
        BaseBenchmark
    """

    def __init__(
        self, name: str, data_dir: str, save_to: str, processes: int = 1
    ):
        r"""
        Initializes the MathBenchmark class.

        Args:
            name (str): Name of the benchmark.
            data_dir (str): Directory containing the dataset.
            save_to (str): Path to save the benchmark results.
            processes (int, optional): Number of parallel processes.
                Defaults to 1.
        """
        super().__init__(name, data_dir, save_to, processes)

    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        randomize: bool = False,
        subset: Optional[int] = None,
        mode: Optional[Mode] = None,
        *args,
        **kwargs,
    ) -> "MathBenchmark":
        r"""
        Runs the benchmark, evaluates answers, and saves results as JSON.

        Args:
            agent (ChatAgent): The agent used to generate answers.
            on (Literal["train", "valid", "test"]): The dataset split to use.
            randomize (bool, optional): Whether to randomize dataset order.
                Defaults to False.
            subset (Optional[int], optional): Number of problems to process.
                Defaults to None (all).
            mode (Mode, optional): The evaluation mode. Defaults to
                Mode("pass@k", 1).

        Returns:
            MathBenchmark: The benchmark instance with results.

        Raises:
            ValueError: If an invalid dataset split is specified.
            TypeError: If the results are not in the expected format.
        """

        if mode is None:
            mode = Mode("pass@k", 1)

        logger.info(
            f"Running {mode.mode} evaluation on {on} set with k={mode.k}"
        )

        if on not in ["train", "test", "valid"]:
            raise ValueError(
                f"Invalid dataset split '{on}'. Use 'train', 'valid' (empty), "
                f"or 'test'."
            )

        if not self._data:
            self.load()

        dataset = self._prepare_dataset(self._data[on])

        # TODO: Fix Seed for reproducibility
        if randomize:
            import random

            random.shuffle(dataset)

        if subset:
            dataset = dataset[:subset]

        # Generate solutions for each question in the dataset
        results = self._generate_solutions(
            agent, dataset, mode, *args, **kwargs
        )

        # Ensure the results are in the expected format
        if isinstance(results, dict):
            results = self.pd.DataFrame(results)

        if not isinstance(results, self.pd.DataFrame):
            raise TypeError(
                "Expected results as a pandas DataFrame or dictionary."
            )

        if (
            "answers" not in results.columns
            or "solution" not in results.columns
        ):
            raise ValueError(
                "Results must contain 'answers' and 'solution' columns."
            )

        # Process answers based on mode
        results["correct"] = results.apply(
            lambda row: self._evaluate(row, mode), axis=1
        )

        # Save results as JSON
        save_dir = Path(self.save_to)
        save_dir.mkdir(parents=True, exist_ok=True)

        save_path = Path(self.save_to) / f"{self.name}_results.json"
        results.to_json(save_path, orient="records", indent=2)

        logger.info(f"Results saved to {save_path}")

        self._results = results.to_dict(orient="records")

        return self

    def _evaluate(self, row: pd.Series, mode: Mode) -> bool:
        r"""
        Evaluate model predictions based on the chosen evaluation mode.
        """
        answers = row["answers"]
        solution = row["solution"]

        if not isinstance(answers, list):
            raise ValueError(
                f"Expected 'answers' to be a list, but got {type(answers)}"
            )

        if mode.mode == "pass@k":
            return bool(self.np.any(self.np.array(answers[: mode.k]) == solution))

        elif mode.mode == "majority voting":
            most_common = self.pd.Series(answers).mode().iloc[0]
            return most_common == solution

        return False  # Default case

    @abstractmethod
    def _prepare_dataset(self, dataset: List[Dict[str, Any]]) -> pd.DataFrame:
        r"""
        Method to further prepare the dataset, like renaming or normalizing
        columns.
        """
        pass

    @abstractmethod
    def _generate_solutions(
        self,
        agent: ChatAgent,
        dataset: pd.DataFrame,
        mode: Mode,
        *args,
        **kwargs,
    ) -> Union[pd.DataFrame, Dict[str, List[Any]]]:
        r"""
        Method to be implemented by subclasses.

        This method should return a pandas DataFrame or a dictionary with:
        - "answers": List of generated answers for each problem.
        - "solution": The correct solution.
        """
        pass
