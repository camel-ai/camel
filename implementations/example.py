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
from synthetic_datagen.agent_systems.single_agent import SingleAgent
from synthetic_datagen.method_factory import SyntheticDataGeneratorMethodType
from synthetic_datagen.pipeline import DataGeneratorPipeline
from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec
from synthetic_datagen.utils.seed_instruction import Instance, SeedInstruction


def main():
    spec = SelfInstructSpec()
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
    generator = DataGeneratorPipeline(
        spec,
        method_type=SyntheticDataGeneratorMethodType.SELFINSTRUCT,
    )
    generator.run_generate()
    generator.run_curate()
    generator.run_evaluate()


if __name__ == "__main__":
    main()
