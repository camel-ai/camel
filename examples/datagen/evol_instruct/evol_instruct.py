# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import logging
import os

from camel.agents import ChatAgent
from camel.datagen.evol_instruct import EvolInstructPipeline
from camel.datagen.evol_instruct.scorer import MathScorer
from camel.datagen.evol_instruct.templates import MathEvolInstructTemplates
from camel.logger import enable_logging, get_logger, set_log_level
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def save_results(results, path):
    # select the best result from the last generation for each prompt
    best_results = []
    for generations in results:
        # get the last generation
        last_generation_key = max(
            generations.keys()
        )  # Get the last iteration key
        last_generation = generations[
            last_generation_key
        ]  # Get the candidates from the last iteration

        # Find the candidate with highest total score
        best_result = max(
            last_generation,
            key=lambda x: sum(x["scores"].values()) if x["scores"] else 0,
        )
        best_results.append(best_result["instruction"])

    with open(path, mode="w", encoding="utf-8") as file:
        json.dump(best_results, file, indent=4, ensure_ascii=False)


def main():
    r"""Example usage of EvolInstructPipeline for iterative and parallel
    evolution.
    """
    # Load data
    file_path = "./examples/datagen/evol_instruct/input.json"
    output_dir = "./examples/datagen/evol_instruct"
    prompts = json.loads(open(file_path, "r", encoding="utf-8").read())

    # Initialize the model and agent
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0.7, "max_tokens": 4096},
    )
    agent = ChatAgent(model=model)

    # Initialize the data generation pipeline with the specified template
    pipeline = EvolInstructPipeline(
        agent=agent,
        templates=MathEvolInstructTemplates,
    )

    # Generate harder math problems
    num_generations = 3
    evol_spec = [
        "in-depth",
        "condense",
    ]

    # Execute the data generation pipeline
    results = pipeline.generate(
        prompts=prompts,
        evolution_spec=evol_spec,
        num_generations=num_generations,
        scorer=MathScorer(),
    )

    save_results(results, os.path.join(output_dir, "results_iter.json"))

    # Generate even harder math problems
    evol_spec = [
        "in-depth",
        "in-depth",
        "in-depth",
        "condense",
    ]

    # Execute the data generation pipeline
    results = pipeline.generate(
        prompts=prompts,
        evolution_spec=evol_spec,
        num_generations=num_generations,
        scorer=MathScorer(),
    )

    save_results(results, os.path.join(output_dir, "results_iter_harder.json"))


if __name__ == "__main__":
    enable_logging()
    set_log_level(logging.WARNING)
    logger = get_logger("evol-instruct")
    logger.info("Begin evolution.")
    main()
    logger.info("Evolution complete.")
