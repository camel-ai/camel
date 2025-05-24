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

import base64
import hashlib
import json
import os
import random
import traceback
from collections import defaultdict
from multiprocessing.pool import ThreadPool
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from camel.agents.chat_agent import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.logger import get_logger
from camel.societies.role_playing import RolePlaying
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task

logger = get_logger(__name__)


class Message(BaseModel):
    role: str
    content: str
    variant: Optional[str] = None


MessageList = List[Message]


class QueryResponse(BaseModel):
    r"""A structured query response for benchmark evaluation.

    This class defines the expected format for model responses to benchmark
    questions, including explanation, exact answer, and confidence score.
    """

    explanation: str = Field(
        description="""your explanation for your final answer."""
    )
    exact_answer: str = Field(description="""your succinct, final answer.""")
    confidence: str = Field(
        description="""
your confidence score between 0|\%| and 100|\%| for your answer.
"""
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
        description="""The extracted confidence score between 0|\%| 
and 100|\%| from [response]. Put 100 if there is no confidence score available.
"""
    )


class SingleEvalResult(BaseModel):
    r"""Result of evaluating a single benchmark sample.

    This class stores the evaluation results for a single benchmark example,
    including score, HTML representation, conversation history, and metrics.
    """

    score: Optional[float] = None
    html: str
    convo: MessageList
    metrics: Dict[str, float] = Field(default_factory=dict)


class EvalResult(BaseModel):
    r"""Result of running a complete benchmark evaluation.

    This class aggregates results from multiple sample evaluations, storing
    the overall score, detailed metrics, HTML reports, and conversation logs.
    """

    score: Optional[float] = None  # top-line metric
    metrics: Optional[Dict[str, float]] = None  # other metrics
    htmls: List[str]  # strings of valid HTML
    convos: List[MessageList]  # sampled conversations


# Define the message template first
_message_template = """
<div class="message {{ role }}">
    <div class="role">
    {{ role }}
    {% if variant %}<span class="variant">({{ variant }})</span>{% endif %}
    </div>
    <div class="content">
    <pre>{{ content }}</pre>
    </div>
</div>
"""

# TODO: Add necessary prompts when tuning.
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


confidence: The extracted confidence score between 0|\%| and 100|\%| 
from [response]. Put 100 if there is no confidence score available.
""".strip()


HTML_JINJA = """
<h3>Question:</h3>
{{ message_to_html(prompt_messages) | safe }}
<h3>Sampled message</h3>
{{ message_to_html(next_message) | safe }}
<h3>Results</h3>
<p>Correct Answer: {{ correct_answer }}</p>
<p>Extracted Answer: {{ extracted_answer }}</p>
<p>Score: {{ score }}</p>
"""
_report_template = """<!DOCTYPE html>
<html>
    <head>
        <style>
            .message {
                padding: 8px 16px;
                margin-bottom: 8px;
                border-radius: 4px;
            }
            .message.user {
                background-color: #B2DFDB;
                color: #00695C;
            }
            .message.assistant {
                background-color: #B39DDB;
                color: #4527A0;
            }
            .message.system {
                background-color: #EEEEEE;
                color: #212121;
            }
            .role {
                font-weight: bold;
                margin-bottom: 4px;
            }
            .variant {
                color: #795548;
            }
            table, th, td {
                border: 1px solid black;
            }
            pre {
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
    {% if metrics %}
    <h1>Metrics</h1>
    <table>
    <tr>
        <th>Metric</th>
        <th>Value</th>
    </tr>
    <tr>
        <td><b>Score</b></td>
        <td>{{ score | float | round(3) }}</td>
    </tr>
    {% for name, value in metrics.items() %}
    <tr>
        <td>{{ name }}</td>
        <td>{{ value }}</td>
    </tr>
    {% endfor %}
    </table>
    {% endif %}
    <h1>Examples</h1>
    {% for html in htmls %}
    {{ html | safe }}
    <hr>
    {% endfor %}
    </body>
</html>
"""


class JinjaEnv:
    r"""A class that encapsulates the Jinja environment setup."""

    _instance: Optional['JinjaEnv'] = None
    _env = None

    def __init__(self):
        r"""Initialize the JinjaEnv instance if not already initialized."""
        if not getattr(self, '_initialized', False):
            self._initialized = True

    def __new__(cls):
        r"""Implement singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(JinjaEnv, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls):
        r"""Get the singleton instance of JinjaEnv.

        Returns:
            JinjaEnv: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def env(self):
        r"""Lazily initialize and return the Jinja environment.

        Returns:
            jinja2.Environment: The Jinja environment instance.
        """
        if self._env is None:
            # Lazy import of jinja2
            import jinja2

            # Create the Jinja environment
            self._env = jinja2.Environment(
                loader=jinja2.BaseLoader(),
                undefined=jinja2.StrictUndefined,
                autoescape=jinja2.select_autoescape(["html", "xml"]),
            )

            # Register the message_to_html function
            self._env.globals["message_to_html"] = self.message_to_html

        return self._env

    def from_string(self, template_str):
        r"""Create a template from the given string.

        Args:
            template_str (str): The template string.

        Returns:
            jinja2.Template: The compiled template.
        """
        return self.env.from_string(template_str)

    @staticmethod
    def message_to_html(message: Message) -> str:
        r"""Generate HTML snippet (inside a <div>) for a message.

        Args:
            message (Message): The message to convert to HTML.

        Returns:
            str: The HTML representation of the message.
        """
        return (
            JinjaEnv.get_instance()
            .from_string(_message_template)
            .render(
                role=message.role,
                content=message.content,
                variant=message.variant,
            )
        )


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


def _compute_stat(values: list, stat: str):
    import numpy as np

    if stat == "mean":
        return np.mean(values)
    elif stat == "std":
        return np.std(values)
    elif stat == "min":
        return np.min(values)
    elif stat == "max":
        return np.max(values)
    else:
        raise ValueError(f"Unknown {stat =}")


def aggregate_results(
    single_eval_results: List[SingleEvalResult],
    default_stats: Tuple[str, str] = ("mean", "std"),
    name2stats: Optional[Dict[str, Tuple[str]]] = None,
) -> EvalResult:
    r"""Aggregate results from multiple evaluations into a single EvalResult.

    Args:
        single_eval_results (List[SingleEvalResult]): A list of
            `SingleEvalResult` objects.
        default_stats (Tuple[str, str]): A tuple of default statistics to
            compute. (default: :obj:`("mean", "std")`)
        name2stats (Optional[Dict[str, Tuple[str]]]): A dictionary mapping
            metric names to statistics to compute. (default: :obj:`None`)

    Returns:
        EvalResult: An `EvalResult` object containing aggregated results.
    """
    name2stats = name2stats or {}
    name2values = defaultdict(list)
    htmls = []
    convos = []

    for single_eval_result in single_eval_results:
        for name, value in single_eval_result.metrics.items():
            name2values[name].append(value)
        if single_eval_result.score is not None:
            name2values["score"].append(single_eval_result.score)
        htmls.append(single_eval_result.html)
        convos.append(single_eval_result.convo)

    final_metrics = {}
    for name, values in name2values.items():
        stats = name2stats.get(name, default_stats)
        for stat in stats:
            key = name if stat == "mean" else f"{name}:{stat}"
            final_metrics[key] = _compute_stat(values, stat)

    return EvalResult(
        score=final_metrics.pop("score", None),
        metrics=final_metrics,
        htmls=htmls,
        convos=convos,
    )


class BrowseCompBenchmark(BaseBenchmark):
    r"""BrowseComp Benchmark for evaluating browser-based comprehension tasks.

    This benchmark evaluates the ability of language models to comprehend and
    answer questions based on browser-based content, measuring accuracy and
    performance.
    """

    def __init__(
        self,
        save_to: str,
        processes: int = 1,
        num_examples: Optional[int] = None,
        n_repeats: int = 1,
    ):
        r"""Initialize the BrowseComp benchmark.

        Args:
            save_to (str): The file to save the results.
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
            num_examples (Optional[int]): Number of examples to evaluate.
                If None, all examples are used. Controls the sample size for
                testing. (default: :obj:`None`)
            n_repeats (int, optional): Number of times to repeat each example.
                Useful for evaluating consistency across multiple runs.
                (default: :obj:`1`)
        """
        # Browsecomp benchmark won't download any data
        # use current path as the data_dir passing into super init
        current_path = os.path.dirname(os.path.abspath(__file__))

        super().__init__("browsecomp", current_path, save_to, processes)
        self.num_examples = num_examples
        self.n_repeats = n_repeats
        self.examples: List[Dict[str, Any]] = []
        self.load()
        self._raw_results: List[Any] = []
        self._validated_results: List[SingleEvalResult] = []
        self._eval_result: EvalResult
        self.jinja_env = JinjaEnv.get_instance()

    def download(self):
        r"""Download the BrowseComp dataset.

        This method is implemented to maintain compatibility
        with the BaseBenchmark interface, but BrowseComp doesn't
        require downloading data separately.

        Returns:
            self: The benchmark instance
        """
        logger.info("BrowseComp benchmark does not require downloading data.")
        return self

    def load(self):
        r"""Load the BrowseComp dataset.

        This method loads the dataset from a remote CSV file, converts each
        row to a dictionary, and applies sampling if num_examples is
        specified. It also handles repeating examples if n_repeats > 1.

        Returns:
            self: The benchmark instance
        """
        # Load dataset from remote CSV
        import pandas

        df = pandas.read_csv(
            "https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv"
        )
        # Convert each row to a dictionary
        examples = [row.to_dict() for _, row in df.iterrows()]

        # Sample examples if num_examples is specified
        if self.num_examples:
            assert (
                self.n_repeats == 1
            ), "n_repeats only supported when max_examples = None"
            rng = random.Random(0)  # Use fixed seed for reproducibility
            examples = rng.sample(examples, self.num_examples)

        # Repeat examples if n_repeats > 1
        self.examples = examples * self.n_repeats
        return self

    @property
    def train(self):
        r"""Get the training set.

        This property is implemented to maintain compatibility with
        the BaseBenchmark interface, but BrowseComp doesn't have a
        training set.

        Raises:
            NotImplementedError: BrowseComp does not have a training set.
        """
        raise NotImplementedError("BrowseComp does not have a training set.")

    def run(  # type: ignore[override]
        self,
        pipeline_template: Union[ChatAgent, RolePlaying, Workforce],
        chat_turn_limit: int = 10,
        roleplaying_summarizer: Optional[ChatAgent] = None,
        task_json_formatter: Optional[ChatAgent] = None,
    ) -> None:
        r"""Run the benchmark by processing each example in parallel.

        This method applies the provided pipeline to each example in the
        dataset using a process pool for parallel execution. It shows progress
        using tqdm and stores the results in self._raw_results.

        Args:
            pipeline_template (Union[ChatAgent, RolePlaying, Workforce]): The
                template agent or framework to use for processing examples.
                Can be a ChatAgent, RolePlaying, or Workforce instance that
                will be cloned for each example.
            chat_turn_limit (int): Maximum number of conversation turns allowed
                when using RolePlaying pipeline. (default: :obj:`10`)
            roleplaying_summarizer (Optional[ChatAgent]): Optional ChatAgent to
                summarize RolePlaying conversations. If None and RolePlaying is
                used, a default summarizer will be created.
                (default: :obj:`None`)
            task_json_formatter (Optional[ChatAgent]): Optional ChatAgent to
                format task JSON. If None and Workforce is used, a default
                formatter will be created. (default: :obj:`None`)
        """
        from tqdm import tqdm

        # Use a process pool for parallel execution
        def process_benchmark_row(row: Dict[str, Any]) -> Dict[str, Any]:
            r"""This inner function processes a single benchmark row by
            extracting the problem and answer, creating a pipeline instance,
            and generating a response using the appropriate method based on
            the pipeline type.

            Args:
                row (Dict[str, Any]): A row from the dataset containing
                    encrypted problem and answer, along with a canary for
                    decryption.

            Returns:
                Dict[str, Any]: A dictionary containing the decrypted problem,
                    expected answer, model response, and structured response
                    fields.
            """

            problem = decrypt(row.get("problem", ""), row.get("canary", ""))
            answer = decrypt(row.get("answer", ""), row.get("canary", ""))
            try:
                input_message = QUERY_TEMPLATE.format(question=problem)

                if isinstance(pipeline_template, (ChatAgent)):
                    pipeline = pipeline_template.clone()  # type: ignore[assignment]

                    response_text = pipeline.step(
                        input_message, response_format=QueryResponse
                    )
                elif isinstance(pipeline_template, Workforce):
                    pipeline = pipeline_template.clone()  # type: ignore[assignment]
                    task = Task(content=input_message, id="0")
                    task = pipeline.process_task(task)  # type: ignore[attr-defined]
                    if task_json_formatter:
                        formatter_in_process = task_json_formatter.clone()
                    else:
                        formatter_in_process = ChatAgent(
                            "You are a helpful assistant."
                        )
                    response_text = formatter_in_process.step(
                        FORMAT_JSON_TEMPLATE.format(content=task.result),
                        response_format=QueryResponse,
                    )

                elif isinstance(pipeline_template, RolePlaying):
                    # RolePlaying is different.
                    pipeline = pipeline_template.clone(  # type: ignore[assignment]
                        task_prompt=input_message
                    )

                    n = 0
                    input_msg = pipeline.init_chat()  # type: ignore[attr-defined]
                    chat_history = []
                    while n < chat_turn_limit:
                        n += 1
                        assistant_response, user_response = pipeline.step(
                            input_msg
                        )
                        if assistant_response.terminated:  # type: ignore[attr-defined]
                            break
                        if user_response.terminated:  # type: ignore[attr-defined]
                            break
                        if "CAMEL_TASK_DONE" in user_response.msg.content:  # type: ignore[attr-defined]
                            break

                        chat_history.append(
                            f"AI User: {user_response.msg.content}"  # type: ignore[attr-defined]
                        )
                        chat_history.append(
                            f"AI Assistant: {assistant_response.msg.content}"  # type: ignore[attr-defined]
                        )
                        input_msg = assistant_response.msg  # type: ignore[attr-defined]

                    chat_history_str = "\n".join(chat_history)
                    if roleplaying_summarizer:
                        summarizer_in_process = roleplaying_summarizer.clone()
                    else:
                        summarizer_in_process = ChatAgent(
                            "You are a helpful assistant."
                        )

                    summarize_prompt = SUMMARIZE_TEMPLATE.format(
                        chat_history=chat_history_str,
                        query=input_message,
                    )
                    response_text = summarizer_in_process.step(
                        summarize_prompt, response_format=QueryResponse
                    )
                else:
                    raise NotImplementedError(
                        f"{type(pipeline_template)} is not supported."
                    )
                # Parse the response JSON
                response_dict = json.loads(response_text.msg.content)

                # Format the response as a key-value string
                formatted_response = f"""
    Explanation: {response_dict['explanation']}

    Exact Answer: {response_dict['exact_answer']}
    Confidence: {response_dict['confidence']}"""

                # Create the result dictionary
                raw_result = {}
                raw_result['problem'] = problem
                raw_result['expected_answer'] = answer
                raw_result['response'] = formatted_response
                # Keep the original dict for reference
                raw_result['response_dict'] = response_dict

                return raw_result
            except Exception as e:
                # Log any errors that occur during evaluation
                logger.error(f"Error evaluating result: {e}")
                logger.error(traceback.format_exc())
                return {
                    'problem': problem,
                    'expected_answer': answer,
                    'response': traceback.format_exc(),
                    'response_dict': {},
                }

        pool_class = ThreadPool
        with pool_class(min(self.processes, len(self.examples))) as pool:
            self._raw_results = list(
                tqdm(
                    pool.imap(process_benchmark_row, self.examples),
                    total=len(self.examples),
                )
            )

    def make_report(self, eval_result: EvalResult) -> str:
        r"""Create a standalone HTML report from an EvalResult."""
        return self.jinja_env.from_string(_report_template).render(
            score=eval_result.score,
            metrics=eval_result.metrics,
            htmls=eval_result.htmls,
        )

    def validate(self, grader: Optional[ChatAgent] = None) -> None:
        r"""Validate the raw results using the GRADER_TEMPLATE and ChatAgent.

        This method evaluates the correctness of each response by
        multi-threading. A dedicated chat agent is created in each thread.
        The chat agent will compare raw result with the expected answer. The
        grading results will be aggregated in a report.

        Args:
            grader: The ChatAgent used for validation. If None, a default
                agent will be created in each thread. If provided, the
                provided agent will be used as a template and be cloned into
                new agents in each thread. (default: :obj:`None`)
        """
        from tqdm import tqdm

        def validate_each_one(raw_result: Dict[str, Any]) -> SingleEvalResult:
            r"""This inner function formats the prompt for the ChatAgent
            grader, sends it for evaluation, extracts the correctness
            assessment, and creates an HTML representation of the result.

            Args:
                raw_result (Dict[str, Any]): A dictionary containing 'problem',
                    'response', and 'expected_answer' keys.

            Returns:
                SingleEvalResult: An evaluation result object with score,
                    metrics, and HTML.
            """
            # Format the template
            prompt = GRADER_TEMPLATE.format(
                question=raw_result['problem'],
                response=raw_result['response'],
                correct_answer=raw_result['expected_answer'],
            )
            if grader:
                grader_in_process = grader.clone()
            else:
                grader_in_process = ChatAgent("You are a helpful assistant.")

            # Create a conversation list for the result
            convo = [
                Message(content=raw_result['problem'], role="user"),
                Message(content=raw_result['response'], role="assistant"),
            ]

            try:
                response = grader_in_process.step(
                    prompt, response_format=GradingResponse
                )

                content = json.loads(response.msg.content)

                grade_result = content['correct']

                # Convert to binary metrics (1 for correct, 0 for incorrect)
                is_correct = int(grade_result == "yes")
                is_incorrect = int(grade_result == "no")

                # Set the score (1 for correct, 0 for incorrect)
                score = is_correct

                # Generate HTML representation of the result
                html = self.jinja_env.from_string(HTML_JINJA).render(
                    prompt_messages=Message(
                        content=raw_result.get('problem', ''), role="user"
                    ),
                    next_message=Message(
                        content=raw_result.get('response', ''),
                        role="assistant",
                    ),
                    score=score,
                    correct_answer=raw_result.get('expected_answer', ''),
                    extracted_answer=raw_result.get('response_dict', {}).get(
                        'exact_answer', ''
                    ),
                )
                # Return the evaluation result
                return SingleEvalResult(
                    html=html,
                    score=score,
                    convo=convo,
                    metrics={
                        "is_correct": is_correct,
                        "is_incorrect": is_incorrect,
                    },
                )
            except Exception as e:
                # Log any errors that occur during evaluation
                logger.error(f"Error evaluating result: {e}")
                logger.error(traceback.format_exc())
                html = self.jinja_env.from_string(HTML_JINJA).render(
                    prompt_messages=Message(
                        content=raw_result.get('problem', ''), role="user"
                    ),
                    next_message=Message(
                        content=raw_result.get('response', ''),
                        role="assistant",
                    ),
                    score=0,
                    correct_answer=raw_result.get('expected_answer', ''),
                    extracted_answer=raw_result.get('response_dict', {}).get(
                        'exact_answer', ''
                    ),
                )
                return SingleEvalResult(
                    html=html,
                    score=0,
                    convo=convo,
                    metrics={
                        "is_correct": 0,
                        "is_incorrect": 1,
                    },
                )

        pool_class = ThreadPool
        with pool_class(min(self.processes, len(self._raw_results))) as pool:
            self._validated_results = list(
                tqdm(
                    pool.imap(validate_each_one, self._raw_results),
                    total=len(self._raw_results),
                )
            )

        aggregate_metrics = {
            "is_correct": sum(
                result.metrics["is_correct"]
                for result in self._validated_results
            )
            / len(self._validated_results),
            "is_incorrect": sum(
                result.metrics["is_incorrect"]
                for result in self._validated_results
            )
            / len(self._validated_results),
        }
        logger.info("AGGREGATE METRICS")
        logger.info(aggregate_metrics)
        logger.info("##################")

        output_d = {
            "accuracy": aggregate_metrics["is_correct"],
        }

        logger.info(f"Accuracy: {output_d['accuracy']:.3f}")

        self._eval_result = aggregate_results(self._validated_results)
        # ^^^ how to use a sampler
        report_filename = self.save_to
        logger.info(f"Writing report to {report_filename}")
        with open(report_filename, "w") as fh:
            fh.write(self.make_report(self._eval_result))
