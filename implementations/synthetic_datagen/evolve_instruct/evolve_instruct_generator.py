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
import logging
from enum import Enum
from typing import Optional

from synthetic_datagen.base_generator import BaseDataGenerator
from synthetic_datagen.evolve_instruct.evolve_instruct_spec import (
    EvolveInstructSpec,
)
from synthetic_datagen.self_instruct.utils.instance_generator import (
    InstanceGenerator,
)
from synthetic_datagen.self_instruct.utils.instruction_curator import (
    InstructionCurator,
)
from synthetic_datagen.self_instruct.utils.instruction_generator import (
    InstructionGenerator,
)

logger = logging.getLogger(__name__)


class Mutation(Enum):
    FRESH_START = 0
    ADD_CONSTRAINTS = 1
    DEEPEN = 2
    CONCRETIZE = 3
    INCREASE_REASONING = 4
    COMPLICATE = 5
    SWITCH_TOPIC = 6


class EvolveInstructGenerator(BaseDataGenerator):
    """
    A generator for self-instructed synthetic data.

    This class orchestrates the process of generating synthetic
    instructions and instances,
    as well as curating the generated data. It uses separate components
    for instruction
    generation, instance generation, and curation.

    Attributes:
        spec (SelfInstructSpec): Specification object containing
        configuration details.
        instruction_generator (InstructionGenerator): Component for
        generating instructions.
        instance_generator (InstanceGenerator): Component for
        generating instances.
        curator (InstructionCurator): Component for curating generated data.
    """

    def __init__(self, spec: Optional[EvolveInstructSpec] = None):
        """
        Initialize the SelfInstructGenerator with the given specification.

        Args:
            spec (Optional[SelfInstructSpec]): Specification object
            for the generator. If not provided,
            a default SelfInstructSpec is used.
        """
        self.spec = spec or EvolveInstructSpec()
        self.instruction_generator = InstructionGenerator(self.spec)
        self.instance_generator = InstanceGenerator(self.spec)
        self.curator = InstructionCurator(self.spec)
        self.prompt_templates = dict()
        self.prompt_templates['base'] = ""
        write_in_korean = "Write in Korean."
        self.prompt_translate_into_korean = """
Translate #Given Prompt# to #New Prompt# in Korean."

#Given Prompt#:
<PROMPT>
"""

        self.prompt_templates[Mutation.FRESH_START] = (
            self.prompt_templates['base']
            + f"""Rewrite #Given Prompt# by switching the locale into \
            Korea and create #New Prompt#. {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.COMPLICATE] = (
            self.prompt_templates['base']
            + f"""Rewrite #Given Prompt# to make it slightly \
            more complicated, and create #New Prompt#. \
            {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.ADD_CONSTRAINTS] = (
            self.prompt_templates['base']
            + f"""Add a few more constraints or requirements \
                to #Given Prompt#, and create #New Prompt#. \
                {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

        self.prompt_templates[Mutation.DEEPEN] = (
            self.prompt_templates['base']
            + f"""Slightly increase the depth and breadth \
                of #Given Prompt#, and create #New Prompt#. \
                {write_in_korean}

#Given Prompt#:
<PROMPT>
"""
        )

    def generate(self):
        """
        Generate synthetic instructions and instances.

        This method triggers the generation of synthetic instructions
        followed by
        the generation of synthetic instances based on those instructions.
        """
        logging.info("Generating synthetic instructions...")
        self.instruction_generator.generate()
        logging.info("Generating synthetic instances...")
        self.instance_generator.generate()

    def curate(self):
        """
        Curate the generated synthetic data.

        This method initiates the curation process for the generated
        instructions
        and instances, typically involving filtering and quality checks.
        """
        self.curator.curate()

    def evaluate(self):
        raise RuntimeError(
            "Evaluation not implemented for SelfInstructGenerator yet "
            " - use an LLM to evaluate the quality of the generations."
        )
