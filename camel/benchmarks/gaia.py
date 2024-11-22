# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
import logging
import os
import random
import re
import string
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.retrievers.auto_retriever import AutoRetriever

logger = logging.getLogger(__name__)


def run_task(model_config, agent_config, msg):
    model = ModelFactory.create(**model_config)
    agent = ChatAgent(**agent_config, model=model)
    result = agent.step(msg)
    return result.msgs[0].content, result.info.get("tool_calls", [])


class GAIABenchmark(BaseBenchmark):
    def __init__(
        self,
        data_dir: str,
        save_to: str,
        retriever: AutoRetriever,
        retrieve_kwargs: Optional[Dict[str, Any]] = None,
        processes: int = 1,
    ):
        super().__init__("gaia", data_dir, save_to, processes)
        self._retriever = retriever
        self._retriever_dir = Path(
            self._retriever.vector_storage_local_path or os.getcwd()
        )
        self._retrieve_kwargs = retrieve_kwargs or dict()

    def download(self):
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id="gaia-benchmark/GAIA",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )

    def load(self, force_download=False):
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
        raise NotImplementedError("GAIA does not have a training set.")

    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        level: Union[List[int], Literal["all"]],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
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
        agent = self._inject(agent)
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
                        retriever_dir = self._retriever_dir / task["task_id"]
                        self._retriever.vector_storage_local_path = (
                            retriever_dir
                        )
                        if not retriever_dir.exists():
                            retriever_dir.mkdir(parents=True)
                        retrieved_info = self._retriever.run_vector_retriever(
                            query=task["Question"],
                            contents=[task['file_name']],
                            **self._retrieve_kwargs,
                        )
                        retrieved_content = [
                            i["text"]  # type: ignore[index]
                            for i in retrieved_info["Retrieved Context"]
                        ]
                        if retrieved_content:
                            task["Question"] += "\n".join(retrieved_content)
                    else:
                        logger.info(
                            f"Skipping task because {tmp.suffix} ",
                            "format not supported.",
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
                            "model_answer": "ERROR",
                            "ground_truth": final_answer,
                            "tool_calls": [],
                            "error": str(e),
                            "score": 0,
                        }
                    )
                agent.reset()

                self._results[-1]["history"] = self._current_history
                self._current_history = []
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
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)

    def normalize_str(self, input_str, remove_punct=True) -> str:
        no_spaces = re.sub(r"\s", "", input_str)
        if remove_punct:
            translator = str.maketrans("", "", string.punctuation)
            return no_spaces.lower().translate(translator)
        else:
            return no_spaces.lower()

    def get_final_answer(self, content: str) -> str:
        final_answer_index = content.find("FINAL ANSWER")
        if final_answer_index == -1:
            return "FINAL ANSWER not found"
        start_index = final_answer_index + len("FINAL ANSWER: ")
        final_answer_content = content[start_index:].strip()
        return final_answer_content
