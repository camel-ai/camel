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

from camel.agents import ReActAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType, RoleType


def main() -> None:
    # Create system message and initialize agent
    system_message = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content=(
            "You are a helpful math assistant that can perform calculations. "
            "Use the appropriate math functions to solve problems accurately."
        ),
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Initialize toolkit and agent
    math_tool = MathToolkit()
    agent = ReActAgent(
        system_message=system_message,
        tools=math_tool.get_tools(),
        model=model,
        max_steps=5,
    )

    # Example queries
    queries = [
        "What is 123.45 plus 678.90?",
        "Calculate 25 multiplied by 3.14, rounded to 2 decimal places",
        "Divide 1000 by 3 and round to the nearest whole number",
    ]

    # Process each query and print raw JSON response
    for query in queries:
        response = agent.step(query)
        print("JSON response:", response.info)
        print("-" * 50)


if __name__ == "__main__":
    main()

"""
JSON response: {
    'thought': 'I need to calculate the sum of 123.45 and 678.90.',
    'action': 'Finish(answer=802.35)',
    'observation': 'Task completed.'
}
--------------------------------------------------
JSON response: {
    'thought': 'I need to calculate 25 multiplied by 3.14 and round the result 
                to 2 decimal places.',
    'action': 'Finish(answer=78.50)', 
    'observation': 'Task completed.'
}
--------------------------------------------------
JSON response: {
    'thought': 'I need to divide 1000 by 3 and round the result to the nearest 
                whole number.',
    'action': 'Finish(answer=334)',
    'observation': 'Task completed.'
}
--------------------------------------------------
"""
