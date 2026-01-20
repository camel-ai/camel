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

import base64
import hashlib
import json
import logging
import random
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks._utils import save_to_jsonl
from camel.benchmarks.base import BaseBenchmark
from camel.societies.role_playing import RolePlaying
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task

logger = logging.getLogger(__name__)


class QueryResponse(BaseModel):
    r"""A structured query response for benchmark evaluation.

    This class defines the expected format for model responses to benchmark
    questions, including explanation, exact answer, and confidence score.
    """

    explanation: str = Field(
        description="your explanation for your final answer."
    )
    exact_answer: str = Field(description="your succinct, final answer.")
    confidence: str = Field(
        description="your confidence score between 0% and 100% for your answer."
    )


class GradingResponse(BaseModel):
    r"""A structured grading response for evaluating model answers.

    This class defines the expected format for grading responses, including
    extracted answer, reasoning about correctness, binary correctness judgment,
    and confidence score extraction.
    """

    extracted_final_answer: str = Field(
        description="""
The final exact answer extracted from the [response].
Put the extracted answer as 'None' if there is no exact, final answer to
extract from the response."""
    )
    reasoning: str = Field(
        description="""
Explain why the extracted_final_answer is correct or incorrect
based on [correct_answer], focusing only on if there are meaningful
differences between [correct_answer] and the extracted_final_answer.
Do not comment on any background to the problem, do not attempt
to solve the problem, do not argue for any answer different
than [correct_answer], focus only on whether the answers match."""
    )
    correct: str = Field(
        description="""Answer 'yes' if extracted_final_answer matches the
[correct_answer] given above, or is within a small margin of error for
numerical problems. Answer 'no' otherwise, i.e. if there if there is any
inconsistency, ambiguity, non-equivalency, or if the extracted answer is
incorrect."""
    )
    confidence: str = Field(
        description="""The extracted confidence score between 0%
and 100% from [response]. Put 100 if there is no confidence score available."""
    )


# Query prompt template
QUERY_TEMPLATE = """
{question}

Your response should be in the following format:
Explanation: {{your explanation for your final answer}}
Exact Answer: {{your succinct, final answer}}
Confidence: {{your confidence score between 0% and 100% for your answer}}
""".strip()


SUMMARIZE_TEMPLATE = """
Based on the chat history:
{chat_history}

answer the question:
{query}
"""


FORMAT_JSON_TEMPLATE = """
format content into json:
{content}
"""


GRADER_TEMPLATE = """
Judge whether the following [response] to [question] is correct or not
based on the precise and unambiguous [correct_answer] below.

[question]: {question}

[response]: {response}

Your judgement must be in the format and criteria specified below:

extracted_final_answer: The final exact answer extracted from the [response].
Put the extracted answer as 'None' if there is no exact, final answer to
extract from the response.

[correct_answer]: {correct_answer}

reasoning: Explain why the extracted_final_answer is correct or incorrect
based on [correct_answer], focusing only on if there are meaningful
differences between [correct_answer] and the extracted_final_answer.
Do not comment on any background to the problem, do not attempt
to solve the problem, do not argue for any answer different
than [correct_answer], focus only on whether the answers match.

correct: Answer 'yes' if extracted_final_answer matches the
[correct_answer] given above, or is within a small margin of error for
numerical problems. Answer 'no' otherwise, i.e. if there is any
inconsistency, ambiguity, non-equivalency, or if the extracted answer is
incorrect.

confidence: The extracted confidence score between 0%
and 100% from [response]. Put 100 if there is no confidence score available.
""".strip()


def derive_key(password: str, length: int) -> bytes:
    r"""Derive a fixed-length key from the password using SHA256."""
    hasher = hashlib.sha256()
    hasher.update(password.encode())
    key = hasher.digest()
    return key * (length // len(key)) + key[: length % len(key)]


def decrypt(ciphertext_b64: str, password: str) -> str:
    r"""Decrypt base64-encoded ciphertext with XOR."""
    encrypted = base64.b64decode(ciphertext_b64)
    key = derive_key(password, len(encrypted))
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key))
    return decrypted.decode()


class BrowseCompBenchmark(BaseBenchmark):
    r"""BrowseComp Benchmark for evaluating browser-based comprehension tasks.

    This benchmark evaluates the ability of language models to comprehend and
    answer questions based on browser-based content, measuring accuracy and
    performance.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        save_to: Optional[str] = None,
        processes: int = 1,
    ):
        r"""Initialize the BrowseComp benchmark.

        Args:
            data_dir (Optional[str]): Path to the data directory.
                (default: :obj:`None`)
            save_to (Optional[str]): The file to save the results. If None,
                uses default 'browsecomp_results.jsonl'. (default: :obj:`None`)
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        self.data_dir = data_dir or str(Path(__file__).parent / "data")
        self.save_to = save_to or "browsecomp_results.jsonl"
        super().__init__("browsecomp", self.data_dir, self.save_to, processes)
        self._raw_results: List[Dict[str, Any]] = []

    def download(self) -> None:
        r"""Download the BrowseComp dataset.

        BrowseComp doesn't require downloading data separately as it loads
        directly from a remote URL.
        """
        logger.info(
            "BrowseComp benchmark loads data directly from remote URL, "
            "no download needed."
        )

    def load(
        self,
        num_examples: Optional[int] = None,
        n_repeats: int = 1,
        force_download: bool = False,
    ) -> None:
        r"""Load the BrowseComp dataset.

        Args:
            num_examples (Optional[int]): Number of examples to evaluate.
                If None, all examples are used. (default: :obj:`None`)
            n_repeats (int, optional): Number of times to repeat each example.
                (default: :obj:`1`)
            force_download (bool, optional): Whether to force
                download the data. (default: :obj:`False`)
        """
        _ = force_download
        import pandas as pd

        logger.info("Loading BrowseComp dataset from remote URL.")
        df = pd.read_csv(
            "https://openaipublic.blob.core.windows.net/simple-evals/"
            "browse_comp_test_set.csv"
        )

        # Convert each row to a dictionary
        examples = [row.to_dict() for _, row in df.iterrows()]

        # Sample examples if num_examples is specified
        if num_examples:
            assert (
                n_repeats == 1
            ), "n_repeats only supported when num_examples = None"
            rng = random.Random(0)  # Use fixed seed for reproducibility
            examples = rng.sample(examples, num_examples)

        # Repeat examples if n_repeats > 1
        self._data["test"] = examples * n_repeats
        logger.info(f"Loaded {len(self._data['test'])} examples.")

    def run(
        self,
        pipeline_template: Union[ChatAgent, RolePlaying, Workforce],
        randomize: bool = False,
        subset: Optional[int] = None,
        chat_turn_limit: int = 10,
        roleplaying_summarizer: Optional[ChatAgent] = None,
        task_json_formatter: Optional[ChatAgent] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            pipeline_template (Union[ChatAgent, RolePlaying, Workforce]): The
                template agent or framework to use for processing examples.
            randomize (bool, optional): Whether to randomize the data.
                (default: :obj:`False`)
            subset (Optional[int], optional): The subset of data to run.
                (default: :obj:`None`)
            chat_turn_limit (int): Maximum number of conversation turns allowed
                when using RolePlaying pipeline. (default: :obj:`10`)
            roleplaying_summarizer (Optional[ChatAgent]): Optional ChatAgent to
                summarize RolePlaying conversations. (default: :obj:`None`)
            task_json_formatter (Optional[ChatAgent]): Optional ChatAgent to
                format task JSON. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Dictionary containing:
                - total: Total number of questions evaluated
                - correct: Number of correct answers
                - accuracy: Accuracy score
        """
        if not self._data.get("test"):
            raise ValueError(
                "Dataset not loaded. Please call load() before run()."
            )

        examples = self._data["test"]

        # Shuffle and subset data if necessary
        if randomize:
            random.shuffle(examples)
        if subset:
            examples = examples[:subset]

        logger.info(f"Running benchmark on {len(examples)} examples.")

        # Clear the results file if it exists
        open(self.save_to, "w").close()

        self._results = []
        self._raw_results = []

        def process_example(row: Dict[str, Any]) -> Dict[str, Any]:
            r"""Process a single benchmark example.

            Args:
                row (Dict[str, Any]): A row from the dataset containing
                    encrypted problem and answer.

            Returns:
                Dict[str, Any]: Result dictionary with problem, answer,
                    and response.
            """
            problem = decrypt(row.get("problem", ""), row.get("canary", ""))
            answer = decrypt(row.get("answer", ""), row.get("canary", ""))

            try:
                input_message = QUERY_TEMPLATE.format(question=problem)

                if isinstance(pipeline_template, ChatAgent):
                    pipeline = pipeline_template.clone()
                    response_text = pipeline.step(
                        input_message, response_format=QueryResponse
                    )

                elif isinstance(pipeline_template, Workforce):
                    pipeline = pipeline_template.clone()
                    task = Task(content=input_message, id="0")
                    task = pipeline.process_task(task)

                    if task_json_formatter:
                        formatter = task_json_formatter.clone()
                    else:
                        formatter = ChatAgent("You are a helpful assistant.")

                    response_text = formatter.step(
                        FORMAT_JSON_TEMPLATE.format(content=task.result),
                        response_format=QueryResponse,
                    )

                elif isinstance(pipeline_template, RolePlaying):
                    pipeline = pipeline_template.clone(
                        task_prompt=input_message
                    )

                    n = 0
                    input_msg = pipeline.init_chat()
                    chat_history = []

                    while n < chat_turn_limit:
                        n += 1
                        assistant_response, user_response = pipeline.step(
                            input_msg
                        )
                        if assistant_response.terminated:
                            break
                        if user_response.terminated:
                            break
                        if "CAMEL_TASK_DONE" in user_response.msg.content:
                            break

                        chat_history.append(
                            f"AI User: {user_response.msg.content}"
                        )
                        chat_history.append(
                            f"AI Assistant: {assistant_response.msg.content}"
                        )
                        input_msg = assistant_response.msg

                    chat_history_str = "\n".join(chat_history)

                    if roleplaying_summarizer:
                        summarizer = roleplaying_summarizer.clone()
                    else:
                        summarizer = ChatAgent("You are a helpful assistant.")

                    summarize_prompt = SUMMARIZE_TEMPLATE.format(
                        chat_history=chat_history_str,
                        query=input_message,
                    )
                    response_text = summarizer.step(
                        summarize_prompt, response_format=QueryResponse
                    )
                else:
                    raise NotImplementedError(
                        f"{type(pipeline_template)} is not supported."
                    )

                response_dict = json.loads(response_text.msg.content)

                formatted_response = f"""Explanation: {response_dict['explanation']}

Exact Answer: {response_dict['exact_answer']}
Confidence: {response_dict['confidence']}"""

                return {
                    "problem": problem,
                    "expected_answer": answer,
                    "response": formatted_response,
                    "response_dict": response_dict,
                }

            except Exception as e:
                logger.error(f"Error processing example: {e}")
                return {
                    "problem": problem,
                    "expected_answer": answer,
                    "response": str(e),
                    "response_dict": {},
                    "error": str(e),
                }

        pool_class = ThreadPool
        with pool_class(min(self.processes, len(examples))) as pool:
            self._raw_results = list(
                tqdm(
                    pool.imap(process_example, examples),
                    total=len(examples),
                    desc="Processing",
                )
            )

        validated_results = self._validate_results()

        total = len(validated_results)
        correct = sum(r["score"] for r in validated_results)

        summary = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0.0,
            "results": validated_results,
        }

        logger.info(f"Accuracy: {summary['accuracy']:.3f}")

        return summary

    def _validate_results(
        self, grader: Optional[ChatAgent] = None
    ) -> List[Dict[str, Any]]:
        r"""Validate raw results using grader.

        Args:
            grader (Optional[ChatAgent]): Optional grader agent.
                If None, a default one will be created.

        Returns:
            List[Dict[str, Any]]: Validated results with scores.
        """

        def validate_single(raw_result: Dict[str, Any]) -> Dict[str, Any]:
            r"""Validate a single result.

            Args:
                raw_result (Dict[str, Any]): Raw result to validate.

            Returns:
                Dict[str, Any]: Validated result with score.
            """
            problem = raw_result["problem"]
            response = raw_result["response"]
            expected_answer = raw_result["expected_answer"]

            try:
                if grader:
                    grader_agent = grader.clone()
                else:
                    grader_agent = ChatAgent("You are a helpful assistant.")

                prompt = GRADER_TEMPLATE.format(
                    question=problem,
                    response=response,
                    correct_answer=expected_answer,
                )

                grade_response = grader_agent.step(
                    prompt, response_format=GradingResponse
                )
                content = json.loads(grade_response.msg.content)

                grade_result = content.get("correct", "no")
                score = 1 if grade_result == "yes" else 0

                result = {
                    "problem": problem,
                    "expected_answer": expected_answer,
                    "model_response": response,
                    "extracted_answer": content.get(
                        "extracted_final_answer", ""
                    ),
                    "score": score,
                    "reasoning": content.get("reasoning", ""),
                    "confidence": content.get("confidence", "100"),
                    "error": raw_result.get("error"),
                }

                save_to_jsonl(self.save_to, result, mode="a")

                return result

            except Exception as e:
                logger.error(f"Error validating result: {e}")
                result = {
                    "problem": problem,
                    "expected_answer": expected_answer,
                    "model_response": response,
                    "extracted_answer": "",
                    "score": 0,
                    "reasoning": "",
                    "confidence": "0",
                    "error": str(e),
                }
                save_to_jsonl(self.save_to, result, mode="a")
                return result

        validated = []
        pool_class = ThreadPool
        with pool_class(min(self.processes, len(self._raw_results))) as pool:
            validated = list(
                tqdm(
                    pool.imap(validate_single, self._raw_results),
                    total=len(self._raw_results),
                    desc="Validating",
                )
            )

        return validated
