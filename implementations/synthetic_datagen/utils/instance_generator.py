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
from collections import OrderedDict
from typing import Dict, List

from tqdm import tqdm

from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec
from synthetic_datagen.self_instruct.templates import (
    input_first_template_for_gen,
)
from synthetic_datagen.utils.generate_utils import load_jsonl

logger = logging.getLogger(__name__)

INSTANCE_ATTRIBUTES = [
    "instruction",
    "raw_instances",
    "metadata",
    "most_similar",
    "avg_similarity_score",
]


class InstanceGenerator:
    """
    A class for generating instances based on given instructions using
    an AI agent system.

    This class takes a SelfInstructSpec object as input, which provides
    the necessary
    configuration for generating instances. It reads instructions from a
    file, generates instances for each instruction using an AI agent system,
    and writes the results to an output file.

    Attributes:
        agent_system: The AI agent system used for generating instances.
        instructions_out_dir: The directory containing the input
        instructions file.
        instances_out_dir: The directory where the generated instances
        will be saved.
    """

    def __init__(self, spec: SelfInstructSpec):
        """
        Initialize the InstanceGenerator with the given SelfInstructSpec.

        Args:
            spec (SelfInstructSpec): A specification object containing
            the necessary configuration for instance generation.
        """
        self.agent_system = spec.agent_system
        self.instructions_out_dir = spec.instructions_out_file
        self.instances_out_dir = spec.instances_out_file

    def generate(self):
        """
        Generate instances for all tasks in the input file and write them
        to the output file.

        This method reads tasks from the input file, generates instances
        for each task in batches, and writes the results to the output file.
        """
        tasks = load_jsonl(self.instructions_out_dir)
        total_tasks = len(tasks)

        with open(self.instances_out_dir, "w") as fout:
            with tqdm(total=total_tasks, desc="Generating instances") as pbar:
                for batch in self._batch_tasks(tasks, batch_size=10):
                    results = self._generate_instances_for_batch(batch)
                    for task, result in zip(batch, results):
                        task["instruction"] = task['instruction'].strip()
                        task["raw_instances"] = result.content
                        task = OrderedDict(
                            (k, task[k]) for k in INSTANCE_ATTRIBUTES
                        )
                        json.dump(task, fout, ensure_ascii=False)
                        fout.write("\n")
                    pbar.update(len(batch))

    def _batch_tasks(self, tasks: List[Dict], batch_size: int = 5):
        """
        Yield batches of tasks from the given list of tasks.

        Args:
            tasks (List[Dict]): A list of task dictionaries to be batched.
            batch_size (int, optional): The size of each batch. Defaults to 5.

        Yields:
            List[Dict]: A batch of tasks with the specified batch size.
        """
        for i in range(0, len(tasks), batch_size):
            yield tasks[i : i + batch_size]

    def _generate_instances_for_batch(self, batch: List[Dict]) -> List[str]:
        """
        Generate instances for a batch of tasks using the AI agent system.

        This method takes a batch of tasks, generates instances for each task
        using the AI agent system, and returns the results.

        Args:
            batch (List[Dict]): A list of task dictionaries to generate
            instances for.

        Returns:
            List[str]: A list of generated instances corresponding to the
            input tasks.
        """
        results = []
        with tqdm(
            total=len(batch),
            desc="Generating batch of instances using AI agent system",
        ) as pbar:
            for task in batch:
                prompt = (
                    f"{input_first_template_for_gen}"
                    f" {task['instruction'].strip()}\n"
                )
                result = self.agent_system.run(prompt)
                results.append(result)
            pbar.update(len(batch))

        return results
