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
from camel.configs import ChatGPTConfig
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.toolkits import SearxNGToolkit
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


def get_searxng_instance() -> Optional[str]:
    """Get SearxNG instance URL from environment variable."""
    instance_url = os.getenv('SEARXNG_URL')
    if not instance_url:
        logger.warning(
            "SEARXNG_URL environment variable not set. "
            "Please set it to your SearxNG instance URL."
        )
        return None
    return instance_url


def demonstrate_search(toolkit: SearxNGToolkit, agent: ChatAgent) -> None:
    """Demonstrate basic search functionality."""
    logger.info("Demonstrating basic search...")
    query = "CAMEL AI framework"
    response = agent.step(f"Search for information about {query}")
    logger.info(f"Search results for '{query}':")
    logger.info(str(response.info['tool_calls'])[:1000])


def demonstrate_category_search(
    toolkit: SearxNGToolkit, agent: ChatAgent
) -> None:
    """Demonstrate category-specific search."""
    logger.info("Demonstrating category-specific search...")
    query = "artificial intelligence"
    response = agent.step(
        f"Search for recent news about {query} in the news category"
    )
    logger.info(f"Category search results for '{query}':")
    logger.info(str(response.info['tool_calls'])[:1000])


def main():
    """Run the SearxNG toolkit examples."""
    instance_url = get_searxng_instance()
    if not instance_url:
        return

    # Initialize the toolkit
    toolkit = SearxNGToolkit(
        searxng_host=instance_url,
        language="en",
        categories=["general", "news"],
        time_range="month",
        safe_search=1,
    )

    # Initialize the model
    model_config = ChatGPTConfig(temperature=0.0).as_dict()
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config,
    )

    # Set up the agent
    system_message = (
        "You are a helpful assistant that can perform web searches using "
        "SearxNG. Use the provided tools to search for information and "
        "retrieve results."
    )
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=toolkit.get_tools(),
    )

    # Run demonstrations
    demonstrate_search(toolkit, agent)
    demonstrate_category_search(toolkit, agent)


if __name__ == "__main__":
    main()
