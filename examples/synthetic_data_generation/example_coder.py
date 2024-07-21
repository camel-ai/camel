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

from camel.synthetic_datagen.agent_systems.eval_agent import (
    NemotronRewardEvalAgent,
)
from camel.synthetic_datagen.agent_systems.single_agent import SingleAgent
from camel.synthetic_datagen.method_factory import (
    SyntheticDataGeneratorMethodType,
)
from camel.synthetic_datagen.pipeline import DataGeneratorPipeline
from camel.synthetic_datagen.self_instruct.self_instruct_spec import (
    SelfInstructSpec,
)
from camel.synthetic_datagen.utils.seed_instruction import (
    Instance,
    SeedInstruction,
)

logging.basicConfig(level=logging.INFO)

# Examples from HuggingFace dataset: "iamtarun/python_code_instructions_18k_alpaca"
# https://huggingface.co/datasets/iamtarun/python_code_instructions_18k_alpaca

spec = SelfInstructSpec()
spec.seed_instructions = [
    SeedInstruction(
        instruction="",
        instances=[Instance("", "")],
    ),
    SeedInstruction(
        instruction="",
        instances=[Instance("", "")],
    ),
    SeedInstruction(
        instruction="",
        instances=[Instance("", "")],
    ),
    SeedInstruction(
        instruction="",
        instances=[Instance("", "")],
    ),
]

spec.agent_system = SingleAgent()
spec.eval_agent_system = NemotronRewardEvalAgent()
generator = DataGeneratorPipeline(
    spec, SyntheticDataGeneratorMethodType.SELFINSTRUCT
)

generator.run_generate()

generator.run_curate()

scores = generator.run_evaluate()
print(scores)
