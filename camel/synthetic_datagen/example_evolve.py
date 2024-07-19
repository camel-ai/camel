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
import argparse

from synthetic_datagen.agent_systems.single_agent import SingleAgent
from synthetic_datagen.evolve_instruct.evolve_instruct_pipeline import (
    EvolveInstructGenerator,
)
from synthetic_datagen.evolve_instruct.evolve_instruct_spec import (
    EvolveInstructSpec,
)
from camel.synthetic_datagen.pipeline import ChatGPTPipeline
from synthetic_datagen.utils.seed_instruction import Instance, SeedInstruction


def main():
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument(
        "--seed_file",
        type=str,
        default="./data/seed_files/alpaca_data.json",
    )
    parser.add_argument("--column_names", nargs='+', default="instruction")
    parser.add_argument("--num_rows", type=int, default=5)
    parser.add_argument("--min_len_chars", type=int, default=32)
    parser.add_argument("--max_len_chars", type=int, default=2048)
    parser.add_argument("--openai_model", type=str, default="gpt-3.5-turbo")

    args = parser.parse_args()

    spec = EvolveInstructSpec()
    spec.seed_instructions = [
        SeedInstruction(
            id="seed_task_0",
            short_name="breakfast_suggestion",
            instruction="Give three tips for staying healthy.",
            instances=[
                Instance(
                    "",
                    "" "",
                )
            ],
            is_classification=False,
        ),
        SeedInstruction(
            id="seed_task_1",
            short_name="antonym_relation",
            instruction="Describe the structure of an atom.",
            instances=[
                Instance(
                    "",
                    "" "",
                )
            ],
            is_classification=False,
        ),
        SeedInstruction(
            id="seed_task_2",
            short_name="one_sentence_description",
            instruction="Identify the odd one out.",
            instances=[
                Instance(
                    "Twitter, Instagram, Telegram",
                    "Telegram",
                )
            ],
            is_classification=False,
        ),
    ]

    spec.agent_system = SingleAgent()
    llm_pipeline = ChatGPTPipeline(args.openai_model)

    spec.llm_pipeline = llm_pipeline
    spec.seed_data = args.seed_file
    spec.column_names = args.column_names
    spec.num_rows = args.num_rows
    spec.min_len_chars = args.min_len_chars
    spec.max_len_chars = args.max_len_chars
    spec.verbose = True

    generator = EvolveInstructGenerator(spec)
    generator.run()


if __name__ == "__main__":
    main()
