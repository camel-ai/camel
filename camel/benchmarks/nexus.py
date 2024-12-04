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
import pandas as pd
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union

from tqdm import tqdm
from .utils.nexus_utils import construct_tool_descriptions, construct_prompt, compare_function_calls
from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory

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

    def load(self, dataset_name, force_download=False):
        # Mapping dataset names to their corresponding folder names
        
        if dataset_name not in dataset_mapping:
            raise ValueError(f"Dataset {dataset_name} is not recognized. Available datasets: {list(dataset_mapping.keys())}")
        
        # Get the directory for the dataset
        dataset_dir = self.data_dir / dataset_name
        if not dataset_dir.exists():
            raise FileNotFoundError(f"The dataset directory for {dataset_name} does not exist at {dataset_dir}. Please download it first.")
        
        # Load the dataset files
        dataset = []
        if dataset_name == dataset_name == "NVDLibrary-NestedCalls":
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

        if dataset not in [
            "NVDLibrary",
            "VirusTotal",
            "OTX",
            "PlacesAPI",
            "ClimateAPI",
            "VirusTotal-ParallelCalls",
            "VirusTotal-NestedCalls",
            "NVDLibrary-NestedCalls"
        ]:
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
        agent = self._inject(agent)

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

                self._results[-1]["history"] = self._current_history
                self._current_history = []
                f.write(json.dumps(self._results[-1], indent=2) + "\n")
                f.flush()
            
        total = len(self._results)
        correct = sum(r["result"] for r in self._results)
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total,
            }
