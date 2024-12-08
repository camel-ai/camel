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
import ast
import textwrap
import pandas as pd
from dataclasses import dataclass
from datasets import load_dataset
from typing import Any, Dict, List, Literal, Optional, Union

from tqdm import tqdm
from camel.agents import ChatAgent
from camel.tool_benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage

logger = logging.getLogger(__name__)

# Define the data class
@dataclass
class NexusSample:
    input: str
    output: str

dataset_mapping = {
            "NVDLibrary": "Nexusflow/NVDLibraryBenchmark",
            "VirusTotal": "Nexusflow/VirusTotalBenchmark",
            "PlacesAPI": "Nexusflow/PlacesAPIBenchmark",
            "ClimateAPI": "Nexusflow/ClimateAPIBenchmark",
            "OTX": "Nexusflow/OTXAPIBenchmark",
            "VirusTotal-NestedCalls": "Nexusflow/vt_multiapi",
            "VirusTotal-ParallelCalls": "Nexusflow/vt_multiapi",
            "NVDLibrary-NestedCalls": "Nexusflow/CVECPEAPIBenchmark"
        }

TOOL_CALLING_PROMPT = """
You are given multiple functions and a user query.

Please proceed with generating a function call for the function with the proper arguments that best answers the given prompt.

Respond with nothing but the function call ONLY, such that I can directly execute your function call without any post processing necessary from my end. Do not use variables. 
If there are more than two function calls, separate them with a semicolon (;).

{tools}

Question: {input}
"""

class NexusBenchmark(BaseBenchmark):
    r"""
    TODO: Write the docstring
    """

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        processes: int = 1,
    ):
        super().__init__("nexus", data_dir, save_to, processes)
        self._data: List[NexusSample]
    
    def download(self):
        r"""Download the Nexus Functional Calling Benchmark dataset."""
        from huggingface_hub import snapshot_download

        for dataset_name, repo_id in dataset_mapping.items():
            local_dir = self.data_dir / dataset_name
            snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                local_dir=local_dir,
                local_dir_use_symlinks=True
            )

    def load(self, dataset_name):
        # Mapping dataset names to their corresponding folder names
        
        if dataset_name not in dataset_mapping:
            raise ValueError(f"Dataset {dataset_name} is not recognized. Available datasets: {list(dataset_mapping.keys())}")
        
        # Get the directory for the dataset
        dataset_dir = self.data_dir / dataset_name
        if not dataset_dir.exists():
            raise FileNotFoundError(f"The dataset directory for {dataset_name} does not exist at {dataset_dir}. Please download it first.")
        
        # Load the dataset files
        dataset = []
        if dataset_name == "NVDLibrary-NestedCalls":
            for file_name in os.listdir(dataset_dir):
                file_path = dataset_dir / file_name
                if file_name.endswith(".csv"):
                    data = pd.read_csv(file_path)
                    for _, sample in data.iterrows():
                        dataset.append(NexusSample(sample["Input"], "".join(sample["Output"])))
        else:
            for file_name in os.listdir(dataset_dir / "data"):
                file_path = dataset_dir / "data" / file_name
                if file_name.endswith(".parquet"):
                    data = pd.read_parquet(file_path)
                    data.head()
                    for _, sample in data.iterrows():
                        if dataset_name == "NVDLibrary":
                            dataset.append(NexusSample(sample["Input"], sample["Output"].replace("r = nvdlib.", "")))
                        elif dataset_name == "VirusTotal":
                            dataset.append(NexusSample(sample["Input"], sample["Output"]))
                        elif dataset_name == "PlacesAPI":
                            dataset.append(NexusSample(sample["Input"], sample["Output"]))
                        elif dataset_name == "ClimateAPI":
                            dataset.append(NexusSample(sample["Input"], sample["Output"]))
                        elif dataset_name == "OTX":
                            dataset.append(NexusSample(sample["Input"], sample["Output"]))
                        elif dataset_name == "VirusTotal-NestedCalls":
                            if len(sample["fncall"]) == 1:
                                dataset.append(NexusSample(sample["generated_question"], "".join(sample["fncall"])))
                        elif dataset_name == "VirusTotal-ParallelCalls":
                            if len(sample["fncall"]) > 1:
                                dataset.append(NexusSample(sample["generated_question"], "; ".join(sample["fncall"])))
        
        self._data = dataset
        
    @property
    def train(self):
        raise NotImplementedError("Nexus Functional Calling has only a single 'train' set.")
    
    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        dataset: Union[int, List[int], Literal[
            "NVDLibrary",
            "VirusTotal",
            "OTX",
            "PlacesAPI",
            "ClimateAPI",
            "VirusTotal-Parallel Calls",
            "VirusTotal-Nested Calls",
            "NVDLibrary-Nested Calls"
        ]],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark
        """

        if dataset not in dataset_mapping:
            raise ValueError(f"Invalid value for dataset: {dataset}.")

        logger.info(f"Running Nexus Function Calling benchmark on {dataset}.")
        self.load(dataset)
        datas = self._data
        if randomize:
            random.shuffle(datas)
        if subset:
            datas = datas[:subset]
        logger.info(f"Number of tasks: {len(datas)}")
        self._results = []

        tools = construct_tool_descriptions(dataset_name=dataset)
        with open(self.save_to, "w") as f:
            for sample in tqdm(datas, desc="Running"):
                prompt = construct_prompt(input=sample.input, tools = tools)
                msg = BaseMessage.make_user_message(
                    role_name="User",
                    content=prompt
                )
                ground_truth_call = sample.output
                try:
                    response = agent.step(msg)
                    agent_call = response.msgs[0].content
                    if agent_call:
                        result = compare_function_calls(agent_call=agent_call, ground_truth_call=ground_truth_call)
                        self._results.append(
                            {
                                "input": sample.input,
                                "agent_call": agent_call,
                                "ground_truth_call": ground_truth_call,
                                "result": result,
                                "error": None,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error in processing task: {sample.input}")
                    self._results.append(
                        {
                            "input": sample.input,
                            "agent_call": None,
                            "ground_truth_call": ground_truth_call,
                            "result": 0,
                            "error": str(e)
                        }
                    )

                agent.reset()

                f.write(json.dumps(self._results[-1], indent=2) + "\n")
                f.flush()
            
        total = len(self._results)
        correct = sum(r["result"] for r in self._results)
        
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total,
            }


# Utility functions
@dataclass
class NexusTool:
    function_calls: str
    descriptions: str

def construct_tool_descriptions(dataset_name) -> str:
    if dataset_name == "NVDLibrary":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="CVECPE")["train"]
    elif dataset_name == "VirusTotal":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="VirusTotal")["train"]
    elif dataset_name == "PlacesAPI":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="Places")["train"]
    elif dataset_name == "ClimateAPI":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="Climate")["train"]
    elif dataset_name == "OTX":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="OTX")["train"]
    elif dataset_name == "VirusTotal-NestedCalls":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="VT_Multi (Nested)")["train"]
    elif dataset_name == "VirusTotal-ParallelCalls":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="VT_Multi (Parallel)")["train"]
    elif dataset_name == "NVDLibrary-NestedCalls":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="CVECPE_Multi (Nested)")["train"]

    tools = [NexusTool(tool["function_calls"], tool["descriptions"]) for tool in dataset]
    
    tool_prompt = ""
    for tool in tools:
        tool_prompt += f"Function:\ndef {tool.function_calls}:\n" + "\"\"\"\n" + f"{tool.descriptions}" + "\n\"\"\"\n"
        
    return tool_prompt

def construct_prompt(input, tools) -> str:
    return TOOL_CALLING_PROMPT.format(tools=tools, input=input)

def parse_function_call(call) -> tuple:
    """
    Parse a function call string and handle nested function calls in both positional and keyword arguments.
    Example input: "func1(arg1=func2(3, 4), arg2=func3(key=func4(5)))"
    Returns a tuple: (function_name, positional_arguments, keyword_arguments).
    """
    def preprocess_input(call: str) -> str:
        """Remove formatting like code blocks and whitespace."""
        if call.strip().startswith("```python"):
            call = call.strip().removeprefix("```python").removesuffix("```")
        return textwrap.dedent(call).strip()

    def evaluate_arg(arg):
        r"""Recursively evaluate arguments, including nested calls."""
        if isinstance(arg, ast.Call):
            # Recursively parse nested calls
            func_name, args, kwargs = parse_function_call(ast.unparse(arg))
            return func_name, args, kwargs
        elif isinstance(arg, ast.Constant):  # Handle literals like numbers, strings, etc.
            return arg.value
        elif isinstance(arg, ast.List):  # Handle list literals
            return [evaluate_arg(el) for el in arg.elts]
        elif isinstance(arg, ast.Dict):  # Handle dictionary literals
            return {evaluate_arg(k): evaluate_arg(v) for k, v in zip(arg.keys, arg.values)}
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
                if isinstance(tree.body.func, ast.Name):  # Simple function call
                    func_name = tree.body.func.id
                elif isinstance(tree.body.func, ast.Attribute):  # Attribute function call
                    func_name = f"{tree.body.func.value.id}.{tree.body.func.attr}"
                else:
                    raise ValueError(f"Unsupported function call: {call}")
                
                # Extract positional arguments
                args = [evaluate_arg(arg) for arg in tree.body.args]
                
                # Extract keyword arguments
                kwargs = {kw.arg: evaluate_arg(kw.value) for kw in tree.body.keywords}
                print("Valid call.")
                return func_name, args, kwargs
        else:
            raise ValueError(f"Not a valid function call: {call}")
    except Exception as e:
        print(f"Error parsing call: {call}, {e}")
        return None, None, None

def compare_function_calls(agent_call, ground_truth_call) -> bool:
    r"""
    Compare the function name and arguments of agent_call and ground_truth_call.
    Returns:
        - True if the function names and arguments match.
        - False otherwise.
    """
    # Parse both calls
    agent_parsed = parse_function_call(agent_call)
    gt_parsed = parse_function_call(ground_truth_call)

    if agent_parsed and gt_parsed:
        return agent_parsed == gt_parsed
    else:
        return False