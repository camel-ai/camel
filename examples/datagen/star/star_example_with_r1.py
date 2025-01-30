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
import os
import time

from camel.agents import ChatAgent
from camel.configs import DeepSeekConfig
from camel.datagen import STaRPipeline
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export DEEPSEEK_API_KEY=""
export GET_REASONING_CONTENT="true"
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_REASONER)

# from camel.models.reward import NemotronRewardModel


def main():
    start_time = time.time()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    problems_path = os.path.join(current_dir, 'math_500_dataset.json')
    output_path = os.path.join(current_dir, 'star_r1_output.json')

    # Load problems from JSON file
    with open(problems_path, 'r') as f:
        problems = json.load(f)

    # Initialize agent
    reason_agent_system_message = """Please reason step by step, and put your 
    final answer within \boxed{}."""
    evaluate_agent_system_message = """You are a highly critical teacher who 
    evaluates the student's answers with a meticulous and demanding approach.
    """
    reason_agent = ChatAgent(
        system_message=reason_agent_system_message, model=model
    )
    evaluate_agent = ChatAgent(system_message=evaluate_agent_system_message)

    # Initialize reward model (optional)
    # reward_model = NemotronRewardModel(
    #     model_type=ModelType.NVIDIA_NEMOTRON_340B_REWARD,
    #     url="https://integrate.api.nvidia.com/v1",
    #     api_key=os.environ.get("NVIDIA_API_KEY"),
    # )

    # # Set score thresholds for different dimensions (optional)
    # score_threshold = {
    #     "correctness": 1.6,
    #     "coherence": 3,
    # }
    # Or use a single threshold for all dimensions:
    score_threshold = 0.9

    # Create and run pipeline
    pipeline = STaRPipeline(
        reason_agent=reason_agent,
        evaluate_agent=evaluate_agent,
        problems=problems,  # Pass problems list directly
        output_path=output_path,
        max_iterations=0,
        score_threshold=score_threshold,
        # reward_model=reward_model,  # To use a reward model (optional)
    )

    results = pipeline.generate(rationalization=True)

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\nProcessed {len(results)} problems")
    print(f"Results saved to: {output_path}")
    print(f"Total execution time: {execution_time:.2f} seconds")


if __name__ == "__main__":
    main()
