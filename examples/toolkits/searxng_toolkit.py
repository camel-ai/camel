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

import os
from typing import Optional

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.toolkits import SearxNGToolkit
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


def get_searxng_instance() -> Optional[str]:
    r"""Get SearxNG instance URL from environment variable.

    Returns:
        Optional[str]: The SearxNG instance URL if set, None otherwise.
    """
    instance_url = os.getenv('SEARXNG_URL')
    if not instance_url:
        logger.warning(
            "SEARXNG_URL environment variable not set. "
            "Please set it to your SearxNG instance URL."
        )
    return instance_url


def main() -> None:
    r"""Run the SearxNG toolkit example."""
    # Get SearxNG instance URL
    instance_url = get_searxng_instance()
    if not instance_url:
        logger.error(
            "\nTo run this example:"
            "\n1. Find a SearxNG instance (self-host or use public instance)"
            "\n2. Set the SEARXNG_URL environment variable:"
            "\n   export SEARXNG_URL='https://your-searxng-instance.com'"
            "\n\nPublic instances can be found at: https://searx.space"
        )
        return

    # Initialize the toolkit
    searxng_toolkit = SearxNGToolkit(
        searxng_host=instance_url,
        language="en",
        categories=["general", "news"],
        time_range="month",
        safe_search=1,
    )

    # Initialize the model
    model = ModelFactory.create(
        model_type=ModelType.DEFAULT,
        model_platform=ModelPlatformType.DEFAULT,
    )

    # Create chat agent
    system_message = (
        "You are a helpful assistant that can search the web using SearxNG."
    )
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[*searxng_toolkit.get_tools()],
    )

    # Example search query
    query = "Tell me about the CAMEL AI framework"
    response = agent.step(query)

    # Print the response message content
    print("\nAgent Response:")
    print(response.msgs[0].content)

    # Print tool calls if needed
    print("\nTool Calls:")
    print(response.info['tool_calls'])


if __name__ == "__main__":
    main()
