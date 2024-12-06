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

import concurrent.futures
import json
import logging
import os
import random
import re
import string
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from tqdm import tqdm

from .utils.apibench_utils import encode_question
from .apibench_eval.eval_scripts.ast_eval import ast_parse, evaluate_response

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage
from camel.retrievers import *

logger = logging.getLogger(__name__)

dataset_mapping = {
    "huggingface": {
        "api": "huggingface_api.jsonl",
        "eval": "huggingface_eval.json",
        "train": "huggingface_train.json",
        "questions": "questions_huggingface_0_shot.jsonl"
        },
    "tensorflowhub": {
        "api": "tensorflowhub_api.jsonl",
        "eval": "tensorflow_eval.json",
        "train": "tensorflow_train.json",
        "questions": "questions_tensorflowhub_0_shot.jsonl"
        },
    "torchhub": {
        "api": "torchhub_api.jsonl",
        "eval": "torchhub_eval.json",
        "train": "torchhub_train.json",
        "questions": "questions_torchhub_0_shot.jsonl"
        },
        }

class APIBenchBenchmark(BaseBenchmark): # TODO: Integrate retriver

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        #retriever: Union[BaseRetriever] = None,
        #retrieve_kwargs: Optional[Dict[str, Any]] = None,
        processes: int = 1,
    ):
        super().__init__("apibench", data_dir, save_to, processes)
        #self._retriever = retriever
        #self._retrieve_kwargs = retrieve_kwargs or dict()

    def download(self):
        r"""Download the GAIA dataset."""
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id="gorilla-llm/APIBench",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )

    def load(self, dataset_name):
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        for label in ['api', 'eval', 'questions']:
            file_name = dataset_mapping[dataset_name][label]
            if label == 'questions':
                file_path = current_dir / f"apibench_eval/questions/{dataset_name}/{file_name}"
                questions = []
                with open(file_path, "r") as f:
                    for line in f:
                        questions.append(json.loads(line))
                self._data[label] = questions
            if label == 'api':
                file_path = self.data_dir / file_name
                api_database = []
                with open(file_path, "r") as f:
                    for line in f:
                        api_database.append(json.loads(line))
                self._data[label] = api_database
            elif label == 'eval':
                file_path = self.data_dir / file_name
                data = []
                with open(file_path, "r") as f:
                    for line in f:
                        data.append(json.loads(line)['api_data'])
                self._data[label] = data

        ast_database = []
        for data in api_database:
            ast_tree = ast_parse(data['api_call'])
            ast_database.append(ast_tree)
        self._data['ast'] = ast_database
        


    
    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        dataset: Union[int, List[int], Literal[
            "huggingface",
            "tensorflowhub",
            "torchhub"
        ]],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark
        """
        pass
        if dataset not in dataset_mapping:
            raise ValueError(f"Invalid value for dataset: {dataset}.")
        
        logger.info(f"Running Nexus Function Calling benchmark on {dataset}.")
        self.load(dataset)
        datas = self._data['questions']
        if randomize:
            random.shuffle(datas)
        if subset:
            datas = datas[:subset]
        logger.info(f"Number of tasks: {len(datas)}")
        self._results = []

        with open(self.save_to, "w") as f:
            for question in tqdm(datas, desc="Running"):
                prompt = encode_question(question["text"], dataset)
                msg = BaseMessage.make_user_message(
                    role_name="User",
                    content=prompt
                )
                try:
                    response = agent.step(msg)
                    response = response.msgs[0].content
                    api_database = self._data['api']
                    qa_pairs = self._data['eval']
                    ast_database = self._data['ast']
                    question_id = question['question_id']

                    error, correct, hallucination = evaluate_response(response, question_id, dataset, api_database, qa_pairs, ast_database)
                    self._results.append(
                            {
                                "question": question,
                                "agent_response": response,
                                "correct": correct,
                                "hallucination": hallucination,
                                "error": str(error)
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error in processing task: {question}: {e}")
                    self._results.append(
                        {
                                "question": question,
                                "agent_response": None,
                                "correct": False,
                                "hallucination": False,
                                "error": str(e)
                        }
                    )

                agent.reset()

                f.write(json.dumps(self._results[-1], indent=2) + "\n")
                f.flush()
        
        total = len(self._results)
        correct = sum(r["correct"] for r in self.results)
        hallucination = sum(r["hallucination"] for r in self.results)

        return {
            "total": total,
            "correct": correct,
            "hallucination": hallucination,
            "accuracy": correct / total,
            "hallucination rate": hallucination / total
        }



        


