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


from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import GoogleMapsToolkit, SearchToolkit, WeatherToolkit
from camel.types import ModelPlatformType, ModelType


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

    function_list = [
        *SearchToolkit().get_tools(),
        *WeatherToolkit().get_tools(),
        *GoogleMapsToolkit().get_tools(),
    ]

    model_platform = ModelPlatformType.DEFAULT
    model_type = ModelType.DEFAULT
    assistant_role_name = "Searcher"
    user_role_name = "Professor"
    assistant_agent_kwargs = dict(
        model=ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
        ),
        tools=function_list,
    )
    user_agent_kwargs = dict(
        model=ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
        ),
    )

    workforce = Workforce('a travel group')
    workforce.add_role_playing_worker(
        description='research Group',
        assistant_role_name=assistant_role_name,
        user_role_name=user_role_name,
        assistant_agent_kwargs=assistant_agent_kwargs,
        user_agent_kwargs=user_agent_kwargs,
        summarize_agent_kwargs={},
        chat_turn_limit=1,
    ).add_single_agent_worker(
        'tour guide', guide_agent
    ).add_single_agent_worker('planner', planner_agent)

    human_task = Task(
        content="research history of Paris and plan a tour.",
        id='0',
    )
    workforce.process_task(human_task)

    # Test WorkforceLogger features
    print("\n--- Workforce Log Tree ---")
    print(workforce.get_workforce_log_tree())

    print("\n--- Workforce KPIs ---")
    kpis = workforce.get_workforce_kpis()
    for key, value in kpis.items():
        print(f"{key}: {value}")

    log_file_path = "role_playing_with_agents_logs.json"
    print(f"\n--- Dumping Workforce Logs to {log_file_path} ---")
    workforce.dump_workforce_logs(log_file_path)
    print(f"Logs dumped. Please check the file: {log_file_path}")


if __name__ == "__main__":
    main()
