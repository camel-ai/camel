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
from typing import Optional

from synthetic_datagen.base_generator import BaseDataGenerator
from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec
from synthetic_datagen.utils.instance_generator import (
    InstanceGenerator,
)
from synthetic_datagen.utils.instruction_curator import (
    InstructionCurator,
)
from synthetic_datagen.utils.instruction_generator import (
    InstructionGenerator,
)

logger = logging.getLogger(__name__)


class SelfInstructGenerator(BaseDataGenerator):
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

    def __init__(self, spec: Optional[SelfInstructSpec] = None):
        """
        Initialize the SelfInstructGenerator with the given specification.

        Args:
            spec (Optional[SelfInstructSpec]): Specification object
            for the generator. If not provided,
            a default SelfInstructSpec is used.
        """
        self.spec = spec or SelfInstructSpec()
        self.instruction_generator = InstructionGenerator(self.spec)
        self.instance_generator = InstanceGenerator(self.spec)
        self.curator = InstructionCurator(self.spec)

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
