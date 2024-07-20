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
from camel.workforce.internal_workforce import InternalWorkforce
from camel.workforce.single_agent_workforce import SingleAgentWorforce
from camel.workforce.task_channel import TaskChannel


async def main():
    public_channel = TaskChannel()

    sys_msg_1 = BaseMessage.make_assistant_message(
        role_name="tour guide",
        content="You have to lead everyone to have fun",
    )
    sys_msg_tools = BaseMessage.make_assistant_message(
        role_name="Tools calling opertor",
        content="You are a helpful assistant",
    )
    sys_msg_3 = BaseMessage.make_assistant_message(
        role_name="Traveler",
        content="You can ask questions about your travel plans",
    )
    function_list = [
        *SEARCH_FUNCS,
        *WEATHER_FUNCS,
        *MAP_FUNCS,
    ]
    model_config_dict = ChatGPTConfig(
        tools=function_list,
        temperature=0.0,
    ).__dict__

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_3_5_TURBO,
        model_config_dict=model_config_dict,
    )

    # Set agent
    agent_2 = ChatAgent(
        system_message=sys_msg_tools,
        model=model,
        tools=function_list,
    )

    human_task = Task(
        content=(
            "Plan a Paris tour itinerary for today"
            "taking into account the weather now."
        ),
        id='0',
    )
    agent_1 = ChatAgent(sys_msg_1)
    agent_2 = ChatAgent(sys_msg_tools)
    agent_3 = ChatAgent(sys_msg_3)

    unit_workforce_1 = SingleAgentWorforce(
        '1', 'tour guide', agent_1, public_channel
    )
    unit_workforce_2 = SingleAgentWorforce(
        '2', 'Tools(eg.weather tools) calling opertor', agent_2, public_channel
    )
    unit_workforce_3 = SingleAgentWorforce(
        '3', 'Traveler', agent_3, public_channel
    )

    workforces = InternalWorkforce(
        workforce_id='0',
        description='a travel group',
        child_workforces=[
            unit_workforce_1,
            unit_workforce_2,
            unit_workforce_3,
        ],
        main_task=human_task,
        channel=public_channel,
    )
    await workforces.start()
    print('Final Result of Origin task:\n', human_task.result)


if __name__ == "__main__":
    asyncio.run(main())
