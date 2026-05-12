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

import logging
import os
import random
import re
import string
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks._utils import save_to_jsonl
from camel.benchmarks.base import BaseBenchmark
from camel.messages import BaseMessage
from camel.retrievers.auto_retriever import AutoRetriever

logger = logging.getLogger(__name__)


class RetrieverProtocol(Protocol):
    r"""Protocol for the retriever class. Any retriever class implementing
    this protocol can be used in the benchmark class.
    """

    def retrieve(
        self, query: str, contents: List[str], **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Retrieve the relevant content for the query.

        Args:
            query (str): The query to retrieve the content for.
            contents (List[str]): The list of contents to search in.
            **kwargs (Dict[str, Any]): Additional keyword arguments.

        Returns:
            Dict[str, Any]: The relevant content for the query.
        """
        ...

    def reset(self, **kwargs) -> bool:
        r"""Reset the retriever.
        Some benchmarks may require resetting the retriever
        after each query.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            bool: True if the reset was successful, False otherwise.
        """
        ...


class DefaultGAIARetriever(AutoRetriever):
    r"""Default retriever for the GAIA benchmark.
    This retriever uses AutoRetriever in camel to retrieve the content based on
    the query.
    """

    def retrieve(
        self, query: str, contents: List[str], **kwargs: Any
    ) -> Dict[str, Any]:
        r"""Retrieve the content based on the query.

        Args:
            query (str): The query to search for.
            contents (List[str]): The list of contents to search from.
            **kwargs (Any): The keyword arguments to pass to the
                retriever.

        Returns:
            Dict[str, Any]: The retrieved content.
        """
        return self.run_vector_retriever(query, contents, **kwargs)  # type: ignore[arg-type]

    def reset(self, **kwargs: Any) -> bool:
        r"""Reset the retriever.

        Args:
            **kwargs (Any): The keyword arguments to pass to the
                retriever.

        Returns:
            bool: Whether the reset was successful.
        """
        path = Path(self.vector_storage_local_path or os.getcwd())
        task_id = str(kwargs.get("task_id", uuid.uuid4()))
        retriever_dir = path / task_id
        if not retriever_dir.exists():
            try:
                retriever_dir.mkdir(parents=True)
            except Exception as e:
                logger.error(
                    "Error in creating directory: " + f"{retriever_dir}: {e!s}"
                )
                return False
        self.vector_storage_local_path = str(retriever_dir)
        return True


class GAIABenchmark(BaseBenchmark):
    r"""GAIA Benchmark adapted from `"GAIA: a benchmark for General AI
    Assistants"
    <https://huggingface.co/datasets/gaia-benchmark/GAIA>`.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        save_to: Optional[str] = None,
        processes: int = 1,
    ):
        r"""Initialize the GAIA benchmark.

        Args:
            data_dir (Optional[str]): Path to the data directory.
            save_to (Optional[str]): The file to save the results. If None,
                uses default 'gaia_results.jsonl'. (default: :obj:`None`)
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        self.data_dir = data_dir or str(Path(__file__).parent / "data")
        self.save_to = save_to or "gaia_results.jsonl"
        super().__init__("gaia", self.data_dir, self.save_to, processes)
        self.retriever = DefaultGAIARetriever()

    def download(self) -> None:
        r"""Download the GAIA dataset."""
        from huggingface_hub import snapshot_download

        logger.info("Downloading GAIA dataset from HuggingFace.")

        snapshot_download(
            repo_id="gaia-benchmark/GAIA",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )

    def load(
        self,
        force_download: bool = False,
    ) -> None:
        r"""Load the GAIA dataset.

        Args:
            force_download (bool, optional): Whether to force
                download the data. (default: :obj:`False`)
        """
        import pandas as pd

        if force_download:
            logger.info("Force downloading data.")
            self.download()

        # Define validation and test directories
        valid_dir = Path(self.data_dir) / "2023/validation"
        test_dir = Path(self.data_dir) / "2023/test"

        # Check if directories exist; if not, download the data
        if not valid_dir.is_dir() or not test_dir.is_dir():
            logger.info("Data not found. Downloading data.")
            self.download()

        # Load metadata for both validation and test datasets
        for path, label in zip([valid_dir, test_dir], ["valid", "test"]):
            self._data[label] = []
            metadata_file = path / "metadata.parquet"
            df = pd.read_parquet(metadata_file)
            for _, row in df.iterrows():
                data = row.to_dict()
                if data["task_id"] == "0-0-0-0-0":
                    continue
                # convert level to int (parquet stores as string)
                data["Level"] = int(data["Level"])
                if data["file_name"]:
                    data["file_name"] = path / data["file_name"]
                self._data[label].append(data)

    def run(
        self,
        pipeline_template: ChatAgent,
        randomize: bool = False,
        subset: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            pipeline_template (ChatAgent): The agent to run the benchmark.
            randomize (bool, optional): Whether to randomize the data.
                (default: :obj:`False`)
            subset (Optional[int], optional): The subset of data to run.
                (default: :obj:`None`)
            **kwargs: Additional keyword arguments. Must include:
                - on (Literal["valid", "test"]): The set to run the benchmark.
                - level (Union[int, List[int], Literal["all"]]): The level(s).

        Returns:
            Dict[str, Any]: Dictionary containing:
                - total: Total number of tasks evaluated
                - correct: Number of correct answers
                - results: List of detailed results

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Validate inputs
        on = kwargs.get("on")
        if not on:
            raise ValueError(
                "Missing required parameter 'on'. Must be 'valid' or 'test'."
            )
        if on not in ["valid", "test"]:
            raise ValueError(
                f"Invalid value for `on`: {on}, expected 'valid' or 'test'."
            )

        level = kwargs.get("level", "all")
        levels = (
            [1, 2, 3]
            if level == "all"
            else [level]
            if isinstance(level, int)
            else level
        )
        if not all(
            isinstance(lvl, int) and lvl in [1, 2, 3] for lvl in levels
        ):
            raise ValueError(
                f"Invalid value for `level`: {level}, expected 1, 2, 3 "
                "or 'all'."
            )

        logger.info(f"Running benchmark on {on} set at levels {levels}.")
        tasks = [task for task in self._data[on] if task["Level"] in levels]

        # Shuffle and subset data if necessary
        if randomize:
            random.shuffle(tasks)
        if subset:
            tasks = tasks[:subset]

        logger.info(f"Number of tasks: {len(tasks)}")

        # Clear the results file if it exists
        open(self.save_to, "w").close()

        # Initialize results storage
        self._results = []

        # Process tasks
        for task in tqdm(tasks, desc="Running"):
            if not self._prepare_task(task):
                continue

            try:
                result = pipeline_template.step(self._create_user_message(task))
                self._process_result(pipeline_template, task, result)
            except Exception as e:
                self._handle_error(task, e)
            finally:
                pipeline_template.reset()

        return self._generate_summary()

    def _prepare_task(self, task: Dict[str, Any]) -> bool:
        r"""Prepare the task by validating and enriching its data.

        Args:
            task (Dict[str, Any]): The task to prepare.

        Returns:
            bool: True if the task is ready to process, False otherwise.
        """
        if task["file_name"]:
            file_path = Path(task["file_name"])
            if not file_path.exists():
                logger.info(
                    f"Skipping task because file not found: {file_path}"
                )
                return False
            if file_path.suffix in [".pdf", ".docx", ".doc", ".txt"]:
                if not self.retriever.reset(task_id=task["task_id"]):
                    return False
                retrieved_info = self.retriever.retrieve(
                    query=task["Question"], contents=[task["file_name"]]
                )
                retrieved_content = [
                    item["text"]
                    for item in retrieved_info.get("Retrieved Context", [])
                ]
                if retrieved_content:
                    task["Question"] += "\n" + "\n".join(retrieved_content)
            else:
                logger.info(
                    f"Skipping task due to unsupported file "
                    f"format: {file_path.suffix}"
                )
                return False
        return True

    def _create_user_message(self, task: Dict[str, Any]) -> BaseMessage:
        r"""Create a user message from a task.

        Args:
            task (Dict[str, Any]): The task data.

        Returns:
            BaseMessage: The user message.
        """
        return BaseMessage.make_user_message(
            role_name="User",
            content=task["Question"],
        )

    def _process_result(
        self,
        agent: ChatAgent,
        task: Dict[str, Any],
        result: Any,
    ) -> None:
        r"""Process and store the result of a task.

        Args:
            agent (ChatAgent): The agent that generated the result.
            task (Dict[str, Any]): The task data.
            result (Any): The result from the agent.
        """
        model_answer = self._get_final_answer(result.msgs[0].content)
        final_answer = task["Final answer"]
        score = self._question_scorer(model_answer, final_answer)
        tool_calls = result.info.get("tool_calls", [])

        result_data = {
            "task_id": task["task_id"],
            "question": task["Question"],
            "level": task["Level"],
            "model_answer": model_answer,
            "ground_truth": final_answer,
            "tool_calls": [tool.model_dump() for tool in tool_calls],
            "error": None,
            "score": int(score),
            "history": agent.memory.get_context(),
        }
        self._results.append(result_data)
        save_to_jsonl(self.save_to, result_data, mode="a")

    def _handle_error(
        self, task: Dict[str, Any], error: Exception
    ) -> None:
        r"""Handle errors encountered during task processing.

        Args:
            task (Dict[str, Any]): The task data.
            error (Exception): The error encountered.
        """
        logger.warning(f"Error processing task {task['task_id']}: {error}")
        error_data = {
            "task_id": task["task_id"],
            "question": task["Question"],
            "level": task["Level"],
            "model_answer": "ERROR",
            "ground_truth": task["Final answer"],
            "tool_calls": [],
            "error": str(error),
            "score": 0,
        }
        self._results.append(error_data)
        save_to_jsonl(self.save_to, error_data, mode="a")

    def _generate_summary(self) -> Dict[str, Any]:
        r"""Generate and return a summary of the benchmark results.

        Returns:
            Dict[str, Any]: Summary containing total, correct, and results.
        """
        return {
            "total": len(self._results),
            "correct": sum(result["score"] for result in self._results),
            "results": self._results,
        }

    def _question_scorer(self, model_answer: str, ground_truth: str) -> bool:
        r"""Scorer for the GAIA benchmark.
        https://huggingface.co/spaces/gaia-benchmark/leaderboard/blob/main/
        scorer.py

        Args:
            model_answer (str): The model answer.
            ground_truth (str): The ground truth answer.

        Returns:
            bool: The score of the model.
        """
        def _is_float(element: Any) -> bool:
            r"""Check if an element can be converted to float."""
            try:
                float(element)
                return True
            except ValueError:
                return False

        if _is_float(ground_truth):
            logger.info(f"Evaluating {model_answer} as a number.")
            normalized_answer = self._normalize_number_str(model_answer)
            return normalized_answer == float(ground_truth)

        elif any(char in ground_truth for char in [",", ";"]):
            logger.info(
                f"Evaluating {model_answer} as a comma separated list."
            )
            gt_elems = self._split_string(ground_truth)
            ma_elems = self._split_string(model_answer)

            if len(gt_elems) != len(ma_elems):
                logger.warning(
                    "Answer lists have different lengths, returning False.",
                    UserWarning,
                )
                return False

            comparisons = []
            for ma_elem, gt_elem in zip(ma_elems, gt_elems):
                if _is_float(gt_elem):
                    normalized_ma_elem = self._normalize_number_str(ma_elem)
                    comparisons.append(normalized_ma_elem == float(gt_elem))
                else:
                    ma_elem = self._normalize_str(ma_elem, remove_punct=False)
                    gt_elem = self._normalize_str(gt_elem, remove_punct=False)
                    comparisons.append(ma_elem == gt_elem)
            return all(comparisons)
        else:
            logger.info(f"Evaluating {model_answer} as a string.")
            ma_elem = self._normalize_str(model_answer)
            gt_elem = self._normalize_str(ground_truth)
            return ma_elem == gt_elem

    def _normalize_number_str(self, number_str: str) -> float:
        r"""Normalize a number string to float.

        Args:
            number_str (str): The number string to normalize.

        Returns:
            float: The normalized number, or inf if conversion fails.
        """
        for char in ["$", "%", ","]:
            number_str = number_str.replace(char, "")
        try:
            return float(number_str)
        except ValueError:
            logger.error(
                f"String {number_str} cannot be normalized to number str."
            )
            return float("inf")

    def _split_string(
        self, s: str, char_list: Optional[List[str]] = None
    ) -> List[str]:
        r"""Split a string based on a list of characters.

        Args:
            s (str): The string to split.
            char_list (Optional[List[str]], optional): The list of characters
                to split on. (default: :obj:`None`)

        Returns:
            List[str]: The split string parts.
        """
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)

    def _normalize_str(
        self, input_str: str, remove_punct: bool = True
    ) -> str:
        r"""Normalize a string.

        Args:
            input_str (str): The input string to normalize.
            remove_punct (bool): Whether to remove punctuation.

        Returns:
            str: The normalized string.
        """
        no_spaces = re.sub(r"\s", "", input_str)
        if remove_punct:
            translator = str.maketrans("", "", string.punctuation)
            return no_spaces.lower().translate(translator)
        else:
            return no_spaces.lower()

    def _get_final_answer(self, content: str) -> str:
        r"""Get the final answer from the content.

        Args:
            content (str): The content to extract the final answer from.

        Returns:
            str: The final answer.
        """
        final_answer_index = content.find("FINAL ANSWER")
        if final_answer_index == -1:
            return "FINAL ANSWER not found"
        start_index = final_answer_index + len("FINAL ANSWER: ")
        final_answer_content = content[start_index:].strip()
        return final_answer_content
