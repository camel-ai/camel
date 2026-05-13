# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import XquikToolkit
from camel.types import ModelPlatformType, ModelType


def main() -> None:
    r"""Run read-only X (Twitter) research with ChatAgent and XquikToolkit.

    Set ``XQUIK_API_KEY`` and your model provider credentials before running
    this example.
    """
    if not os.environ.get("XQUIK_API_KEY"):
        raise RuntimeError("Set XQUIK_API_KEY before running this example.")

    tools = XquikToolkit().get_tools()
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=(
            "You are a social research assistant. Use Xquik tools for "
            "read-only X/Twitter search, profile lookup, and trends. "
            "Summarize results concisely and include source URLs when present."
        ),
        model=model,
        tools=tools,
    )
    agent.reset()

    user_messages = [
        (
            "Search X for recent posts about CAMEL-AI and multi-agent "
            "frameworks. Return three concise findings."
        ),
        "Look up the X profile CamelAIOrg and summarize the public profile.",
        "Get the top five global X trends and group them by topic.",
    ]

    for user_message in user_messages:
        response = agent.step(user_message)
        print(f"User: {user_message}")
        print(f"Tool calls: {response.info.get('tool_calls', [])}")
        print(f"Agent: {response.msg.content}\n")


if __name__ == "__main__":
    main()
