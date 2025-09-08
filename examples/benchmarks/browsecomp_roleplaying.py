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
from camel.models.model_factory import ModelFactory
from camel.societies.role_playing import RolePlaying
from camel.types.enums import ModelPlatformType, ModelType, TaskType

if __name__ == '__main__':
    model_config = {
        "model_platform": ModelPlatformType.DEFAULT,
        "model_type": ModelType.DEFAULT,
    }

    model = ModelFactory.create(**model_config)
    summarize_agent = ChatAgent('You are a helpful assistant.', model=model)

    # Create a RolePlaying session, its task_prompt will be overwritten.
    role_play_session = RolePlaying(
        assistant_role_name="assistant",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="user",
        user_agent_kwargs=dict(model=model),
        task_prompt="Analyze web content and extract accurate information",
        with_task_specify=False,
        task_type=TaskType.AI_SOCIETY,
    )

    benchmark = BrowseCompBenchmark(
        "report_role_playing.html", num_examples=2, processes=2
    )

    benchmark.run(
        pipeline_template=role_play_session,
        roleplaying_summarizer=summarize_agent,
    )

    # Create a grader agent for validation
    grader_agent = ChatAgent(
        "You are a helpful assistant.",
        model=ModelFactory.create(**model_config),
    )

    # Validate the results
    benchmark.validate(grader=grader_agent)
