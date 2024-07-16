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
import random
import re
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec
from synthetic_datagen.utils.generate_utils import load_jsonl

logger = logging.getLogger(__name__)


def parse_input_output(response_text: str):
    """
    Parse the input and output from a given response text.

    This function attempts to separate the input and output
    components of a response text.
    It handles cases where the text may or may not contain
    explicit "Input:" and "Output:" labels.

    Args:
        response_text (str): The text to be parsed, potentially
        containing input and output.

    Returns:
        tuple: A tuple containing two strings:
            - inst_input (str): The parsed input text, with any
            "Input:" label removed.
            - inst_output (str): The parsed output text.

    Note:
        If no "Output:" label is found, the entire text is treated as output
        and input is set to an empty string.
    """
    if re.findall(r"Output\s*\d*\s*:", response_text):
        inst_input = re.split(r"Output\s*\d*\s*:", response_text)[0].strip()
        inst_output = re.split(r"Output\s*\d*\s*:", response_text)[1].strip()
    else:
        inst_input = ""
        inst_output = response_text.strip()
    # to avoid the case multiple input/output pairs are generated
    if re.findall(r"Input\s*\d*\s*:", inst_output):
        inst_output = re.split(r"Input\s*\d*\s*:", inst_output)[0].strip()
    # remove the prefix "Input:" from the string
    inst_input = re.sub(r"^Input\s*\d*\s*:", "", inst_input).strip()
    return inst_input, inst_output


def filter_duplicate_instances(instances):
    """
    Filter out duplicate instances and instances with the same input but
    different outputs.

    This function removes exact duplicates and also filters out cases where
    multiple instances
    have the same non-empty input but different outputs, as these are
    considered inconsistent.

    Args:
        instances (list): A list of tuples, each containing
        (instruction, input, output).

    Returns:
        list: A filtered list of instances with duplicates and
        inconsistent cases removed.

    Note:
        If instances with the same input but different outputs
        are found, an empty list is returned.
    """
    # if the instances have same non-empty input, but different output,
    # we will not use such instances
    same_input_diff_output = False
    for i in range(1, len(instances)):
        for j in range(0, i):
            if instances[i][1] == "":
                continue
            if (
                instances[i][1] == instances[j][1]
                and instances[i][2] != instances[j][2]
            ):
                same_input_diff_output = True
                break
    if same_input_diff_output:
        return []

    # remove duplicate instances
    instances = list(set(instances))
    return instances


def filter_invalid_instances(instances):
    """
    Filter out invalid instances based on specific criteria.

    This function removes instances that are considered invalid, including:
    - Instances where input and output are identical
    - Instances with empty output
    - Instances where input or output ends with a colon (considered incomplete)

    Args:
        instances (list): A list of tuples, each containing
        (instruction, input, output).

    Returns:
        list: A filtered list of instances with invalid cases removed.
    """
    filtered_instances = []
    for instance in instances:
        # if input and output are the same, we will not use such instances
        if instance[1] == instance[2]:
            continue
        # if output is empty, we will not use such instances
        if instance[2] == "":
            continue
        # if input or output ends with a colon, these are usually
        # imcomplete generation. We will not use such instances
        if instance[1].strip().endswith(":") or instance[2].strip().endswith(
            ":"
        ):
            continue
        filtered_instances.append(instance)
    return filtered_instances


def parse_instances_for_generation_task(
    raw_text, instruction, response_metadata
):
    """
    Parse and extract instances from raw text for a generation task.

    This function processes raw text to extract multiple instances,
    handling different
    formatting cases (e.g., numbered examples, single input/output pairs).

    Args:
        raw_text (str): The raw text containing one or more instances.
        instruction (str): The instruction associated with these instances.
        response_metadata (Any): Metadata associated with the response
        (unused in this function).

    Returns:
        list: A list of tuples, each containing (instruction, input, output)
        for valid instances.

    Note:
        The function applies filtering to remove invalid and duplicate
        instances.
    """
    instances = []
    raw_text = raw_text.strip()
    if re.findall("Example\s?\d*\.?", raw_text):
        instance_texts = re.split(r"Example\s?\d*\.?", raw_text)
        instance_texts = [
            it.strip() for it in instance_texts if it.strip() != ""
        ]
        for instance_text in instance_texts:
            inst_input, inst_output = parse_input_output(instance_text)
            instances.append(
                (instruction.strip(), inst_input.strip(), inst_output.strip())
            )
    elif re.findall(r"Output\s*\d*\s*:", raw_text):
        # we assume only one input/output pair in this case
        inst_input, inst_output = parse_input_output(raw_text)
        instances.append(
            (instruction.strip(), inst_input.strip(), inst_output.strip())
        )
    else:
        return []

    instances = filter_invalid_instances(instances)
    instances = filter_duplicate_instances(instances)

    return instances


class InstructionCurator:
    """
    A class to curate and process instruction data for synthetic
    data generation.

    This class handles the loading, processing, and saving of instruction data,
    including both generated tasks and seed tasks.

    Attributes:
        spec (SelfInstructSpec): Specification object containing
        configuration details.
        synthetic_data_dir (Path): Directory for synthetic data output.
        seed_instructions (List[SeedInstruction]): List of SeedInstruction
        representing seed tasks
        num_instructions_to_generate (int): Number of instructions to generate.
        include_seed_tasks (bool): Flag to include seed tasks in
        the final output.
        all_instances_file (Path): Path to the file where all curated
        instances will be saved.
    """

    def __init__(self, spec: SelfInstructSpec):
        """
        Initialize the InstructionCurator with the given specification.

        Args:
            spec (SelfInstructSpec): Specification object containing
            configuration details.
        """
        self.spec = spec
        self.synthetic_data_dir = Path(spec.synthetic_data_dir)
        self.seed_instructions = spec.seed_instructions
        self.num_instructions_to_generate = spec.num_instructions_to_generate
        self.include_seed_tasks = spec.include_seed_tasks
        self.all_instances_file = (
            self.synthetic_data_dir / spec.CURATED_SYNTHETIC_DATA_FILE
        )

    def curate(self):
        """
        Curate the synthetic data by processing generated tasks and
        optionally including seed tasks.

        This method orchestrates the entire curation process,
        including loading tasks, processing instances, and saving the
        final curated data to a file.
        """

        logger.info("Curating synthetic data...")
        generated_tasks = self._load_generated_tasks()
        training_instances = self._curate_instances(generated_tasks)

        if self.include_seed_tasks:
            training_instances = self._include_seed_tasks(training_instances)

        out_file = self.synthetic_data_dir
        out_file = out_file / self.spec.CURATED_SYNTHETIC_DATA_FILE
        with open(
            out_file,
            "w",
        ) as fout:
            for instance in training_instances:
                json.dump(
                    {
                        "instruction": instance[0],
                        "input": instance[1],
                        "output": instance[2],
                    },
                    fout,
                )
                fout.write("\n")
        logger.info(
            f"Saved {len(training_instances)} instances to " f"{out_file}"
        )

    def _load_generated_tasks(self) -> List[Dict[str, Any]]:
        """
        Load the generated tasks from the specified file.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries,
            each representing a generated task.
        """
        generated_tasks = load_jsonl(self.spec.instances_out_dir)
        logger.info(f"Loaded {len(generated_tasks)} raw generated tasks")
        return generated_tasks

    def _curate_instances(
        self, generated_tasks: List[Dict[str, Any]]
    ) -> List[tuple]:
        """
        Process and curate instances from the generated tasks.

        This method parses the raw instances from each task, applies filtering,
        and limits the number of instances per task.

        Args:
            generated_tasks (List[Dict[str, Any]]): List of generated
            tasks to process.

        Returns:
            List[tuple]: A list of curated instances, each as a tuple of
            (instruction, input, output).
        """
        training_instances = []
        for task in tqdm(generated_tasks):
            instruction = task["instruction"]
            task_instances = parse_instances_for_generation_task(
                task["raw_instances"], instruction, task["metadata"]
            )
            task_instances = random.sample(
                task_instances, min(len(task_instances), 5)
            )
            if task_instances:
                training_instances.extend(task_instances)
        return training_instances

    def _include_seed_tasks(self, instances: List[tuple]) -> List[tuple]:
        """
        Include seed tasks in the list of curated instances.

        This method loads seed tasks from a file and adds them to the
        existing list of instances.

        Args:
            instances (List[tuple]): Existing list of curated instances.

        Returns:
            List[tuple]: Updated list of instances including seed tasks.
        """
        for seed in self.seed_instructions:
            for instance in seed.instances:
                instances.append(
                    (
                        seed.instruction,
                        instance.input,
                        instance.output,
                    )
                )
        logger.info(f"Included {len(self.seed_instructions)} seed tasks")
        return instances
