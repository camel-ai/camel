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
from camel.types import (
    ModelType,
)

logging.basicConfig(level=logging.INFO)

# Examples from HuggingFace dataset:
# "iamtarun/python_code_instructions_18k_alpaca"
# https://huggingface.co/datasets/iamtarun/python_code_instructions_18k_alpaca


# Part 1: Self-Instruct 
spec = SelfInstructSpec()
seed_instructions = [
    SeedInstruction(
        instruction="Create a function to calculate the"
        " sum of a sequence of integers.",
        instances=[
            Instance(
                "[1, 2, 3, 4, 5]",
                "# Python code "
                "def sum_sequence(sequence):"
                " sum = 0 for num in sequence:"
                " sum += num return sum",
            )
        ],
    ),
    SeedInstruction(
        instruction="Generate a Python code for crawling "
        "a website for a specific type of data.",
        instances=[
            Instance(
                "website: www.example.com data to crawl: phone numbers",
                "import requests "
                "import re "
                "def crawl_website_for_phone_numbers(website):"
                " response = requests.get(website)"
                " phone_numbers = re.findall('\d{3}-\d{3}-\d{4}',"
                " response.text)"
                " return phone_numbers "
                "if __name__ == '__main__':"
                " print(crawl_website_for_phone_numbers('www.example.com'))",
            )
        ],
    ),
    SeedInstruction(
        instruction="Create a Python list comprehension to"
        " get the squared values of a list"
        " [1, 2, 3, 5, 8, 13].",
        instances=[Instance("", "[x*x for x in [1, 2, 3, 5, 8, 13]]")],
    ),
    SeedInstruction(
        instruction="Generate a python script to perform this action. "
        "Given a string, "
        "remove all the consecutive duplicates from the string.",
        instances=[
            Instance(
                "AAABBCCCD",
                "def remove_duplicates(string):"
                " result = ''"
                " prev = ''"
                " for char in string:"
                " if char != prev:"
                " result += char"
                " prev = char"
                " return result "
                "result = remove_duplicates('AAABBCCCD') "
                "print(result)",
            )
        ],
    ),
    SeedInstruction(
        instruction="Write a python script to generates random "
        "numbers between 0 and 9 that are divisible by 3.",
        instances=[
            Instance(
                "",
                "def generate_random_divisible_number():"
                " import random while True:"
                " # Generate a random number process = random.randint(0, 9)"
                " # Check if the number is divisible by 3 if process % 3 == 0:"
                " # If it is divisible, return it return process",
            )
        ],
    ),
]
spec.seed_instructions = seed_instructions
spec.agent_system = SingleAgent(model_type=ModelType.DeepSeek_code.value)
spec.eval_agent_system = NemotronRewardEvalAgent()
generator = DataGeneratorPipeline(
    spec, SyntheticDataGeneratorMethodType.SELFINSTRUCT
)

generator.run_generate()

generator.run_curate()

scores = generator.run_evaluate()
print(scores)


# Part 2: Evolve-Instruct 
spec = SelfInstructSpec()