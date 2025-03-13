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
from typing import Optional

from camel.agents import ReActAgent
from camel.messages import BaseMessage
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import RoleType


def search(query: str) -> Optional[str]:
    r"""Search for information using DuckDuckGo.

    Args:
        query: The search query string to look up information

    Returns:
        Optional[str]: The search results or None if no results found
    """
    toolkit = SearchToolkit()
    return toolkit.search_duckduckgo(query=query)


def main() -> None:
    # Create system message and initialize agent
    system_message = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content=(
            "You are a helpful assistant that can search information online. "
            "Use the search tool to find accurate information and "
            "provide detailed answers. Always verify information"
            "from multiple sources when possible before providing"
            "a final answer."
        ),
    )

    # Initialize search tool with proper schema
    search_tool = FunctionTool(
        func=search,  # Use our documented function
        synthesize_schema=True,  # Let the tool auto-generate proper schema
    )

    # Example queries that require search
    queries = [
        "What is the current population of Paris?",
        "Who won the Nobel Prize in Physics in 2024?",
    ]

    # Process each query
    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 50)

        # Create a fresh agent for each query to avoid state mixing
        agent = ReActAgent(
            system_message=system_message,
            tools=[search_tool],
            max_steps=5,
        )

        # Track steps
        step_num = 1
        response = agent.step(query)

        # Show intermediate steps from scratchpad
        for step in agent.scratchpad:
            print(f"Step {step_num}:")
            print(f"Thought: {step.get('Thought', '')}")
            print(f"Action: {step.get('Action', '')}")
            print(f"Observation: {step.get('Observation', '')}")
            print()
            step_num += 1

        # Show final response
        print("Final Response:")
        print("{")
        print(f"    \"thought\": \"{response.info['thought']}\",")
        print(f"    \"action\": \"{response.info['action']}\",")
        print(f"    \"observation\": \"{response.info['observation']}\"")
        print("}")
        print("-" * 50)


if __name__ == "__main__":
    main()
