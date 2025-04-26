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
from multiprocessing.pool import ThreadPool, Pool
import os
import random
import re
import sys
import importlib.util
import pandas
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.messages import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.retrievers.auto_retriever import AutoRetriever
from camel.types.enums import ModelPlatformType
from camel.toolkits.browser_toolkit import BrowserToolkit
# # Direct import of BrowserToolkit from the local file
# browser_toolkit_path = os.path.join(os.path.dirname(
#     os.path.dirname(__file__)), 'toolkits', 'browser_toolkit.py')
# spec = importlib.util.spec_from_file_location(
#     "browser_toolkit", browser_toolkit_path)
# browser_toolkit_module = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(browser_toolkit_module)
# BrowserToolkit = browser_toolkit_module.BrowserToolkit

logger = logging.getLogger(__name__)

# from: https://github.com/centerforaisafety/hle/blob/7b6be5aad6f9b43af3857de7867f3b52f6e4acb3/hle_eval/run_judge_results.py#L16-L33
GRADER_TEMPLATE = """
Judge whether the following [response] to [question] is correct or not based on the precise and unambiguous [correct_answer] below.

[question]: {question}

[response]: {response}

Your judgement must be in the format and criteria specified below:

extracted_final_answer: The final exact answer extracted from the [response]. Put the extracted answer as 'None' if there is no exact, final answer to extract from the response.

[correct_answer]: {correct_answer}

reasoning: Explain why the extracted_final_answer is correct or incorrect based on [correct_answer], focusing only on if there are meaningful differences between [correct_answer] and the extracted_final_answer. Do not comment on any background to the problem, do not attempt to solve the problem, do not argue for any answer different than [correct_answer], focus only on whether the answers match.

correct: Answer 'yes' if extracted_final_answer matches the [correct_answer] given above, or is within a small margin of error for numerical problems. Answer 'no' otherwise, i.e. if there if there is any inconsistency, ambiguity, non-equivalency, or if the extracted answer is incorrect.


confidence: The extracted confidence score between 0|\%| and 100|\%| from [response]. Put 100 if there is no confidence score available.
""".strip()

CHOICE_STRINGS = ["yes", "no"]


def map_with_progress(f: callable, xs: list[Any], num_threads: int = 1, use_processes: bool = False, sequential: bool = False):
    """
    Apply f to each element of xs, using a ThreadPool or ProcessPool, and show progress.

    Args:
        f: Function to apply to each element
        xs: List of elements to process
        num_threads: Number of threads/processes to use
        use_processes: If True, use ProcessPool instead of ThreadPool
        sequential: If True, process sequentially (ignores num_threads and use_processes)
    """
    if sequential or os.getenv("debug"):
        return list(tqdm(map(f, xs), total=len(xs)))
    else:
        pool_class = Pool if use_processes else ThreadPool
        with pool_class(min(num_threads, len(xs))) as pool:
            return list(tqdm(pool.imap(f, xs), total=len(xs)))


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


class BrowseCompBenchmark(BaseBenchmark):
    r"""BrowseComp Benchmark for evaluating browser-based comprehension tasks.

    Args:
        save_to (str): The file to save the results.
        retriever (Optional[RetrieverProtocol]): The retriever to use.
            (default: :obj:`None`)
        processes (int, optional): The number of processes to use.
            (default: :obj:`1`)
    """

    def __init__(
        self,
        save_to: str,
        processes: int = 1,
        num_examples: int | None = None,
        n_repeats: int = 1
    ):
        r"""Initialize the BrowseComp benchmark.

        Args:
            save_to (str): The file to save the results.
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        # Browsecomp benchmark won't download any data
        # use current path as the data_dir passing into super init
        current_path = os.path.dirname(os.path.abspath(__file__))
        super().__init__("browsecomp", current_path, save_to, processes)
        self.num_examples = num_examples
        self.n_repeats = n_repeats
        self.examples = []
        self.load()

    def download(self):
        r"""Download the BrowseComp dataset."""
        logger.info(
            f"BrowseComp benchmark does not require downloading data separately."
        )
        return self

    def load(self):
        r"""Load the BrowseComp dataset.

        Args:
            force_download (bool, optional): Whether to
                force download the data.
        """
        df = pandas.read_csv(
            "https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv"
        )
        examples = [row.to_dict() for _, row in df.iterrows()]
        if self.num_examples:
            assert self.n_repeats == 1, "n_repeats only supported when max_examples = None"
            rng = random.Random(0)
            examples = rng.sample(examples, self.num_examples)
        self.examples = examples * self.n_repeats
        return self

    @property
    def train(self):
        r"""Get the training set."""
        raise NotImplementedError("BrowseComp does not have a training set.")

    def _process_example_with_agent(self, row: dict) -> Any:
        """Process a single example with the provided agent.

        This method is used for sequential processing or thread-based parallelism.
        """
        problem = decrypt(row.get("problem", ""), row.get("canary", ""))
        answer = decrypt(row.get("answer", ""), row.get("canary", ""))

        # Model configuration
        model_config = {
            "model_platform": ModelPlatformType.OPENAI,
            "model_type": "gemini-2.5-pro-exp",
            "url": "https://litellm-cloudrun-668429440317.us-central1.run.app",

        }

        # Create model for the main process
        model = ModelFactory.create(**model_config)

        # Create browser toolkit for the main process
        # web_toolkit = BrowserToolkit(
        #     headless=False,
        #     web_agent_model=model,
        #     planning_agent_model=model,
        #     channel="chromium",
        # )

        # Create agent for the main process
        agent = ChatAgent(
            system_message="You are a helpful assistant.",
            model=model,
            # tools=[*web_toolkit.get_tools()],
        )
        input_message = f"""
            {problem}
            navigate to related website to find the answer.
            
            Your response should be in the following format:
            Explanation:{{your explanation for your final answer}}
            Exact Answer: {{your succinct, final answer}}
            Confidence: {{your confidence score between 0% and 100% for your answer}}
            """.strip()
        response_text = agent.step(input_message)

        print(problem)
        print(response_text.msgs[0].content)
        print(answer)
        return {
            "problem": problem,
            "answer": answer,
            "response": response_text.msgs[0].content
        }

    def _process_example_in_new_process(self, args):
        """Process a single example in a new process with a new agent.

        This method is used for process-based parallelism to avoid pickling issues.
        It creates a new agent for each process, avoiding the need to pickle the agent.
        """
        row = args

        try:
            # Process the example with the new agent
            return self._process_example_with_agent(row)
        except Exception as e:
            print(f"Error processing example: {e}")
            return {
                "problem": "Error processing example",
                "answer": "Error",
                "response": f"Error: {str(e)}",
                "error": str(e)
            }

    def run(  # type: ignore[override]
        self,
        grading_model=None,
        use_processes: bool = True,
        sequential: bool = False,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            agent (ChatAgent): The agent to run the benchmark.
            grading_model: The model to use for grading.
            use_processes (bool): Whether to use processes instead of threads.
                This helps avoid greenlet switching issues with browser toolkit.
            sequential (bool): Whether to process examples sequentially.
                This also avoids greenlet switching issues.
            model_config (Optional[Dict[str, Any]]): Configuration for creating
                new models in separate processes. Required if use_processes=True.

        Returns:
            Dict[str, Any]: The results of the benchmark.
        """
        if use_processes:

            # Prepare arguments for each process: (row, model_config)
            process_args = [row for row in self.examples]

            # Use process-based parallelism with new agents in each process
            results = map_with_progress(
                self._process_example_in_new_process,
                process_args,
                use_processes=True,
                sequential=False
            )
        else:
            # For sequential or thread-based processing, use the provided agent
            def process_example_wrapper(row):
                return self._process_example_with_agent(row)

            # Use sequential processing or thread-based parallelism
            results = map_with_progress(
                process_example_wrapper,
                self.examples,
                use_processes=False,
                sequential=sequential
            )

        return {"results": list(results)}


if __name__ == "__main__":

    try:
        # Create benchmark
        benchmark = BrowseCompBenchmark("", num_examples=2)

        # Process in parallel with separate agents in each process
        # Using 'spawn' method ensures each process has a clean environment
        results = benchmark.run(
            use_processes=True,
            sequential=False,
        )

        print(results)
    except Exception as e:
        print(f"Error running benchmark: {e}")
    finally:
        # Ensure all resources are cleaned up
        print("Benchmark completed, cleaning up resources...")
