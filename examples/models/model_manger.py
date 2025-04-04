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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Use two different models for ModelManager

model1 = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="grok-beta",
    api_key="xai-...",
    url="https://api.x.ai/v1",
    model_config_dict={"max_tokens": 2000},
)

model2 = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0.4},
)

assistant_sys_msg = "Testing two models in ModelManager"

agent = ChatAgent(
    assistant_sys_msg,
    model=[model1, model2],
    scheduling_strategy="random_model",
)

# scheduling_strategy can be one of
# "round_robin, "always_first", "random_model"


# For using a custom scheduling_strategy. After ChatAgent initialization,
# custom callable need to be provided to agent.add_strategy method


def custom_strategy(self):
    r"""Custom strategy implementation."""
    return self.models[-1]


agent.add_model_scheduling_strategy("custom", custom_strategy)


user_msg = """What is the meaning of life, the universe, and everything?"""

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)


# Creating a model instance by loading model configs from a JSON file.
model_inst_from_json = ModelFactory.create_from_json(
    "config_files/config.json"
)

# Using the same system message and user message.
agent_1 = ChatAgent(
    system_message=assistant_sys_msg, model=model_inst_from_json
)

agent_1_response = agent.step(user_msg)
print(agent_1_response.msg.content)


# Creating a model instance by loading model configs from a YAML file.
model_inst_from_yaml = ModelFactory.create_from_yaml(
    "config_files/config.yaml"
)

agent_2 = ChatAgent(
    system_message=assistant_sys_msg, model=model_inst_from_yaml
)

agent_2_response = agent_2.step(user_msg)
print(agent_2_response.msg.content)


"""
===============================================================================
The phrase "the meaning of life, the universe, and everything" is famously 
associated with Douglas Adams' science fiction series "The Hitchhiker's Guide 
to the Galaxy." In the story, a group of hyper-intelligent beings builds a 
supercomputer named Deep Thought to calculate the answer to the ultimate 
question of life, the universe, and everything. After much contemplation, the 
computer reveals that the answer is simply the number 42, though the actual 
question remains unknown. 

This has led to various interpretations and discussions about the nature of 
existence, purpose, and the search for meaning in life. Ultimately, the 
meaning of life can vary greatly from person to person, shaped by individual 
beliefs, experiences, and values.
===============================================================================
"""
