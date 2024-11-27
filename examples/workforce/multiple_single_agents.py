# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    FunctionTool,
    GoogleMapsToolkit,
    SearchToolkit,
    WeatherToolkit,
)
from camel.types import ModelPlatformType, ModelType


def main():
    search_toolkit = SearchToolkit()
    search_tools = [
        FunctionTool(search_toolkit.search_google),
        FunctionTool(search_toolkit.search_duckduckgo),
    ]

    # Set up web searching agent
    search_agent_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )
    search_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Web searching agent",
            content="You can search online for information",
        ),
        model=search_agent_model,
        tools=[*search_tools, *WeatherToolkit().get_tools()],
    )

    # Set up tour guide agent
    tour_guide_agent_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    tour_guide_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Tour guide",
            content="You are a tour guide",
        ),
        model=tour_guide_agent_model,
        tools=GoogleMapsToolkit().get_tools(),
    )

    # Set up traveler agent
    traveler_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Traveler",
            content="You can ask questions about your travel plans",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    workforce = Workforce('A travel group')

    workforce.add_single_agent_worker(
        "A tour guide",
        worker=tour_guide_agent,
    ).add_single_agent_worker(
        "A traveler", worker=traveler_agent
    ).add_single_agent_worker(
        "An agent who can do online searches", worker=search_agent
    )

    # specify the task to be solved
    human_task = Task(
        content=(
            "Plan a one-week trip to Paris, considering some historical places"
            " to visit and weather conditions."
        ),
        id='0',
    )

    task = workforce.process_task(human_task)

    print('Final Result of Original task:\n', task.result)


if __name__ == "__main__":
    main()
