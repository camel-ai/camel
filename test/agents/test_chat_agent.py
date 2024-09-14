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
import ast
import asyncio
from io import BytesIO
from typing import List
from unittest.mock import Mock

import pytest
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage
from PIL import Image
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.agents.chat_agent import FunctionCallingRecord
from camel.configs import ChatGPTConfig
from camel.generators import SystemMessageGenerator
from camel.memories import MemoryRecord
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.terminators import ResponseWordsTerminator
from camel.toolkits import (
    MathToolkit,
    OpenAIFunction,
    SearchToolkit,
)
from camel.types import (
    ChatCompletion,
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
    TaskType,
)
from camel.utils.async_func import sync_funcs_to_async

parametrize = pytest.mark.parametrize(
    'model',
    [
        ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
            model_config_dict=ChatGPTConfig().as_dict(),
        ),
        pytest.param(None, marks=pytest.mark.model_backend),
    ],
)


@parametrize
def test_chat_agent(model):
    model = model
    system_msg = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY
    ).from_dict(
        dict(assistant_role="doctor"),
        role_tuple=("doctor", RoleType.ASSISTANT),
    )
    assistant = ChatAgent(system_msg, model=model)

    assert str(assistant) == (
        "ChatAgent(doctor, " f"RoleType.ASSISTANT, {ModelType.GPT_4O_MINI})"
    )

    assistant.reset()
    user_msg = BaseMessage(
        role_name="Patient",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Hello!",
    )
    assistant_response = assistant.step(user_msg)

    assert isinstance(assistant_response.msgs, list)
    assert len(assistant_response.msgs) > 0
    assert isinstance(assistant_response.terminated, bool)
    assert assistant_response.terminated is False
    assert isinstance(assistant_response.info, dict)
    assert assistant_response.info['id'] is not None


def test_chat_agent_stored_messages():
    system_msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    assistant = ChatAgent(system_msg)

    expected_context = [system_msg.to_openai_system_message()]
    context, _ = assistant.memory.get_context()
    assert context == expected_context

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Tell me a joke.",
    )
    assistant.update_memory(user_msg, OpenAIBackendRole.USER)
    expected_context = [
        system_msg.to_openai_system_message(),
        user_msg.to_openai_user_message(),
    ]
    context, _ = assistant.memory.get_context()
    assert context == expected_context


@pytest.mark.model_backend
def test_chat_agent_step_with_structure_response():
    system_msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    assistant = ChatAgent(
        system_message=system_msg,
    )

    class JokeResponse(BaseModel):
        joke: str = Field(description="a joke")
        funny_level: str = Field(description="Funny level, from 1 to 10")

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Tell a jokes.",
    )

    response = assistant.step(user_msg, output_schema=JokeResponse)
    response_content_json = ast.literal_eval(response.msgs[0].content)
    joke_response_keys = set(
        JokeResponse.model_json_schema()["properties"].keys()
    )

    response_content_keys = set(response_content_json.keys())

    assert joke_response_keys.issubset(
        response_content_keys
    ), f"Missing keys: {joke_response_keys - response_content_keys}"

    for key in joke_response_keys:
        assert (
            key in response_content_json
        ), f"Key {key} not found in response content"


@pytest.mark.model_backend
def test_chat_agent_step_with_external_tools():
    internal_tools = SearchToolkit().get_tools()
    external_tools = MathToolkit().get_tools()
    tool_list = internal_tools + external_tools

    model_config_dict = ChatGPTConfig(
        tools=tool_list,
        temperature=0.0,
    ).as_dict()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=model_config_dict,
    )

    # Set external_tools
    external_tool_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling operator",
            content="You are a helpful assistant",
        ),
        model=model,
        tools=internal_tools,
        external_tools=external_tools,
    )

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="What's the result of the release year of Portal subtracted "
        "from the year that United States was founded?",
    )

    response = external_tool_agent.step(usr_msg)
    assert not response.msg.content

    external_tool_request = response.info["external_tool_request"]
    assert external_tool_request.function.name == "sub"


@pytest.mark.model_backend
def test_chat_agent_messages_window():
    system_msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    assistant = ChatAgent(
        system_message=system_msg,
        message_window_size=2,
    )

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Tell me a joke.",
    )

    assistant.memory.write_records(
        [
            MemoryRecord(
                message=user_msg,
                role_at_backend=OpenAIBackendRole.USER,
            )
            for _ in range(5)
        ]
    )
    openai_messages, _ = assistant.memory.get_context()
    assert len(openai_messages) == 2


@pytest.mark.model_backend
def test_chat_agent_step_exceed_token_number():
    system_msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    assistant = ChatAgent(
        system_message=system_msg,
        token_limit=1,
    )

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Tell me a joke.",
    )

    response = assistant.step(user_msg)
    assert len(response.msgs) == 0
    assert response.terminated


@pytest.mark.model_backend
@pytest.mark.parametrize('n', [1, 2, 3])
def test_chat_agent_multiple_return_messages(n):
    model_config = ChatGPTConfig(temperature=1.4, n=n)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=model_config.as_dict(),
    )
    system_msg = BaseMessage(
        "Assistant",
        RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a helpful assistant.",
    )
    assistant = ChatAgent(system_msg, model=model)
    assistant.reset()
    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Tell me a joke.",
    )
    assistant_response = assistant.step(user_msg)
    assert assistant_response.msgs is not None
    assert len(assistant_response.msgs) == n


@pytest.mark.model_backend
@pytest.mark.parametrize('n', [2])
def test_chat_agent_multiple_return_message_error(n):
    model_config = ChatGPTConfig(temperature=1.4, n=n)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=model_config.as_dict(),
    )
    system_msg = BaseMessage(
        "Assistant",
        RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a helpful assistant.",
    )

    assistant = ChatAgent(system_msg, model=model)
    assistant.reset()

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Tell me a joke.",
    )
    assistant_response = assistant.step(user_msg)

    with pytest.raises(
        RuntimeError,
        match=(
            "Property msg is only available " "for a single message in msgs."
        ),
    ):
        _ = assistant_response.msg


@pytest.mark.model_backend
def test_chat_agent_stream_output():
    system_msg = BaseMessage(
        "Assistant",
        RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a helpful assistant.",
    )
    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Tell me a joke.",
    )

    stream_model_config = ChatGPTConfig(temperature=0, n=2, stream=True)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=stream_model_config.as_dict(),
    )
    stream_assistant = ChatAgent(system_msg, model=model)
    stream_assistant.reset()
    stream_assistant_response = stream_assistant.step(user_msg)

    for msg in stream_assistant_response.msgs:
        assert len(msg.content) > 0

    stream_usage = stream_assistant_response.info["usage"]
    assert stream_usage["completion_tokens"] > 0
    assert stream_usage["prompt_tokens"] > 0
    assert (
        stream_usage["total_tokens"]
        == stream_usage["completion_tokens"] + stream_usage["prompt_tokens"]
    )


@pytest.mark.model_backend
def test_set_output_language():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    agent = ChatAgent(system_message=system_message)
    assert agent.output_language is None

    # Set the output language to "Arabic"
    output_language = "Arabic"
    agent.set_output_language(output_language)

    # Check if the output language is set correctly
    assert agent.output_language == output_language

    # Verify that the system message is updated with the new output language
    updated_system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant."
        "\nRegardless of the input language, you must output text in Arabic.",
    )
    assert agent.system_message.content == updated_system_message.content


@pytest.mark.model_backend
def test_set_multiple_output_language():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    agent = ChatAgent(system_message=system_message)

    # Verify that the length of the system message is kept constant even when
    # multiple set_output_language operations are called
    agent.set_output_language("Chinese")
    agent.set_output_language("English")
    agent.set_output_language("French")
    updated_system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant."
        "\nRegardless of the input language, you must output text in French.",
    )
    assert agent.system_message.content == updated_system_message.content


@pytest.mark.model_backend
def test_function_enabled():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    agent_no_func = ChatAgent(system_message=system_message)
    agent_with_funcs = ChatAgent(
        system_message=system_message,
        model=model,
        tools=MathToolkit().get_tools(),
    )

    assert not agent_no_func.is_tools_added()
    assert agent_with_funcs.is_tools_added()


@pytest.mark.model_backend
def test_tool_calling_sync():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=MathToolkit().get_tools(),
    )

    ref_funcs = MathToolkit().get_tools()

    assert len(agent.func_dict) == len(ref_funcs)

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Calculate the result of: 2*8-10.",
    )
    agent_response = agent.step(user_msg)

    tool_calls: List[FunctionCallingRecord] = [
        call for call in agent_response.info['tool_calls']
    ]

    assert len(tool_calls) > 0
    assert str(tool_calls[0]).startswith("Function Execution")

    assert tool_calls[0].func_name == "mul"
    assert tool_calls[0].args == {"a": 2, "b": 8}
    assert tool_calls[0].result == 16


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_tool_calling_math_async():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    math_funcs = sync_funcs_to_async(MathToolkit().get_tools())
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=math_funcs,
    )

    ref_funcs = math_funcs

    assert len(agent.func_dict) == len(ref_funcs)

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Calculate the result of: 2*8-10.",
    )
    agent_response = await agent.step_async(user_msg)

    tool_calls = agent_response.info['tool_calls']

    assert tool_calls
    assert str(tool_calls[0]).startswith("Function Execution")

    assert tool_calls[0].func_name == "mul"
    assert tool_calls[0].args == {"a": 2, "b": 8}
    assert tool_calls[0].result == 16


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_tool_calling_async():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )

    async def async_sleep(second: int) -> int:
        r"""Async sleep function.

        Args:
            second (int): Number of seconds to sleep.

        Returns:
            integer: Number of seconds to sleep.
        """
        await asyncio.sleep(second)
        return second

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )

    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[OpenAIFunction(async_sleep)],
    )

    assert len(agent.func_dict) == 1

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Call the async sleep which is specified in function list with"
        " 1 second.",
    )
    agent_response = await agent.step_async(user_msg)

    tool_calls = agent_response.info['tool_calls']

    assert tool_calls
    assert str(tool_calls[0]).startswith("Function Execution")

    assert tool_calls[0].func_name == "async_sleep"
    assert tool_calls[0].args == {'second': 1}
    assert tool_calls[0].result == 1


def test_response_words_termination():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    response_terminator = ResponseWordsTerminator(words_dict=dict(goodbye=1))
    agent = ChatAgent(
        system_message=system_message,
        response_terminators=[response_terminator],
    )
    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Just say 'goodbye' once.",
    )
    agent_response = agent.step(user_msg)

    assert agent.terminated
    assert agent_response.terminated
    assert "goodbye" in agent_response.info['termination_reasons'][0]


def test_chat_agent_vision():
    system_message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a help assistant.",
    )
    model_config = ChatGPTConfig(temperature=0, max_tokens=200, stop="")
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=model_config.as_dict(),
    )
    agent = ChatAgent(
        system_message=system_message,
        model=model,
    )

    # Create an all blue PNG image:
    image = Image.new("RGB", (100, 100), "blue")
    image_list = []
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    image = Image.open(img_byte_arr)
    image_list.append(image)

    user_msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content="Is this image blue? Just answer yes or no.",
        image_list=image_list,
        image_detail="low",
    )
    # Mock the OpenAI model return value:
    agent.model_backend = Mock()
    agent.model_backend.run.return_value = ChatCompletion(
        id="mock_vision_id",
        choices=[
            Choice(
                finish_reason='stop',
                index=0,
                logprobs=None,
                message=ChatCompletionMessage(
                    content='Yes.',
                    role='assistant',
                    function_call=None,
                    tool_calls=None,
                ),
            )
        ],
        created=123456,
        model='gpt-4-turbo-2024-04-09',
        object='chat.completion',
        system_fingerprint='fp_5d12056990',
        usage=CompletionUsage(
            completion_tokens=2, prompt_tokens=113, total_tokens=115
        ),
    )

    agent_response = agent.step(user_msg)
    assert agent_response.msgs[0].content == "Yes."
