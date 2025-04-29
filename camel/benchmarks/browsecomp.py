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
import logging
import os
import random
import re
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from multiprocessing.pool import Pool, ThreadPool
from typing import Any, Callable

import jinja2
import numpy as np
import pandas
from tqdm import tqdm

from camel.benchmarks.base import BaseBenchmark
from camel.models.model_factory import ModelFactory

logger = logging.getLogger(__name__)

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
numerical problems. Answer 'no' otherwise, i.e. if there if there is any 
inconsistency, ambiguity, non-equivalency, or if the extracted answer is 
incorrect.


confidence: The extracted confidence score between 0|\%| and 100|\%| 
from [response]. Put 100 if there is no confidence score available.
""".strip()

Message = dict[str, Any]  # keys role, content
MessageList = list[Message]

jinja_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    undefined=jinja2.StrictUndefined,
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)


def message_to_html(message: Message) -> str:
    """
    Generate HTML snippet (inside a <div>) for a message.
    """
    return jinja_env.from_string(_message_template).render(
        role=message["role"],
        content=message["content"],
        variant=message.get("variant", None),
    )


jinja_env.globals["message_to_html"] = message_to_html


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


def derive_key(password: str, length: int) -> bytes:
    """Derive a fixed-length key from the password using SHA256."""
    hasher = hashlib.sha256()
    hasher.update(password.encode())
    key = hasher.digest()
    return key * (length // len(key)) + key[: length % len(key)]


def decrypt(ciphertext_b64: str, password: str) -> str:
    """Decrypt base64-encoded ciphertext with XOR."""
    encrypted = base64.b64decode(ciphertext_b64)
    key = derive_key(password, len(encrypted))
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key))
    return decrypted.decode()


@dataclass
class SingleEvalResult:
    """
    Result of evaluating a single sample
    """

    score: float | None
    html: str
    convo: MessageList
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class EvalResult:
    """
    Result of running an evaluation (usually consisting of many samples)
    """

    score: float | None  # top-line metric
    metrics: dict[str, float] | None  # other metrics
    htmls: list[str]  # strings of valid HTML
    convos: list[MessageList]  # sampled conversations


def make_report(eval_result: EvalResult) -> str:
    """
    Create a standalone HTML report from an EvalResult.
    """
    return jinja_env.from_string(_report_template).render(
        score=eval_result.score,
        metrics=eval_result.metrics,
        htmls=eval_result.htmls,
    )


def _compute_stat(values: list, stat: str):
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
    single_eval_results: list[SingleEvalResult],
    default_stats: tuple[str, str] = ("mean", "std"),
    name2stats: dict[str, tuple[str]] | None = None,
) -> EvalResult:
    """
    Aggregate results from multiple evaluations into a single EvalResult.
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


# Above are from https://github.com/openai/simple-evals/blob/main/browsecomp_eval.py


class BrowseCompBenchmark(BaseBenchmark):
    """
    BrowseComp Benchmark for evaluating browser-based comprehension tasks.
    """

    def __init__(
        self,
        save_to: str,
        processes: int = 1,
        num_examples: int | None = None,
        n_repeats: int = 1,
    ):
        r"""Initialize the BrowseComp benchmark.

        Args:
            save_to (str): The file to save the results.
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
            num_examples (int | None, optional): Number of examples to
                evaluate. If None, all examples are used. Controls the
                sample size for testing.
            n_repeats (int, optional): Number of times to repeat each example.
                Useful for evaluating consistency across multiple runs.
        """
        # Browsecomp benchmark won't download any data
        # use current path as the data_dir passing into super init
        current_path = os.path.dirname(os.path.abspath(__file__))

        super().__init__("browsecomp", current_path, save_to, processes)
        # Store configuration parameters
        # Number of examples to sample (if None, use all)
        self.num_examples = num_examples
        self.n_repeats = n_repeats
        self.examples: list[dict[str, Any]] = []
        # Load the examples from the dataset
        self.load()
        # Initialize result storage
        self._raw_results: list[Any] = []  # Will store raw evaluation results
        # Will store validated results after LLM evaluation
        self._validated_results: list[Any] = []
        self._eval_result: EvalResult  # Will store final aggregated results

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
        df = pandas.read_csv(
            "https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv"
        )
        # Convert each row to a dictionary
        examples = [row.to_dict() for _, row in df.iterrows()]

        # Sample examples if num_examples is specified
        if self.num_examples:
            assert self.n_repeats == 1, (
                "n_repeats only supported when max_examples = None"
            )
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

    def run(  # type: ignore[override, return]
        self, process_each_row_f: Callable
    ):
        """
        Run the benchmark by processing each example in parallel.

        This method applies the provided function to each example in the
        dataset using a process pool for parallel execution. It shows
        progress using tqdm and stores the results in self.raw_results.

        Args:
            process_each_row_f (callable): Function to process each example.
                This function should take a row (dict) and return a dict with
                'problem', 'answer', and 'response' keys.
        """
        # Use a process pool for parallel execution
        pool_class = Pool
        # Limit the number of processes
        with pool_class(min(self.processes, len(self.examples))) as pool:
            # Process each example in parallel and collect results
            self._raw_results = list(
                tqdm(
                    pool.imap(process_each_row_f, self.examples),
                    total=len(self.examples),
                )
            )
        return self

    def validate(self, model_config: dict):
        """
        Validate the raw results using the GRADER_TEMPLATE and an LLM.

        This method evaluates the correctness of each response by using an LLM
        to compare it with the expected answer. It aggregates the results and
        generates a report.

        Args:
            model_config (dict): Configuration for the LLM used for validation
        """

        model = ModelFactory.create(**model_config)

        def validate_each_one(result: dict):
            """
            Validate a single result using the LLM grader.

            This inner function formats the prompt for the LLM grader, sends
            it for evaluation, extracts the correctness assessment, and
            creates an HTML representation of the result.

            Args:
                result (dict): A dictionary containing 'problem', 'response',
                and 'answer' keys

            Returns:
                SingleEvalResult: An evaluation result object with score,
                metrics, and HTML
            """
            # Format the template
            prompt = GRADER_TEMPLATE.format(
                question=result['problem'],
                response=result['response'],
                correct_answer=result['answer'],
            )

            # Send to LLM for evaluation
            # Convert to OpenAIMessage format
            from camel.messages import OpenAIMessage

            messages: list[OpenAIMessage] = [
                {"role": "user", "content": prompt}
            ]
            try:
                # Get the LLM's assessment
                response = model.run(messages)

                # None streaming only.
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    # Extract the yes/no correctness judgment using regex
                    match = (
                        re.search(r"correct: (yes|no)", str(content))
                        if content
                        else None
                    )
                grade_result = match.group(1) if match else "no"

                # Convert to binary metrics (1 for correct, 0 for incorrect)
                is_correct = int(grade_result == "yes")
                is_incorrect = int(grade_result == "no")

                # Extract the answer from the response
                extracted_match = re.search(
                    r"Exact Answer:.*", result['response']
                )

                # Set the score (1 for correct, 0 for incorrect)
                score = is_correct

                # Generate HTML representation of the result
                html = jinja_env.from_string(HTML_JINJA).render(
                    prompt_messages=dict(
                        content=result['problem'], role="user"
                    ),
                    next_message=dict(
                        content=result['response'], role="assistant"
                    ),
                    score=score,
                    correct_answer=result['answer'],
                    extracted_answer=extracted_match.group(0).replace(
                        'Exact Answer:', ''
                    )
                    if extracted_match
                    else 'N/A',
                )

                # Create a conversation list for the result
                convo = [
                    dict(content=result['problem'], role="user"),
                    dict(content=result['response'], role="assistant"),
                ]

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

        # Use ThreadPool instead of Pool to avoid pickling issues
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
        print("AGGREGATE METRICS")
        print(aggregate_metrics)
        print("##################")

        output_d = {
            "accuracy": aggregate_metrics["is_correct"],
        }

        print(f"Accuracy: {output_d['accuracy']:.3f}")

        self._eval_result = aggregate_results(self._validated_results)
        # ^^^ how to use a sampler
        report_filename = self.save_to
        print(f"Writing report to {report_filename}")
        with open(report_filename, "w") as fh:
            fh.write(make_report(self._eval_result))
