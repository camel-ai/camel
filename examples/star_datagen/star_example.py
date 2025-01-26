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

from camel.agents import ChatAgent
from camel.datagen.star import STaRPipeline
from camel.models.reward import NemotronRewardModel
from camel.types import ModelType


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    problems_path = os.path.join(current_dir, 'input_problems.json')
    output_path = os.path.join(current_dir, 'star_output.json')

    # Load problems from JSON file
    with open(problems_path, 'r') as f:
        problems_data = json.load(f)
        problems = problems_data.get('problems', [])

    # Initialize agent
    system_message = """You are an expert mathematical reasoner who excels at 
        solving problems step by step.
        For each problem:
        1. First understand what's being asked
        2. Break down the problem into parts
        3. Solve each part systematically
        4. Verify your solution
        5. Explain your reasoning clearly
        Always show your work and explain your thinking process."""

    agent = ChatAgent(system_message)

    # Initialize reward model (optional)
    reward_model = NemotronRewardModel(
        model_type=ModelType.NVIDIA_NEMOTRON_340B_REWARD,
        url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY"),
    )

    # Set score thresholds for different dimensions (optional)
    score_threshold = {
        "correctness": 1.6,
        "coherence": 3,
    }
    # Or use a single threshold for all dimensions:
    # score_threshold = 0.9

    # Create and run pipeline
    pipeline = STaRPipeline(
        agent=agent,
        problems=problems,  # Pass problems list directly
        output_path=output_path,
        max_iterations=1,
        score_threshold=score_threshold,
        reward_model=reward_model,  # To use a reward model (optional)
    )

    results = pipeline.generate()
    print(f"\nProcessed {len(results)} problems")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
