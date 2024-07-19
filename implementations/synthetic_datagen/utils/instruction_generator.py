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
import os
import random
from functools import partial
from typing import Any, Dict, List

import numpy as np
import tqdm

from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec
from synthetic_datagen.utils.generate_utils import (
    encode_prompt,
    post_process_agent_system_response,
    sample_machine_instructions,
)

logger = logging.getLogger(__name__)


class InstructionGenerator:
    """
    A class for generating and managing instructions for synthetic
    data generation.

    This class handles the process of generating new instructions based
    on seed instructions and previously generated machine instructions.
    It also manages the filtering and scoring
    of these instructions to ensure quality and uniqueness.

    Attributes:
        agent_system: The system used for generating new instructions.
        seed_instructions (List[SeedInstruction]): List of SeedInstruction
        representing seed tasks
        instructions_out_file (str): Directory where generated instructions
        will be saved.
        num_instructions_to_generate (int): Total number of instructions
        to generate.
        num_prompt_instructions (int): Number of instructions to use in
        each generation prompt.
        scorer: The scoring system used to evaluate instruction similarity.
    """

    def __init__(
        self,
        spec: SelfInstructSpec,
    ):
        """
        Initialize the InstructionGenerator with the given specification.

        Args:
            spec (SelfInstructSpec): Specification object containing
            configuration details.
        """
        self.spec = spec
        self.agent_system = spec.agent_system
        self.seed_instructions = [
            seed.instruction for seed in spec.seed_instructions
        ]
        self.instructions_out_file = spec.instructions_out_file
        self.num_instructions_to_generate = spec.num_instructions_to_generate
        self.num_prompt_instructions = spec.num_prompt_instructions
        self.scorer = spec.scorer

    def generate(self):
        """
        Generate new instructions and save them to the output directory.

        This method orchestrates the entire instruction generation process,
        including loading existing instructions, generating new ones,
        filtering them, and saving the results to a file.
        """
        os.makedirs(os.path.dirname(self.instructions_out_file), exist_ok=True)

        machine_instructions = self._load_machine_instructions()

        progress_bar = tqdm.tqdm(total=self.num_instructions_to_generate)
        if machine_instructions:
            progress_bar.update(len(machine_instructions))

        with open(self.instructions_out_file, "a") as fout:
            while (
                len(machine_instructions) < self.num_instructions_to_generate
            ):
                new_instructions = self._generate_new_instructions(
                    self.seed_instructions, machine_instructions
                )
                for inst, _metadata in new_instructions:
                    instruction_data = (
                        self._filter_synthetic_instruction_by_rouge_score(
                            inst, self.seed_instructions, machine_instructions
                        )
                    )
                    if instruction_data is None:
                        continue
                    json.dump(instruction_data, fout)
                    fout.write("\n")
                    progress_bar.update(1)
                    machine_instructions.append(inst)

    def _load_machine_instructions(self) -> List[str]:
        """
        Load existing machine-generated instructions from the output file.

        Returns:
            List[str]: A list of previously generated machine instructions.
        """
        if not os.path.exists(self.instructions_out_file):
            return []

        machine_instructions = []
        with open(self.instructions_out_file, "r") as fin:
            for line in fin:
                instruction_info = json.loads(line)
                machine_instructions.append(instruction_info["instruction"])
        logger.info(
            f"Loaded {len(machine_instructions)} "
            " machine-generated instructions"
        )

        return machine_instructions

    def _generate_new_instructions(
        self, seed_instructions: List[str], machine_instructions: List[str]
    ) -> List[tuple]:
        """
        Generate new instructions using the chat agent.

        This method creates prompts by combining seed and machine
        instructions,
        then uses these prompts to generate new instructions via
        the agent system.

        Args:
            seed_instructions (List[str]): List of seed instructions.
            machine_instructions (List[str]): List of previously
            generated machine instructions.

        Returns:
            List[tuple]: A list of tuples, each containing a new
            instruction and its metadata.
        """
        res = []
        logger.debug(f"Initialized empty result list: {res}")

        num_sampling_steps = self.num_instructions_to_generate - len(
            machine_instructions
        )
        logger.debug(f"Calculated num_sampling_steps: {num_sampling_steps}")

        logger.debug(f"Generating {num_sampling_steps} new instructions")

        for _ in range(num_sampling_steps):
            prompt_instructions = sample_machine_instructions(
                machine_instructions,
                similarities=None,
                n=self.num_prompt_instructions,
            )
            prompt_instructions += random.sample(
                seed_instructions,
                self.num_prompt_instructions - len(prompt_instructions),
            )

            random.shuffle(prompt_instructions)
            prompt = encode_prompt(prompt_instructions)
            result = self.agent_system.run(prompt)
            new_instructions = post_process_agent_system_response(
                result.content
            )
            for instruction in new_instructions:
                res.append((instruction, "NO METADATA"))

        return res

    def _filter_synthetic_instruction_by_rouge_score(
        self,
        instruction: str,
        seed_instructions: List[str],
        machine_instructions: List[str],
    ) -> Dict[str, Any]:
        """
        Filter and score a synthetic instruction based on its similarity
        to existing instructions.

        This method calculates ROUGE scores between the new instruction
        and all existing
        instructions, filtering out highly similar instructions and
        providing similarity metadata.

        Args:
            instruction (str): The new instruction to be evaluated.
            seed_instructions (List[str]): List of seed instructions.
            machine_instructions (List[str]): List of previously generated
            machine instructions.

        Returns:
            Dict[str, Any]: A dictionary containing the instruction,
            similarity scores, and metadata. Returns None if the instruction is
            too similar to existing ones.
        """
        rouge_scores = map(
            partial(self.scorer.score, instruction),
            seed_instructions + machine_instructions,
        )
        rouge_scores = [score["rougeL"].fmeasure for score in rouge_scores]
        if max(rouge_scores) > 0.7:
            return None
        all_instructions = seed_instructions + machine_instructions
        most_similar_instructions = {
            all_instructions[i]: rouge_scores[i]
            for i in np.argsort(rouge_scores)[-10:][::-1]
        }
        return {
            "instruction": instruction,
            "most_similar": most_similar_instructions,
            "avg_similarity_score": float(np.mean(rouge_scores)),
            "metadata": "NO METADATA",
        }
