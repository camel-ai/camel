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
from camel.toolkits import SearchToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # 1. Set up a Research agent with search tools
    search_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Research Specialist",
            content="You are a research specialist who excels at finding and "
            "gathering information from the web.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
        tools=[SearchToolkit().search_wiki],
    )

    # 2. Set up an Analyst agent
    analyst_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Business Analyst",
            content="You are an expert business analyst. Your job is "
            "to analyze research findings, identify key insights, "
            "opportunities, and challenges.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    # 3. Set up a Writer agent
    writer_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Report Writer",
            content="You are a professional report writer. You take "
            "analytical insights and synthesize them into a clear, "
            "concise, and well-structured final report.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    workforce = Workforce(
        'Business Analysis Team',
        graceful_shutdown_timeout=30.0,
    )

    workforce.add_single_agent_worker(
        "A researcher who can search online for information.",
        worker=search_agent,
    ).add_single_agent_worker(
        "An analyst who can process research findings.", worker=analyst_agent
    ).add_single_agent_worker(
        "A writer who can create a final report from the analysis.",
        worker=writer_agent,
    )

    # specify the task to be solved
    human_task = Task(
        content=(
            "Conduct a comprehensive market analysis for launching a new "
            "electric scooter in Berlin. The analysis should cover: "
            "1. Current market size and key competitors. "
            "2. Target audience and their preferences. "
            "3. Local regulations and potential challenges. "
            "Finally, synthesize all findings into a summary report."
        ),
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

    log_file_path = "multiple_single_agents_logs.json"
    print(f"\n--- Dumping Workforce Logs to {log_file_path} ---")
    workforce.dump_workforce_logs(log_file_path)
    print(f"Logs dumped. Please check the file: {log_file_path}")


if __name__ == "__main__":
    main()
