"""Tests for ChatAgent max_tool_calls behavior."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.chat.chat_completion_message_function_tool_call import Function
from openai.types.completion_usage import CompletionUsage

from camel.agents import ChatAgent
from camel.models.base_model import BaseModelBackend
from camel.models.stub_model import StubTokenCounter
from camel.toolkits import FunctionTool
from camel.types import ModelType


class DummyToolModel(BaseModelBackend):
    """Minimal local model backend for deterministic ChatAgent tests.

    Mirrors the ``StubModel`` convention used elsewhere in the test suite:
    ``run``/``arun`` are mocked per-test with synthetic ``ChatCompletion``
    objects, and the token counter lazily falls back to the lightweight,
    offline ``StubTokenCounter`` so no network access or real tokenizer is
    required.
    """

    @property
    def token_counter(self):
        if not self._token_counter:
            self._token_counter = StubTokenCounter()
        return self._token_counter

    def _run(self, messages, response_format=None, tools=None):
        return self.run_response

    async def _arun(self, messages, response_format=None, tools=None):
        return self.run_response


def _make_chat_completion(
    response_id: str,
    message: ChatCompletionMessage,
    finish_reason: str,
) -> ChatCompletion:
    """Create a deterministic chat completion for tool-call tests."""
    return ChatCompletion(
        id=response_id,
        choices=[
            {
                "finish_reason": finish_reason,
                "index": 0,
                "message": message,
            }
        ],
        created=1730753000,
        model="test-model",
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=10,
            prompt_tokens=20,
            total_tokens=30,
        ),
    )


def _make_tool_calls_message(calls, content=None):
    """Build a ``ChatCompletionMessage`` requesting the given tool calls.

    Args:
        calls: An iterable of ``(tool_call_id, tool_name)`` pairs. Each
            call is issued with empty ``{}`` arguments.
        content: Optional assistant text content alongside the tool calls.
    """
    return ChatCompletionMessage(
        content=content,
        role="assistant",
        function_call=None,
        tool_calls=[
            ChatCompletionMessageFunctionToolCall(
                id=call_id,
                function=Function(arguments="{}", name=name),
                type="function",
            )
            for call_id, name in calls
        ],
    )


def _final_text_message(text: str = "Done.") -> ChatCompletionMessage:
    """Build a plain assistant text response with no tool calls."""
    return ChatCompletionMessage(
        content=text,
        role="assistant",
        function_call=None,
        tool_calls=None,
    )


def test_chat_agent_max_tool_calls_limits_tool_execution():
    """Limit actual tool executions within a single step."""
    tool_a_calls = []
    tool_b_calls = []

    def tool_a() -> str:
        tool_a_calls.append("called")
        return "tool A result"

    def tool_b() -> str:
        tool_b_calls.append("called")
        return "tool B result"

    model = DummyToolModel(ModelType.STUB)

    tool_call_response = _make_chat_completion(
        "mock_tool_limit_1",
        ChatCompletionMessage(
            content=None,
            role="assistant",
            function_call=None,
            tool_calls=[
                ChatCompletionMessageFunctionToolCall(
                    id="call_tool_a",
                    function=Function(
                        arguments="{}",
                        name="tool_a",
                    ),
                    type="function",
                ),
                ChatCompletionMessageFunctionToolCall(
                    id="call_tool_b",
                    function=Function(
                        arguments="{}",
                        name="tool_b",
                    ),
                    type="function",
                ),
            ],
        ),
        "tool_calls",
    )

    final_response = _make_chat_completion(
        "mock_tool_limit_2",
        ChatCompletionMessage(
            content="Done.",
            role="assistant",
            function_call=None,
            tool_calls=None,
        ),
        "stop",
    )

    model.run = MagicMock(
        side_effect=[tool_call_response, final_response]
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_tool_calls=1,
        tools=[
            FunctionTool(tool_a),
            FunctionTool(tool_b),
        ],
    )

    response = agent.step("Run both tools.")

    assert tool_a_calls == ["called"]
    assert tool_b_calls == []
    assert response.msg.content == "Done."


def test_max_tool_calls_resets_between_steps():
    """The tool-call budget is per-step and resets automatically at the
    start of every new step() call."""
    calls = []

    def tool() -> str:
        """A simple tool."""
        calls.append("called")
        return "ok"

    model = DummyToolModel(ModelType.STUB)

    def tool_call_response(call_id, resp_id):
        return _make_chat_completion(
            resp_id,
            _make_tool_calls_message([(call_id, "tool")]),
            "tool_calls",
        )

    final_response = _make_chat_completion(
        "resp_final", _final_text_message(), "stop"
    )

    # Step 1 consumes the budget of 1; step 2 should be able to consume
    # one tool call again since the counter resets per step.
    model.run = MagicMock(
        side_effect=[
            tool_call_response("call_1", "resp_1"),
            final_response,
            tool_call_response("call_2", "resp_2"),
            final_response,
        ]
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_tool_calls=1,
        tools=[FunctionTool(tool)],
    )

    first = agent.step("Run the tool.")
    assert calls == ["called"]
    assert first.msg.content == "Done."

    second = agent.step("Run the tool again.")
    assert calls == ["called", "called"]
    assert second.msg.content == "Done."


def test_max_tool_calls_partial_batch_rejects_remaining_calls():
    """A single model response requesting more tool calls than the
    remaining budget only executes calls up to that budget; the rest are
    rejected but still produce structurally valid tool-result messages."""
    executed = []

    def _make_tool(name):
        def _tool() -> str:
            executed.append(name)
            return f"{name} result"

        _tool.__name__ = name
        _tool.__doc__ = f"Tool {name}."
        return _tool

    tool_a = _make_tool("tool_a")
    tool_b = _make_tool("tool_b")
    tool_c = _make_tool("tool_c")
    tool_d = _make_tool("tool_d")

    model = DummyToolModel(ModelType.STUB)

    batch_response = _make_chat_completion(
        "resp_batch",
        _make_tool_calls_message(
            [
                ("call_a", "tool_a"),
                ("call_b", "tool_b"),
                ("call_c", "tool_c"),
                ("call_d", "tool_d"),
            ]
        ),
        "tool_calls",
    )
    final_response = _make_chat_completion(
        "resp_final", _final_text_message(), "stop"
    )

    model.run = MagicMock(side_effect=[batch_response, final_response])

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_tool_calls=2,
        tools=[
            FunctionTool(tool_a),
            FunctionTool(tool_b),
            FunctionTool(tool_c),
            FunctionTool(tool_d),
        ],
    )

    response = agent.step("Run all four tools.")

    # Only the first two calls (within the remaining budget) executed.
    assert executed == ["tool_a", "tool_b"]
    assert response.msg.content == "Done."

    # Every requested tool_call_id must have a matching tool-role result
    # message recorded, so the OpenAI-compatible message history stays
    # structurally valid even for rejected calls.
    openai_messages, _ = agent.memory.get_context()
    tool_result_ids = {
        message["tool_call_id"]
        for message in openai_messages
        if message.get("role") == "tool"
    }
    assert tool_result_ids == {"call_a", "call_b", "call_c", "call_d"}


def test_max_tool_calls_disables_tools_after_budget_exhausted():
    """Once the tool-call budget is exhausted, subsequent model calls
    within the same step no longer offer tools, allowing the model to
    produce a final textual response from the results already gathered."""

    def tool_a() -> str:
        """Tool A."""
        return "tool A result"

    def tool_b() -> str:
        """Tool B."""
        return "tool B result"

    model = DummyToolModel(ModelType.STUB)

    batch_response = _make_chat_completion(
        "resp_batch",
        _make_tool_calls_message([("call_a", "tool_a"), ("call_b", "tool_b")]),
        "tool_calls",
    )
    final_response = _make_chat_completion(
        "resp_final", _final_text_message(), "stop"
    )

    model.run = MagicMock(side_effect=[batch_response, final_response])

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_tool_calls=1,
        tools=[FunctionTool(tool_a), FunctionTool(tool_b)],
    )

    response = agent.step("Run both tools.")

    assert response.msg.content == "Done."
    assert model.run.call_count == 2

    # The tools argument is the 3rd positional argument passed to
    # BaseModelBackend.run(messages, response_format, tools).
    first_call_tools = model.run.call_args_list[0].args[2]
    second_call_tools = model.run.call_args_list[1].args[2]
    assert first_call_tools  # Tools were offered on the first call.
    assert not second_call_tools  # Withheld once the budget is exhausted.


def test_chat_agent_max_tool_calls_limits_tool_execution_async():
    """The max_tool_calls budget is enforced identically through
    astep()."""
    tool_a_calls = []
    tool_b_calls = []

    def tool_a() -> str:
        """Tool A."""
        tool_a_calls.append("called")
        return "tool A result"

    def tool_b() -> str:
        """Tool B."""
        tool_b_calls.append("called")
        return "tool B result"

    model = DummyToolModel(ModelType.STUB)

    tool_call_response = _make_chat_completion(
        "mock_async_tool_limit_1",
        _make_tool_calls_message(
            [("call_tool_a", "tool_a"), ("call_tool_b", "tool_b")]
        ),
        "tool_calls",
    )
    final_response = _make_chat_completion(
        "mock_async_tool_limit_2", _final_text_message(), "stop"
    )

    model.arun = AsyncMock(side_effect=[tool_call_response, final_response])

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_tool_calls=1,
        tools=[FunctionTool(tool_a), FunctionTool(tool_b)],
    )

    response = asyncio.run(agent.astep("Run both tools."))

    assert tool_a_calls == ["called"]
    assert tool_b_calls == []
    assert response.msg.content == "Done."


def test_clone_preserves_max_tool_calls():
    """ChatAgent.clone() preserves the configured max_tool_calls value."""
    model = DummyToolModel(ModelType.STUB)
    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_tool_calls=3,
    )

    cloned = agent.clone()

    assert cloned.max_tool_calls == 3
    assert cloned.max_tool_calls == agent.max_tool_calls


@pytest.mark.parametrize("value", [None, 1, 2, 100])
def test_max_tool_calls_accepts_valid_values(value):
    """None and any positive integer are accepted."""
    model = DummyToolModel(ModelType.STUB)
    agent = ChatAgent(model=model, max_tool_calls=value)
    assert agent.max_tool_calls == value


@pytest.mark.parametrize("value", [0, -1, 1.5, "5", True, False])
def test_max_tool_calls_rejects_invalid_values(value):
    """Zero, negative numbers, non-integers, and bools are all rejected
    (bool is a subclass of int in Python, so it must be excluded
    explicitly)."""
    model = DummyToolModel(ModelType.STUB)
    with pytest.raises(ValueError):
        ChatAgent(model=model, max_tool_calls=value)


def test_max_tool_calls_independent_from_max_iteration():
    """max_tool_calls and max_iteration are independent controls: leaving
    max_iteration unset does not remove the tool-call budget, and the
    agent keeps iterating (with tools withheld) once that budget is
    exhausted until the model produces a final response."""

    def tool() -> str:
        """A simple tool."""
        return "ok"

    model = DummyToolModel(ModelType.STUB)

    responses = [
        _make_chat_completion(
            "resp_1",
            _make_tool_calls_message([("call_1", "tool")]),
            "tool_calls",
        ),
        _make_chat_completion(
            "resp_2",
            _make_tool_calls_message([("call_2", "tool")]),
            "tool_calls",
        ),
        _make_chat_completion("resp_3", _final_text_message(), "stop"),
    ]
    model.run = MagicMock(side_effect=responses)

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        max_iteration=None,
        max_tool_calls=2,
        tools=[FunctionTool(tool)],
    )

    response = agent.step("Use the tool as needed.")

    assert response.msg.content == "Done."
    # Two iterations to exhaust the tool budget, plus one more (with
    # tools withheld) to obtain the final textual response.
    assert model.run.call_count == 3
    assert agent.max_iteration is None
    assert agent.max_tool_calls == 2
