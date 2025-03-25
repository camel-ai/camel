# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import os 
import json
import logging

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent
from camel.datagen.evol_instruct import EvolInstructPipeline
from camel.logger import enable_logging, set_log_level, get_logger

os.environ["CAMEL_LOGGING_DISABLED"] = "false" 


def main():
    """
    Example usage of EvolInstructPipeline with iterative and parallel evolution.
    """
    
    # Set the agent
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={
            "temperature": 0.7,
            "max_tokens": 2048,
        },
    )
    system_msg = "You are a creative agent for creating new prompts."
    agent = ChatAgent(system_msg, model=model)

    # Set the prompts
    prompts = json.load(open("input.json", "r", encoding="utf-8"))


    # Set the pipeline
    pipeline = EvolInstructPipeline(agent=agent)
    
    # Define evolution parameters
    num_evolutions = 4
    num_generations = 2
    keep_original = True
    scorer = "uniform"
    num_chunks = 1
    retry_limit = 3
    retry_delay = 30
    
    # Set the method for each evolution
    # (you can only just use strings not the dict)
    # (like 'in-depth', 'in-breadth', 'uniform' if you are lazy)
    method_dict = {
        0: 'in-breadth', 
        1: 'in-depth', 
        2: 'in-depth', 
        3: 'in-breadth'
    }  
    assert len(method_dict) == num_evolutions

    # Run the pipeline
    results = pipeline.generate(
        prompts=prompts,
        method=method_dict,
        num_generations=num_generations,
        num_evolutions=num_evolutions,
        keep_original=keep_original,
        num_chunks=num_chunks, 
        retry_limit=retry_limit,
        retry_delay=retry_delay,
    )
    
    # Save results
    with open('results.json', mode="w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)
    logger.critical("Results saved to 'results.json'.")


if __name__ == "__main__":
    enable_logging()  
    set_log_level(logging.CRITICAL)  
    logger = get_logger("evol-instruct")
    logger.critical("let's evolve some ideas.")
    
    main()
