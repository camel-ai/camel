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
from camel.benchmarks.browsecomp import BrowseCompBenchmark
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.societies.workforce.workforce import Workforce
from camel.types.enums import ModelPlatformType, ModelType

if __name__ == '__main__':
    # Configure the model
    model_config = {
        "model_platform": ModelPlatformType.DEFAULT,
        "model_type": ModelType.DEFAULT,
    }

    # Create a model instance
    model = ModelFactory.create(**model_config)

    # Create a grader agent for validation
    grader_agent = ChatAgent(
        "You are a helpful assistant.",
        model=model,
    )

    formatter_agent = ChatAgent('You are a helpful assistant.', model=model)

    # Create specialized agents for the workforce
    web_researcher_sys_msg = BaseMessage.make_assistant_message(
        role_name="Web Researcher",
        content="""You are an expert at researching information on the web. 
You can search for and analyze web content to extract accurate information. 
You excel at understanding complex queries and finding precise answers.""",
    )

    # Create the agents with the model
    web_researcher_agent = ChatAgent(
        web_researcher_sys_msg,
        model=model,
    )

    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        "You are a helpful coordinator.", model=model
    )
    task_agent = ChatAgent("You are a helpful task planner.", model=model)
    new_worker_agent = ChatAgent("You are a helpful worker.", model=model)

    # Create a workforce for BrowseComp tasks
    workforce = Workforce(
        description="BrowseComp Research Team",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        new_worker_agent=new_worker_agent,
    )

    # Add workers to the workforce
    workforce.add_single_agent_worker(
        description="Web content researcher", worker=web_researcher_agent
    )

    # Add a role-playing worker for complex queries
    workforce.add_role_playing_worker(
        description="Collaborative research team",
        assistant_role_name="Research Assistant",
        user_role_name="Research Lead",
        assistant_agent_kwargs=dict(model=model),
        user_agent_kwargs=dict(model=model),
        summarize_agent_kwargs=dict(model=model),
        chat_turn_limit=3,
    )

    # Create the BrowseComp benchmark
    benchmark = BrowseCompBenchmark(
        "report_workforce.html", num_examples=3, processes=2
    )

    # Run the benchmark with the workforce
    print("Running BrowseComp benchmark with workforce...")
    benchmark.run(
        pipeline_template=workforce,
        task_json_formatter=formatter_agent,
    )

    # Validate the results
    print("Validating results...")
    benchmark.validate(grader=grader_agent)

    print("Benchmark completed. Results saved to report_workforce.html")
