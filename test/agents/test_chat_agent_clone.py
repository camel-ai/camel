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
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import OpenAIModel, StubModel
from camel.terminators import ResponseWordsTerminator
from camel.types import ModelType
from camel.utils.langfuse import set_current_agent_session_id


def _make_agent() -> ChatAgent:
    return ChatAgent(
        model=StubModel(ModelType.STUB),
        response_terminators=[ResponseWordsTerminator(words_dict={"stop": 2})],
    )


def _stop_response():
    return [
        BaseMessage.make_assistant_message(
            role_name="assistant",
            content="stop",
        )
    ]


def _response_events(response_id: str):
    return [
        {
            "type": "response.created",
            "response": {"id": response_id},
        },
        {
            "type": "response.output_text.delta",
            "item_id": "msg_1",
            "delta": "Done",
        },
        {
            "type": "response.completed",
            "response": {
                "id": response_id,
                "usage": {
                    "input_tokens": 2,
                    "output_tokens": 1,
                    "total_tokens": 3,
                },
            },
        },
    ]


async def _async_response_events(response_id: str):
    for event in _response_events(response_id):
        yield event


def test_clone_response_terminators_have_independent_identity():
    source = _make_agent()
    first = source.clone()
    second = source.clone()

    assert first.response_terminators is not source.response_terminators
    assert second.response_terminators is not source.response_terminators
    assert first.response_terminators is not second.response_terminators
    assert first.response_terminators[0] is not source.response_terminators[0]
    assert second.response_terminators[0] is not source.response_terminators[0]
    assert first.response_terminators[0] is not second.response_terminators[0]


def test_clone_response_terminator_counts_are_independent():
    source = _make_agent()
    first = source.clone()
    second = source.clone()

    assert first.response_terminators[0].is_terminated(_stop_response()) == (
        False,
        None,
    )
    assert second.response_terminators[0].is_terminated(_stop_response()) == (
        False,
        None,
    )


def test_resetting_clone_does_not_reset_another_clone_terminator():
    source = _make_agent()
    first = source.clone()
    second = source.clone()

    assert first.response_terminators[0].is_terminated(_stop_response()) == (
        False,
        None,
    )
    second.reset()

    terminated, reason = first.response_terminators[0].is_terminated(
        _stop_response()
    )
    assert terminated
    assert reason is not None


def test_resetting_clone_clears_only_its_model_session():
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_key="dummy",
        client=MagicMock(),
        async_client=MagicMock(),
        api_mode="responses",
    )
    source = ChatAgent(model=model)
    first = source.clone()
    second = source.clone()
    model._save_response_chain_state(first.agent_id, "first-response", 2)
    model._save_response_chain_state(second.agent_id, "second-response", 2)

    first.reset()

    set_current_agent_session_id(first.agent_id)
    chain_state = model._prepare_responses_input_and_chain(
        [
            {"role": "system", "content": "new system prompt"},
            {"role": "user", "content": "new task"},
        ]
    )

    assert chain_state["previous_response_id"] is None
    assert chain_state["input_messages"][0]["role"] == "system"
    assert first.agent_id not in (
        model._responses_previous_response_id_by_session
    )
    assert first.agent_id not in model._responses_last_message_count_by_session
    assert (
        model._responses_previous_response_id_by_session[second.agent_id]
        == "second-response"
    )
    assert model._responses_last_message_count_by_session[second.agent_id] == 2


def test_clearing_clone_memory_clears_only_its_model_session():
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_key="dummy",
        client=MagicMock(),
        async_client=MagicMock(),
        api_mode="responses",
    )
    source = ChatAgent(model=model)
    first = source.clone()
    second = source.clone()
    model._save_response_chain_state(first.agent_id, "first-response", 2)
    model._save_response_chain_state(second.agent_id, "second-response", 2)

    first.clear_memory()

    assert first.agent_id not in (
        model._responses_previous_response_id_by_session
    )
    assert first.agent_id not in model._responses_last_message_count_by_session
    assert (
        model._responses_previous_response_id_by_session[second.agent_id]
        == "second-response"
    )
    assert model._responses_last_message_count_by_session[second.agent_id] == 2


def test_streaming_clones_use_independent_model_sessions():
    client = MagicMock()
    client.responses.create.side_effect = [
        _response_events("first-response"),
        _response_events("second-response"),
        _response_events("reset-response"),
    ]
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_key="dummy",
        client=client,
        async_client=MagicMock(),
        model_config_dict={"stream": True},
        api_mode="responses",
    )
    source = ChatAgent(
        system_message="system", model=model, stream_accumulate=False
    )
    first = source.clone()
    second = source.clone()

    first_stream = first.step("first task")
    second_stream = second.step("second task")
    list(first_stream)
    list(second_stream)

    assert "previous_response_id" not in (
        client.responses.create.call_args_list[1].kwargs
    )
    assert set(model._responses_previous_response_id_by_session) == {
        first.agent_id,
        second.agent_id,
    }

    first.reset()
    list(first.step("new task"))

    assert "previous_response_id" not in (
        client.responses.create.call_args_list[2].kwargs
    )
    assert (
        model._responses_previous_response_id_by_session[first.agent_id]
        == "reset-response"
    )
    assert (
        model._responses_previous_response_id_by_session[second.agent_id]
        == "second-response"
    )


@pytest.mark.asyncio
async def test_async_streaming_clones_use_independent_model_sessions():
    async_client = MagicMock()
    async_client.responses.create = AsyncMock(
        side_effect=[
            _async_response_events("first-response"),
            _async_response_events("second-response"),
            _async_response_events("reset-response"),
        ]
    )
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_key="dummy",
        client=MagicMock(),
        async_client=async_client,
        model_config_dict={"stream": True},
        api_mode="responses",
    )
    source = ChatAgent(
        system_message="system", model=model, stream_accumulate=False
    )
    first = source.clone()
    second = source.clone()

    first_stream = await first.astep("first task")
    second_stream = await second.astep("second task")
    _ = [response async for response in first_stream]
    _ = [response async for response in second_stream]

    assert "previous_response_id" not in (
        async_client.responses.create.call_args_list[1].kwargs
    )
    assert set(model._responses_previous_response_id_by_session) == {
        first.agent_id,
        second.agent_id,
    }

    first.reset()
    reset_stream = await first.astep("new task")
    _ = [response async for response in reset_stream]

    assert "previous_response_id" not in (
        async_client.responses.create.call_args_list[2].kwargs
    )
    assert (
        model._responses_previous_response_id_by_session[first.agent_id]
        == "reset-response"
    )
    assert (
        model._responses_previous_response_id_by_session[second.agent_id]
        == "second-response"
    )
