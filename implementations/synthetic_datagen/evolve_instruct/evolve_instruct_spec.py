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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

from rouge_score import rouge_scorer
from synthetic_datagen.agent_systems.base_agent_system import BaseAgentSystem
from synthetic_datagen.agent_systems.single_agent import SingleAgent

from implementations.synthetic_datagen.utils.seed_instruction import (
    SeedInstruction,
)


@dataclass
class EvolveInstructSpec:
    """
    Specification for the Self-Instruct process of generating synthetic data.

    This dataclass encapsulates all the configuration parameters and file paths
    needed for the Self-Instruct algorithm, including agent system setup,
    input/output directories, and generation parameters.

    Attributes:
        scorer (Any): The scoring system used for evaluating
        generated instructions.
        agent_system (BaseAgentSystem): The agent system used for generation,
        default is SingleAgent.
        seed_instructions (List[SeedInstruction]): List of SeedInstruction
        representing seed tasks
        include_seed_tasks (bool): Whether to include seed tasks in the
        final output.
        synthetic_data_dir (str): Directory path for storing all synthetic
        data.
        num_prompt_instructions (int): Number of instructions to use in each
        generation prompt.
        num_instructions_to_generate (int): Number of instructions to
        generate.
        SYNTHETIC_INSTANCES_FILE (str): Filename for storing generated
        instances.
        SYNTHETIC_INSTRUCTIONS_FILE (str): Filename for storing
        generated instructions.
        CURATED_SYNTHETIC_DATA_FILE (str): Filename for storing
        curated synthetic data.

    Properties:
        instructions_out_dir (Path): Full path for the generated
        instructions file.
        instances_out_dir (Path): Full path for the generated
        instances file.

    Note:
        The default values provided are typical settings,
        but can be overridden when instantiating the class.
    """

    scorer: Any = field(
        default_factory=lambda: rouge_scorer.RougeScorer(
            ["rougeL"], use_stemmer=False
        )
    )
    agent_system: BaseAgentSystem = field(default_factory=SingleAgent)
    seed_instructions: List[SeedInstruction] = field(default=list)
    include_seed_tasks: bool = False
    synthetic_data_dir: str = Path("data/gpt4_generations/")
    num_prompt_instructions: int = 3
    num_instructions_to_generate: int = 20
    SYNTHETIC_INSTANCES_FILE: str = "machine_generated_instances.jsonl"
    SYNTHETIC_INSTRUCTIONS_FILE: str = "machine_generated_instructions.jsonl"
    CURATED_SYNTHETIC_DATA_FILE: str = "curated_synthetic_data.jsonl"

    @property
    def instructions_out_dir(self) -> Path:
        """Full path for the file storing generated instructions."""
        return self.synthetic_data_dir / self.SYNTHETIC_INSTRUCTIONS_FILE

    @property
    def instances_out_dir(self) -> Path:
        """Full path for the file storing generated instances."""
        return self.synthetic_data_dir / self.SYNTHETIC_INSTANCES_FILE
