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
from camel.toolkits import MathToolkit
from camel.types import RoleType


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

    # Initialize toolkit and agent
    math_tool = MathToolkit()
    agent = ReActAgent(
        system_message=system_message,
        tools=[math_tool],
        max_steps=5,
    )

    # Example queries
    queries = [
        "What is 123.45 plus 678.90?",
        "Calculate 25 multiplied by 3.14, rounded to 2 decimal places",
        "Divide 1000 by 3 and round to the nearest whole number",
    ]

    # Process each query - simplified!
    for query in queries:
        response = agent.step(query)
        print("Agent response:", response.msgs[0].content)
        print("-" * 50)


if __name__ == "__main__":
    main()
