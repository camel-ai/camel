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


import pytest
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)
from openai.types.completion_usage import CompletionUsage

from camel.configs import DeepSeekConfig
from camel.models import DeepSeekModel, ModelFactory
from camel.types import ChatCompletion, ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.DEEPSEEK_V4_FLASH,
        ModelType.DEEPSEEK_V4_PRO,
        ModelType.DEEPSEEK_CHAT,
        ModelType.DEEPSEEK_REASONER,
    ],
)
def test_deepseek_model(model_type):
    model_config_dict = DeepSeekConfig().as_dict()
    model = DeepSeekModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.DEEPSEEK_V4_FLASH,
        ModelType.DEEPSEEK_V4_PRO,
        ModelType.DEEPSEEK_CHAT,
        ModelType.DEEPSEEK_REASONER,
    ],
)
def test_deepseek_model_create(model_type: ModelType):
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=model_type,
        model_config_dict=DeepSeekConfig(temperature=1.3).as_dict(),
    )
    assert model.model_type == model_type


def test_deepseek_v4_model_types():
    assert ModelType.DEEPSEEK_V4_FLASH.is_deepseek
    assert ModelType.DEEPSEEK_V4_PRO.is_deepseek
    assert ModelType.DEEPSEEK_V4_FLASH.token_limit == 1_000_000
    assert ModelType.DEEPSEEK_V4_PRO.token_limit == 1_000_000


def test_deepseek_config_supports_thinking_options():
    config = DeepSeekConfig(
        reasoning_effort="high",
        thinking={"type": "enabled"},
        extra_body={"custom": True},
    ).as_dict()

    assert config["reasoning_effort"] == "high"
    assert config["thinking"] == {"type": "enabled"}
    assert config["extra_body"] == {"custom": True}


def test_deepseek_prepare_request_moves_thinking_to_extra_body():
    model = DeepSeekModel(
        ModelType.DEEPSEEK_V4_PRO,
        DeepSeekConfig(
            thinking={"type": "disabled"},
            reasoning_effort="high",
        ).as_dict(),
        api_key="test",
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_date",
                "parameters": {"type": "object", "properties": {}},
                "strict": True,
            },
        }
    ]

    request_config = model._prepare_request(
        messages=[{"role": "user", "content": "hello"}],
        tools=tools,
    )

    assert "thinking" not in request_config
    assert request_config["extra_body"]["thinking"] == {"type": "disabled"}
    assert request_config["reasoning_effort"] == "high"
    assert "strict" not in request_config["tools"][0]["function"]
    assert tools[0]["function"]["strict"] is True


def _make_chat_completion(
    message: ChatCompletionMessage,
    finish_reason: str,
) -> ChatCompletion:
    return ChatCompletion(
        id="mock_response_id",
        choices=[
            Choice(
                finish_reason=finish_reason,
                index=0,
                logprobs=None,
                message=message,
            )
        ],
        created=123456789,
        model="deepseek-v4-pro",
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=10,
            prompt_tokens=20,
            total_tokens=30,
        ),
    )


def test_deepseek_model_injects_tool_call_reasoning_content():
    model = DeepSeekModel(
        ModelType.DEEPSEEK_V4_PRO,
        DeepSeekConfig().as_dict(),
        api_key="test",
    )
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call_123",
        type="function",
        function=Function(name="get_date", arguments="{}"),
    )
    message = ChatCompletionMessage(
        content="",
        role="assistant",
        function_call=None,
        tool_calls=[tool_call],
    )
    message.reasoning_content = "Need the date before answering."

    model.postprocess_response(_make_chat_completion(message, "tool_calls"))
    messages = model.preprocess_messages(
        [
            {"role": "user", "content": "What is today's date?"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_date",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_123", "content": "2026"},
        ]
    )

    assert messages[1]["reasoning_content"] == (
        "Need the date before answering."
    )


def test_deepseek_model_injects_final_reasoning_after_tool_turn():
    model = DeepSeekModel(
        ModelType.DEEPSEEK_V4_PRO,
        DeepSeekConfig().as_dict(),
        api_key="test",
    )
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call_123",
        type="function",
        function=Function(name="get_date", arguments="{}"),
    )
    tool_message = ChatCompletionMessage(
        content="",
        role="assistant",
        function_call=None,
        tool_calls=[tool_call],
    )
    tool_message.reasoning_content = "Need the date before answering."
    model.postprocess_response(
        _make_chat_completion(tool_message, "tool_calls")
    )

    final_message = ChatCompletionMessage(
        content="I created the logs directory.",
        role="assistant",
        function_call=None,
        tool_calls=None,
    )
    final_message.reasoning_content = "The tool succeeded, so I can answer."
    model.postprocess_response(_make_chat_completion(final_message, "stop"))

    messages = model.preprocess_messages(
        [
            {"role": "user", "content": "Create logs"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_date",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_123", "content": "ok"},
            {
                "role": "assistant",
                "content": "I created the logs directory.",
            },
            {"role": "user", "content": "Create app.log"},
        ]
    )

    assert messages[1]["reasoning_content"] == (
        "Need the date before answering."
    )
    assert messages[3]["reasoning_content"] == (
        "The tool succeeded, so I can answer."
    )


def test_deepseek_chat_agent_preserves_reasoning_across_steps(monkeypatch):
    from camel.agents import ChatAgent
    from camel.toolkits import FunctionTool

    def get_date() -> str:
        r"""Get the current date."""
        return "2026-04-24"

    model = DeepSeekModel(
        ModelType.DEEPSEEK_V4_PRO,
        DeepSeekConfig().as_dict(),
        api_key="test",
    )

    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call_123",
        type="function",
        function=Function(name="get_date", arguments="{}"),
    )
    tool_message = ChatCompletionMessage(
        content="",
        role="assistant",
        function_call=None,
        tool_calls=[tool_call],
    )
    tool_message.reasoning_content = "Need a tool result."

    final_message = ChatCompletionMessage(
        content="The date is 2026-04-24.",
        role="assistant",
        function_call=None,
        tool_calls=None,
    )
    final_message.reasoning_content = "The tool returned the date."

    second_turn_message = ChatCompletionMessage(
        content="The log file has been created.",
        role="assistant",
        function_call=None,
        tool_calls=None,
    )
    second_turn_message.reasoning_content = "Use prior context and answer."

    responses = [
        _make_chat_completion(tool_message, "tool_calls"),
        _make_chat_completion(final_message, "stop"),
        _make_chat_completion(second_turn_message, "stop"),
    ]
    captured_messages = []

    def fake_call_client(call, *args, **kwargs):
        captured_messages.append(kwargs["messages"])
        return responses.pop(0)

    monkeypatch.setattr(model, "_call_client", fake_call_client)

    agent = ChatAgent(
        system_message="You can use tools.",
        model=model,
        tools=[FunctionTool(get_date)],
    )

    agent.step("What is today's date?")
    agent.step("Create a log file for that date.")

    second_step_messages = captured_messages[2]
    assistant_tool_message = next(
        message
        for message in second_step_messages
        if (
            message["role"] == "assistant"
            and message.get("tool_calls")
            and message["tool_calls"][0]["id"] == "call_123"
        )
    )
    assistant_final_message = next(
        message
        for message in second_step_messages
        if (
            message["role"] == "assistant"
            and message.get("content") == "The date is 2026-04-24."
        )
    )

    assert assistant_tool_message["reasoning_content"] == "Need a tool result."
    assert assistant_final_message["reasoning_content"] == (
        "The tool returned the date."
    )
