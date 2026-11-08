# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.data_collectors import ShareGPTDataCollector
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import FunctionTool, MathToolkit
from camel.types import ModelPlatformType, ModelType


class _NoNetworkBackend(BaseModelBackend):
    r"""A backend stub so the collector can be exercised without API keys."""

    @property
    def token_counter(self):
        return None

    def _run(self, messages, response_format=None, tools=None):
        raise RuntimeError("no network access in this test")

    async def _arun(self, messages, response_format=None, tools=None):
        raise RuntimeError("no network access in this test")


def test_sharegpt_convert_omits_ensure_ascii_key():
    r"""convert() must not leak json.dumps kwargs into the record dict and
    must serialize tool schemas with ensure_ascii=False like the rest of
    the collector."""

    def get_release_date(game: str) -> str:
        r"""Return the release date of the 游戏 release."""
        return "October 9, 2007"

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling operator",
            content="You are a helpful assistant",
        ),
        model=_NoNetworkBackend(ModelType.GPT_4O_MINI, model_config_dict={}),
        tools=[FunctionTool(get_release_date)],
    )
    collector = ShareGPTDataCollector().record(agent)
    collector.step(
        role="user", name=agent.role_name, message="When is the release date?"
    )
    collector.step(
        role="assistant",
        name=agent.role_name,
        message="The release date is October 9, 2007.",
    )

    data = collector.convert()

    # json.dumps kwargs must not leak into the converted record.
    assert "ensure_ascii" not in data

    # Tool schemas are serialized with ensure_ascii=False, so non-ASCII
    # characters stay readable instead of being \uXXXX-escaped.
    assert "游戏" in data["tools"]


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
