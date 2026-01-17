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

import ast
import logging
import textwrap
from typing import Any, Dict, List, Optional, Tuple

from datasets import Dataset, load_dataset
from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.benchmarks._utils import construct_prompt, save_to_jsonl

logger = logging.getLogger(__name__)


class NexusBenchmark(BaseBenchmark):
    r"""Nexus Function Calling Benchmark adapted from `NexusRaven V2
    Function Calling Benchmark`
    <https://huggingface.co/collections/Nexusflow/nexusraven-v2-function-calling-benchmark-657a597fb84dbe7a09ebfc3e>.

    Args:
        data_dir (str): The directory to save the data.
        save_to (str): The file to save the results.
        processes (int, optional): The number of processes to use.
            (default: :obj:`1`)
    """
    DEFAULT_DATASET_NAME = "Nexusflow/VirusTotalBenchmark"
    DEFAULT_SPLIT = "train"

    def __init__(
        self,
        save_to: Optional[str] = None,
        processes: int = 1,
    ):
        r"""Initialize the Nexus Function Calling benchmark.

        Args:
            data_dir (str): The directory to save the data.
            save_to (Optional[str]): The file to save the results. If None,
                uses default 'NexusResults.jsonl'. (default: :obj:`None`)
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        self.save_to = save_to or "NexusResults.jsonl"
        self.num_processes = processes
        self.dataset: Optional[Dataset] = None
        self.dataset_name: Optional[str] = None
        self.split: Optional[str] = None

        self._agent: Optional[ChatAgent] = None
        super().__init__("nexus", "", save_to, processes)
    
    def download(self) -> None:
        r"""Download the RAGBench dataset using stored configuration.

        Raises:
            ValueError: If dataset configuration is not set via load().
            Exception: If dataset download fails.
        """
        if self.dataset_name is None:
            raise ValueError(
                "Dataset configuration not set. Please call load() first."
            )

        try:
            self.dataset = load_dataset(
                self.dataset_name, split=self.split
            )
        except Exception as e:
            logger.error(f"Failed to download dataset: {e}")
            raise
    
    def load(
        self,
        name: str = DEFAULT_DATASET_NAME,
        split: Optional[str] = DEFAULT_SPLIT,
        force_download: bool = False,
    ) -> None:
        r"""Load the RAGBench dataset.

        Args:
            name (str): Dataset name/path.
            split (Optional[str]): Dataset split. Defaults to "train".
            force_download (bool): Whether to force re-download. Defaults to False.
        """
        self.dataset_name = name
        self.split = split

        if force_download or self.dataset is None:
            logger.info(
                "%s dataset: %s (split=%s)",
                "Force downloading" if force_download else "Loading",
                name,
                split,
            )
            self.download()
    
    def _construct_tool_descriptions(self) -> str:
        r"""Construct tool descriptions from function definitions and
        descriptions."""
        tool_dataset_mapping = {
            "Nexusflow/NVDLibraryBenchmark": "CVECPE",
            "Nexusflow/VirusTotalBenchmark": "VirusTotal",
            "Nexusflow/PlacesAPIBenchmark": "Places",
            "Nexusflow/ClimateAPIBenchmark": "Climate",
            "Nexusflow/OTXAPIBenchmark": "OTX",
            "Nexusflow/CVECPEAPIBenchmark": "CVECPE_Multi (Nested)",
        }

        dataset = load_dataset(
            "Nexusflow/Function_Call_Definitions",
            name=tool_dataset_mapping[self.dataset_name],
        )["train"]

        # Generate the tool prompt
        tool_prompt = "".join(
            f"Function:\ndef {row['function_calls']}:\n"
            + "\"\"\"\n"
            + f"{row['descriptions']}\n"
            + "\"\"\"\n"
            for row in dataset
        )

        return tool_prompt

    def run(
        self,
        pipeline_template: ChatAgent,
    ) -> Dict[str, Any]:
        r"""Run the benchmark evaluation.

        Args:
            pipeline_template (ChatAgent): Chat agent for generating answers.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - total_samples: Total number of samples evaluated
                - correct: total correct calls
                - accuracy: accuracy score

        Raises:
            ValueError: If dataset is not loaded.
        """
        if self.dataset is None:
            raise ValueError(
                "Dataset not loaded. Please call load() before run()."
            )
        logger.info(
            f"Running Nexus Function Calling benchmark on {self.dataset_name} "
            f"with {self.num_processes} process(es)."
        )
        self._agent = pipeline_template
        tools = self._construct_tool_descriptions()

        # Clear the results file if it exists
        open(self.save_to, "w").close()

        results = self._process_sample(tools)

        total = len(results)
        correct = sum(r["result"] for r in results)

        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total,
        }

    def _process_sample(
        self,
        tools: str,
    ) -> List[Dict[str, Any]]:
        r"""Process samples sequentially.

        Args:
            tools: Tool descriptions.

        Returns:
            List of result dictionaries.
        """
        results = []
        for sample in tqdm(self.dataset, desc="Running"):
            prompt = construct_prompt(input=sample["Input"], tools=tools)
            ground_truth_call = sample["Output"]

            try:
                response = self._agent.step(prompt)
                agent_call = response.msgs[0].content

                if agent_call:
                    result = compare_function_calls(
                        agent_call=agent_call,
                        ground_truth_call=ground_truth_call,
                    )
                    result_dict = {
                        "input": sample["Input"],
                        "agent_call": agent_call,
                        "ground_truth_call": ground_truth_call,
                        "result": result,
                        "error": None,
                    }
                else:
                    result_dict = {
                        "input": sample["input"],
                        "agent_call": None,
                        "ground_truth_call": ground_truth_call,
                        "result": 0,
                        "error": "No response generated",
                    }
            except Exception as e:
                logger.warning(f"Error in processing task: {sample['Input']}")
                result_dict = {
                    "input": sample["Input"],
                    "agent_call": None,
                    "ground_truth_call": ground_truth_call,
                    "result": 0,
                    "error": str(e),
                }

            results.append(result_dict)
            self._agent.reset()

            save_to_jsonl(self.save_to, result_dict, mode="a")

        return results


def parse_function_call(
    call: str,
) -> Tuple[Optional[str], Optional[List[Any]], Optional[Dict[str, Any]]]:
    r"""Parse a function call string to extract the function name,
    positional arguments, and keyword arguments, including
    nested function calls.

    Args:
        call (str): A string in the format `func(arg1, arg2, kwarg=value)`.

    Returns:
        tuple: (function_name (str), positional_args (list),
        keyword_args (dict)) or (None, None, None).
    """

    def preprocess_input(call: str) -> str:
        r"""Remove formatting like code blocks and whitespace."""
        if call.strip().startswith("```python"):
            call = call.strip().removeprefix("```python").removesuffix("```")
        return textwrap.dedent(call).strip()

    def evaluate_arg(arg):
        r"""Recursively evaluate arguments, including nested calls."""
        if isinstance(arg, ast.Call):
            # Recursively parse nested calls
            func_name, args, kwargs = parse_function_call(ast.unparse(arg))
            return func_name, args, kwargs
        elif isinstance(
            arg, ast.Constant
        ):  # Handle literals like numbers, strings, etc.
            return arg.value
        elif isinstance(arg, ast.List):  # Handle list literals
            return [evaluate_arg(el) for el in arg.elts]
        elif isinstance(arg, ast.Dict):  # Handle dictionary literals
            return {
                evaluate_arg(k): evaluate_arg(v)
                for k, v in zip(arg.keys, arg.values)
            }
        elif isinstance(arg, ast.Tuple):  # Handle tuple literals
            return tuple(evaluate_arg(el) for el in arg.elts)
        else:
            return ast.literal_eval(arg)  # Safely evaluate other types

    call = preprocess_input(call)
    parsed_calls = []

    try:
        # Parse the string into an AST
        parsed_calls = call.split(";")
        for single_call in parsed_calls:
            tree = ast.parse(single_call, mode='eval')

            # Ensure it's a function call
            if isinstance(tree.body, ast.Call):
                # Extract function name
                if isinstance(
                    tree.body.func, ast.Name
                ):  # Simple function call
                    func_name = tree.body.func.id
                elif isinstance(
                    tree.body.func, ast.Attribute
                ):  # Attribute function call
                    func_name = (
                        f"{tree.body.func.value.id}.{tree.body.func.attr}"  # type: ignore[attr-defined]
                    )
                else:
                    raise ValueError(f"Unsupported function call: {call}")

                # Extract positional arguments
                args = [evaluate_arg(arg) for arg in tree.body.args]

                # Extract keyword arguments
                kwargs: Dict[str, Any] = {
                    kw.arg: evaluate_arg(kw.value)
                    for kw in tree.body.keywords
                    if kw.arg is not None
                }
                logger.info("Valid call.")
                return func_name, args, kwargs
        else:
            raise ValueError(f"Not a valid function call: {call}")
    except Exception as e:
        logger.info(f"Error parsing call: {call}, {e}")
        return None, None, None


def compare_function_calls(agent_call: str, ground_truth_call: str) -> bool:
    r"""Compare the function name and arguments of
    agent_call and ground_truth_call.
    Args:
        agent_call (str): Function call by agent.
        ground_truth_call (str): Ground truth function call.

    Returns:
        - `True` if the function names and arguments match.
        - `False` otherwise.
    """
    # Parse both calls
    agent_parsed = parse_function_call(agent_call)
    gt_parsed = parse_function_call(ground_truth_call)

    if agent_parsed and gt_parsed:
        return agent_parsed == gt_parsed
    else:
        return False