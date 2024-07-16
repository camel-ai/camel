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
from synthetic_datagen.evolve_instruct.evolve_instruct_generator import (
    EvolveInstructGenerator,
)
from synthetic_datagen.evolve_instruct.evolve_instruct_spec import (
    EvolveInstructSpec,
)
from synthetic_datagen.pipeline import ChatGPTPipeline
from synthetic_datagen.utils.seed_instruction import Instance, SeedInstruction


def main():
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument("--seed_file", type=str, default="")
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
            instruction="Is there anything I can eat for a breakfast that "
            "doesn't include eggs, yet includes protein, and has"
            " roughly 700-1000 calories?",
            instances=[
                Instance(
                    "",
                    "Yes, you can have 1 oatmeal banana protein shake and"
                    " 4 strips of bacon. The oatmeal banana protein shake may"
                    " contain 1/2 cup oatmeal, 60 grams whey protein powder,"
                    " 1/2 medium banana, 1tbsp flaxseed oil and 1/2 cup"
                    "water, totalling about 550 calories. "
                    "The 4 strips of bacon "
                    "contains about 200 calories.",
                )
            ],
            is_classification=False,
        ),
        SeedInstruction(
            id="seed_task_1",
            short_name="antonym_relation",
            instruction="What is the relation between the given pairs?",
            instances=[
                Instance(
                    "Night : Day :: Right : Left",
                    "The relation between the given pairs is "
                    "that they are opposites.",
                )
            ],
            is_classification=False,
        ),
        SeedInstruction(
            id="seed_task_2",
            short_name="one_sentence_description",
            instruction="Generate a one-sentence description for each"
            " of the following people.",
            instances=[
                Instance(
                    "- Brack Obama\n- Elon Musk\n- Taylor Swift",
                    "- Barack Hussein Obama II is an American politician"
                    " who served as the 44th president of the United States"
                    " from 2009 to 2017.\n- Elon Musk is the founder, CEO,"
                    " and chief engineer of SpaceX; angel investor, CEO and"
                    " product architect of Tesla, Inc.; founder of The Boring"
                    " Company; co-founder of Neuralink and OpenAI; president"
                    " of the Musk Foundation; and owner and CEO of Twitter,"
                    " Inc.\n- Taylor Alison Swift is an American"
                    " singer-songwriter.",
                )
            ],
            is_classification=False,
        ),
    ]

    spec.agent_system = SingleAgent()
    llm_pipeline = ChatGPTPipeline(args.openai_model)

    generator = EvolveInstructGenerator(
        llm_pipeline=llm_pipeline,
        seed_data=args.seed_file,
        column_names=args.column_names,
        num_rows=args.num_rows,
        min_len_chars=args.min_len_chars,
        max_len_chars=args.max_len_chars,
        verbose=True,
    )
    generator.run()


if __name__ == "__main__":
    main()
