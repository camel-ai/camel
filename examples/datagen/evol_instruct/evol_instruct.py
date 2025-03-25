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

os.environ["CAMEL_LOGGING_DISABLED"] = "false"


def main():
    r"""Example usage of EvolInstructPipeline for iterative and parallel
    evolution.
    """
    # Load data
    file_path = "./examples/datagen/evol_instruct/input.json"
    prompts = json.loads(open(file_path, "r", encoding="utf-8").read())

    # Define parameters
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={"temperature": 0.7, "max_tokens": 4096},
    )
    agent = ChatAgent(model=model)
    num_generations = 2
    evol_spec = [
        "in-depth",
        "in-depth",
        "in-depth",
        "condense",
    ]

    # Initialize the data generation pipeline with the specified template
    pipeline = EvolInstructPipeline(
        agent=agent,
        templates=MathEvolInstructTemplates,
    )

    # Execute the data generation pipeline
    results = pipeline.generate(
        prompts=prompts,
        evolution_spec=evol_spec,
        num_iterations=4,
        num_generations=num_generations,
        scorer=MathScorer(),
    )

    # Save the generated results to a file
    results_path = "./examples/datagen/evol_instruct/results.json"
    with open(results_path, mode="w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    logger.info(f"Results saved to '{results_path}'.")


if __name__ == "__main__":
    enable_logging()
    set_log_level(logging.WARNING)
    logger = get_logger("evol-instruct")
    logger.info("Begin evolution.")
    main()
    logger.info("Evolution complete.")
