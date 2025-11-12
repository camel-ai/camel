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
from camel.data_collectors import AlpacaDataCollector
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.types.enums import ModelPlatformType, ModelType


def test_alpaca_converter():
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling operator",
            content="You are a helpful assistant. ",
        ),
        model=model,
    )

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="When is the release date of the video game Portal?",
    )

    collector = AlpacaDataCollector().record(agent).start()

    _resp = agent.step(usr_msg)
    resp = collector.convert()

    assert (
        resp["instruction"]
        == "You are a helpful assistant. "
        + "When is the release date of the video game Portal?"
    )
    assert resp['input'] == ''
    assert resp['output'] != ''


def test_alpaca_llm_converter():
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling operator",
            content="You are a helpful assistant. ",
        ),
        model=model,
    )

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="When is the release date of the video game Portal?",
    )

    collector = AlpacaDataCollector().record(agent).start()

    _resp = agent.step(usr_msg)
    resp = collector.llm_convert()

    assert (
        resp["instruction"]
        == "You are a helpful assistant. "
        + "When is the release date of the video game Portal?"
    )
    assert isinstance(resp["input"], str)  # LLM may add clarifying questions
    assert resp["output"] != ""
