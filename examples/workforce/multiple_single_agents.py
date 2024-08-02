# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import asyncio

from camel.agents.chat_agent import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.tasks.task import Task
from camel.toolkits import MAP_FUNCS, SEARCH_FUNCS, WEATHER_FUNCS
from camel.types import ModelPlatformType, ModelType
from camel.workforce.manager_node import ManagerNode
from camel.workforce.single_agent_node import SingleAgentNode
from camel.workforce.task_channel import TaskChannel


async def main():
    # Note that it is essential to instantiate the channel and pass it to each
    # workforce.
    public_channel = TaskChannel()

    # Set the tools for the tool_agent
    function_list = [
        *SEARCH_FUNCS,
        *WEATHER_FUNCS,
        *MAP_FUNCS,
    ]
    # Configure the model of tool_agent
    model_config_dict = ChatGPTConfig(
        tools=function_list,
        temperature=0.0,
    ).__dict__

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_3_5_TURBO,
        model_config_dict=model_config_dict,
    )

    # Set tool_agent
    tool_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling opertor",
            content="You are a helpful assistant",
        ),
        model=model,
        tools=function_list,
    )
    # Set tour_guide_agent
    tour_guide_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="tour guide",
            content="You have to lead everyone to have fun",
        )
    )
    # traveler_agent
    traveler_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Traveler",
            content="You can ask questions about your travel plans",
        )
    )

    # Wrap the single agent into the SingleAgentWorkforce
    tour_guide_workforce = SingleAgentNode(
        node_id='1',
        description='tour guide',
        worker=tour_guide_agent,
    )
    traveler_workforce = SingleAgentNode(
        node_id='2', description='Traveler', worker=traveler_agent
    )
    tool_workforce = SingleAgentNode(
        node_id='3',
        description='Tools(eg.weather tools) calling opertor',
        worker=tool_agent,
    )
    # Specify the task to be solved
    human_task = Task(
        content=(
            "Plan a Paris tour itinerary for today"
            "taking into account the weather now."
        ),
        id='0',
    )
    # create a InternalWorkforce to combine all SignleAgentWorkforces
    workforces = ManagerNode(
        workforce_id='0',
        description='A travel group',
        child_workforces=[
            tour_guide_workforce,
            traveler_workforce,
            tool_workforce,
        ],
        main_task=human_task,
        channel=public_channel,
    )
    # start InternalWorkforce and task
    workforces.start()
    # print('Final Result of Origin task:\n', human_task.result)


if __name__ == "__main__":
    asyncio.run(main())
