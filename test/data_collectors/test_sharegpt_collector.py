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
from camel.configs import ChatGPTConfig
from camel.data_collectors import ShareGPTDataCollector
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType


def test_sharegpt_converter():
    tool_list = MathToolkit().get_tools()

    model_config_dict = ChatGPTConfig(
        tools=tool_list,
    ).as_dict()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config_dict,
    )

    # Set external_tools
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling operator",
            content="You are a helpful assistant",
        ),
        model=model,
        tools=tool_list,
    )
    collector = ShareGPTDataCollector().record(agent).start()

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Call tools to calculate 17 * 19 = ?",
    )

    # This will directly run the internal tool
    _ = agent.step(usr_msg)
    resp = collector.convert()
    assert resp["system"] == "You are a helpful assistant"
    assert len(resp["conversations"]) in {3, 4}


def test_sharegpt_llm_converter():
    tool_list = MathToolkit().get_tools()

    model_config_dict = ChatGPTConfig(
        tools=tool_list,
    ).as_dict()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config_dict,
    )

    # Set external_tools
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling operator",
            content="You are a helpful assistant",
        ),
        model=model,
        tools=tool_list,
    )
    collector = ShareGPTDataCollector().record(agent).start()

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Call tools to calculate 17 * 19 = ?",
    )

    # This will directly run the internal tool
    _ = agent.step(usr_msg)
    resp = collector.llm_convert()
    assert resp["system"] == "You are a helpful assistant"
    assert any("323" in entry['value'] for entry in resp["conversations"])
