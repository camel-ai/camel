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
import textwrap

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    r"""An example of showing how to use multi-hop tasks in a workforce."""
    # Define agents
    researcher_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Researcher",
            content=textwrap.dedent(
                """\
                You are a researcher who does research on a given topic.
                You must use the web search tool to find the information.
                """
            ),
        ),
        tools=[FunctionTool(SearchToolkit().search_duckduckgo)],
    )

    writer_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Writer",
            content=textwrap.dedent(
                """\
                You are a writer who writes a report 
                based on provided information.
                You must ensure the report is 
                well-structured and easy to read.
                """
            ),
        )
    )

    # Define model config for workforce
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create a workforce
    workforce = Workforce(
        "Research and Writing Team",
        coordinator_agent_kwargs=dict(model=model),
        task_agent_kwargs=dict(model=model),
    )

    # Add workers to the workforce
    researcher_worker = workforce.add_single_agent_worker(
        "Researcher Rachel, who does online searches.",
        worker=researcher_agent,
    )

    writer_worker = workforce.add_single_agent_worker(
        "Writer William, who drafts reports from research findings.",
        worker=writer_agent,
    )

    # Define a multi-hop task
    research_subtask = Task(
        content="Research the latest trends in large language models (LLMs).",
        assignee_id=researcher_worker.node_id,
    )

    writing_subtask = Task(
        content="Based on the research findings, write a one-paragraph "
        "summary of the current trends in LLMs.",
        assignee_id=writer_worker.node_id,
    )

    main_task = Task(
        content="Create a report on the latest trends in LLMs.",
        subtasks=[
            research_subtask,
            writing_subtask,
        ],
    )

    # Process the task
    result_task = workforce.process_task(main_task)

    # Print results
    print("------------------")
    if result_task.result:
        print(f"Main Task Result:\n{result_task.result}")
    else:
        print("Main task did not produce a result.")
    print("------------------")
    for i, subtask in enumerate(result_task.subtasks):
        print(f"Subtask {i + 1} Result:\n{subtask.result}")
        print("------------------")


if __name__ == "__main__":
    main()
