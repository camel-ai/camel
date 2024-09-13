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

from camel.agents.chat_agent import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.tasks.task import Task
from camel.toolkits import MathToolkit, SearchToolkit, WeatherToolkit
from camel.types import ModelPlatformType, ModelType
from camel.workforce.manager_node import ManagerNode
from camel.workforce.role_playing_node import RolePlayingNode
from camel.workforce.single_agent_node import SingleAgentNode
from camel.workforce.workforce import Workforce


def main():
    guide_sysmsg = BaseMessage.make_assistant_message(
        role_name="tour guide",
        content="You have to lead everyone to have fun",
    )

    planner_sysmsg = BaseMessage.make_assistant_message(
        role_name="planner",
        content="good at tour plan.",
    )

    guide_agent = ChatAgent(guide_sysmsg)
    planner_agent = ChatAgent(planner_sysmsg)

    guide_worker_node = SingleAgentNode('tour guide', guide_agent)
    planner_worker_node = SingleAgentNode('planner', planner_agent)

    tools_list = [
        *MathToolkit().get_tools(),
        *WeatherToolkit().get_tools(),
        *SearchToolkit().get_tools(),
    ]
    user_model_config = ChatGPTConfig(temperature=0.0)
    assistant_model_config = ChatGPTConfig(
        tools=tools_list,
        temperature=0.0,
    )
    model_platform = ModelPlatformType.OPENAI
    model_type = ModelType.GPT_4O_MINI
    assistant_role_name = "Searcher"
    user_role_name = "Professor"
    assistant_agent_kwargs = dict(
        model=ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=assistant_model_config.as_dict(),
        ),
        tools=tools_list,
    )
    user_agent_kwargs = dict(
        model=ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=user_model_config.as_dict(),
        ),
    )
    research_rp_worker_node = RolePlayingNode(
        'research Group',
        assistant_role_name,
        user_role_name,
        assistant_agent_kwargs,
        user_agent_kwargs,
        1,
    )

    human_task = Task(
        content="research history of Paris and plan a tour.",
        id='0',
    )

    root_node = ManagerNode(
        description='a travel group',
        children=[
            guide_worker_node,
            planner_worker_node,
            research_rp_worker_node,
        ],
    )

    workforce = Workforce(root_node)
    task = workforce.process_task(human_task)

    print('Final Result of Origin task:\n', task.result)


if __name__ == "__main__":
    main()
