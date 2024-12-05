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
import logging
import os
import random
import re
import string
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.benchmarks.protocols import RetrieverProtocol
from camel.messages.base import BaseMessage
from camel.retrievers.auto_retriever import AutoRetriever

logger = logging.getLogger(__name__)


class DefaultGAIARetriever(AutoRetriever):
    r"""Default retriever for the GAIA benchmark.
    This retriever uses AutoRetriever in camel to retrieve the content based on
    the query.
    """

    def retrieve(
        self, query: str, contents: List[str], **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Retrieve the content based on the query.

        Args:
            query (str): The query to search for.
            contents (List[str]): The list of contents to search from.
            **kwargs (Dict[str, Any]): The keyword arguments to pass to the
                retriever.

        Returns:
            Dict[str, Any]: The retrieved content.
        """
        return self.run_vector_retriever(
            query=query, contents=contents, **kwargs
        )

    def reset(self, **kwargs: Dict[str, Any]) -> bool:
        r"""Reset the retriever.

        Args:
            **kwargs (Dict[str, Any]): The keyword arguments to pass to the
                retriever.

        Returns:
            bool: Whether the reset was successful.
        """
        path = Path(self.vector_storage_local_path or os.getcwd())
        task_id = kwargs.get("task_id", str(uuid.uuid1()))
        retriever_dir = path / task_id
        if not retriever_dir.exists():
            try:
                retriever_dir.mkdir(parents=True)
            except Exception as e:
                logger.error(
                    "Error in creating directory: " + f"{retriever_dir}: {e!s}"
                )
                return False
        self.vector_storage_local_path = retriever_dir
        return True


class GAIABenchmark(BaseBenchmark):
    r"""GAIA Benchmark adapted from `"GAIA: a benchmark for General AI
    Assistants"
    <https://huggingface.co/datasets/gaia-benchmark/GAIA>`_.

    Args:
        data_dir (str): The directory to save the data.
        save_to (str): The file to save the results.
        retriever (Optional[RetrieverProtocol]): The retriever to use.
            (default: :obj:`None`)
        processes (int, optional): The number of processes to use.
            (default: :obj:`1`)
    """

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        retriever: Optional[RetrieverProtocol] = None,
        processes: int = 1,
    ):
        r"""Initialize the GAIA benchmark.

        Args:
            data_dir (str): The directory to save the data.
            save_to (str): The file to save the results.
            retriever (Optional[RetrieverProtocol], optional): The retriever to
                use. (default: :obj:`None`)
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        super().__init__("gaia", data_dir, save_to, processes)
        self.retriever = retriever or DefaultGAIARetriever()

    def download(self):
        r"""Download the GAIA dataset."""
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id="gaia-benchmark/GAIA",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )

    def load(self, force_download=False):
        r"""Load the GAIA dataset.

        Args:
            force_download (bool, optional): Whether to
                force download the data.
        """
        if force_download:
            logger.info("Force downloading data.")
            self.download()
        valid_dir = self.data_dir / "2023/validation"
        test_dir = self.data_dir / "2023/test"
        if not valid_dir.is_dir() or not test_dir.is_dir():
            logger.info("Data not found. Downloading data.")
            self.download()
        for path, label in zip([valid_dir, test_dir], ["valid", "test"]):
            self._data[label] = []
            with open(path / "metadata.jsonl", "r") as f:
                lines = f.readlines()
                for line in lines:
                    data = json.loads(line)
                    if data["task_id"] == "0-0-0-0-0":
                        continue
                    if data["file_name"]:
                        data["file_name"] = path / data["file_name"]
                    self._data[label].append(data)
        return self

    @property
    def train(self):
        r"""Get the training set."""
        raise NotImplementedError("GAIA does not have a training set.")

    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        level: Union[int, List[int], Literal["all"]],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            agent (ChatAgent): The agent to run the benchmark.
            on (Literal["valid", "test"]): The set to run the benchmark.
            level (Union[int, List[int], Literal["all"]]): The level to run
                the benchmark.
            randomize (bool, optional): Whether to randomize the data.
                (default: :obj:`False`)
            subset (Optional[int], optional): The subset of data to run.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: The results of the benchmark.
        """
        if on not in ["valid", "test"]:
            raise ValueError(
                f"Invalid value for `on`: {on}, expected 'valid' or 'test'."
            )
        if isinstance(level, str) and level == "all":
            levels = [1, 2, 3]
        elif isinstance(level, int):
            levels = [level]
        else:
            levels = level
        if any(_level not in [1, 2, 3] for _level in levels):
            raise ValueError(
                f"Invalid value for `level`: {level},"
                " expected 1, 2, 3 or 'all'."
            )

        logger.info(f"Running benchmark on {on} set at levels {levels}.")
        datas = [data for data in self._data[on] if data["Level"] in levels]
        if randomize:
            random.shuffle(datas)
        if subset:
            datas = datas[:subset]
        logger.info(f"Number of tasks: {len(datas)}")
        self._results = []
        with open(self.save_to, "w") as f:
            for task in tqdm(datas, desc="Running"):
                if task["file_name"] != "":
                    tmp = Path(task["file_name"])
                    if not tmp.exists():
                        logger.info(
                            f"Skipping task because file: {tmp} not found."
                        )
                        continue
                    if tmp.suffix in ['.pdf', '.docx', '.doc', '.txt']:
                        if not self.retriever.reset(task_id=task["task_id"]):
                            continue
                        retrieved_info = self.retriever.retrieve(
                            query=task["Question"],
                            contents=[task['file_name']],
                        )
                        retrieved_content = [
                            i["text"]  # type: ignore[index]
                            for i in retrieved_info["Retrieved Context"]
                        ]
                        if retrieved_content:
                            task["Question"] += "\n".join(retrieved_content)
                    else:
                        logger.info(
                            f"Skipping task because {tmp.suffix} "
                            + "format not supported.",
                        )
                        continue

                msg = BaseMessage.make_user_message(
                    role_name="User",
                    content=task["Question"],
                )
                final_answer = task["Final answer"]
                try:
                    result = agent.step(msg)
                    model_answer = self.get_final_answer(
                        result.msgs[0].content
                    )
                    tool_calls = result.info.get("tool_calls", [])
                    score = self.question_scorer(model_answer, final_answer)
                    self._results.append(
                        {
                            "task_id": task["task_id"],
                            "question": task["Question"],
                            "level": task["Level"],
                            "model_answer": model_answer,
                            "ground_truth": final_answer,
                            "tool_calls": [
                                tool.model_dump() for tool in tool_calls
                            ],
                            "error": None,
                            "score": int(score),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Error in processing task: {task['task_id']}"
                    )
                    self._results.append(
                        {
                            "task_id": task["task_id"],
                            "question": task["Question"],
                            "level": task["Level"],
                            "model_answer": "ERROR",
                            "ground_truth": final_answer,
                            "tool_calls": [],
                            "error": str(e),
                            "score": 0,
                        }
                    )
                agent.reset()

                self._results[-1]["history"] = agent.memory.get_context()

                f.write(json.dumps(self._results[-1], indent=2) + "\n")
                f.flush()

        return {
            "total": len(self._results),
            "correct": sum(r["score"] for r in self._results),
            "results": self._results,
        }

    # scorer part
    # https://huggingface.co/spaces/gaia-benchmark/leaderboard/blob/main/scorer.py
    def question_scorer(self, model_answer: str, ground_truth: str) -> bool:
        r"""Scorer for the GAIA benchmark.

        Args:
            model_answer (str): The model answer.
            ground_truth (str): The ground truth answer.

        Returns:
            bool: The score of the model
        """

        def is_float(element: Any) -> bool:
            try:
                float(element)
                return True
            except ValueError:
                return False

        if is_float(ground_truth):
            logger.info(f"Evaluating {model_answer} as a number.")
            normalized_answer = self.normalize_number_str(model_answer)
            return normalized_answer == float(ground_truth)

        elif any(char in ground_truth for char in [",", ";"]):
            logger.info(
                f"Evaluating {model_answer} as a comma separated list."
            )
            gt_elems = self.split_string(ground_truth)
            ma_elems = self.split_string(model_answer)

            if len(gt_elems) != len(ma_elems):
                logger.warning(
                    "Answer lists have different lengths, returning False.",
                    UserWarning,
                )
                return False

            comparisons = []
            for ma_elem, gt_elem in zip(ma_elems, gt_elems):
                if is_float(gt_elem):
                    normalized_ma_elem = self.normalize_number_str(ma_elem)
                    comparisons.append(normalized_ma_elem == float(gt_elem))
                else:
                    ma_elem = self.normalize_str(ma_elem, remove_punct=False)
                    gt_elem = self.normalize_str(gt_elem, remove_punct=False)
                    comparisons.append(ma_elem == gt_elem)
            return all(comparisons)
        else:
            logger.info(f"Evaluating {model_answer} as a string.")
            ma_elem = self.normalize_str(model_answer)
            gt_elem = self.normalize_str(ground_truth)
            return ma_elem == gt_elem

    def normalize_number_str(self, number_str: str) -> float:
        for char in ["$", "%", ","]:
            number_str = number_str.replace(char, "")
        try:
            return float(number_str)
        except ValueError:
            logger.error(
                f"String {number_str} cannot be normalized to number str."
            )
            return float("inf")

    def split_string(
        self, s: str, char_list: Optional[List[str]] = None
    ) -> list[str]:
        r"""Split a string based on a list of characters.

        Args:
            s (str): The string to split.
            char_list (Optional[List[str]], optional): T
                he list of characters to split on.
                (default: :obj:`None`)
        """
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)

    def normalize_str(self, input_str, remove_punct=True) -> str:
        r"""Normalize a string.

        Args:
            input_str: The input string to normalize.
            remove_punct: Whether to remove punctuation.

        Returns:
            str: The normalized string.
        """
        no_spaces = re.sub(r"\s", "", input_str)
        if remove_punct:
            translator = str.maketrans("", "", string.punctuation)
            return no_spaces.lower().translate(translator)
        else:
            return no_spaces.lower()

    def get_final_answer(self, content: str) -> str:
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
