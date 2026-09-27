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

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import OpenAICompatibleModel, OpenAIModel, StubModel
from camel.terminators import ResponseWordsTerminator
from camel.types import ModelType


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


@pytest.mark.parametrize("model_class", [OpenAIModel, OpenAICompatibleModel])
def test_reset_clears_response_chain_state_for_reset_agent(model_class):
    model = model_class(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    agent = ChatAgent(model=model)
    other_agent = agent.clone()
    agent_key = agent.agent_id
    other_key = other_agent.agent_id
    model._save_response_chain_state(agent_key, "resp_agent", 3)
    model._save_response_chain_state(other_key, "resp_other", 3)

    agent.reset()

    assert agent_key not in model._responses_previous_response_id_by_session
    assert agent_key not in model._responses_last_message_count_by_session
    assert other_key in model._responses_previous_response_id_by_session
    assert other_key in model._responses_last_message_count_by_session


@pytest.mark.parametrize("model_class", [OpenAIModel, OpenAICompatibleModel])
def test_step_timeout_uses_agent_session_for_response_chain(
    monkeypatch, model_class
):
    model = model_class(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    agent = ChatAgent(model=model, step_timeout=1)
    captured = {}

    def fake_step_impl(*args, **kwargs):
        captured["session_key"] = model._get_response_chain_session_key()
        model._save_response_chain_state(
            captured["session_key"], "resp_agent", 3
        )

    monkeypatch.setattr(agent, "_step_impl", fake_step_impl)
    agent.step("hello")

    assert captured["session_key"] == agent.agent_id
    agent.reset()
    assert (
        agent.agent_id not in model._responses_previous_response_id_by_session
    )
    assert agent.agent_id not in model._responses_last_message_count_by_session


def test_step_sets_agent_session_before_streaming(monkeypatch):
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    model.model_config_dict["stream"] = True
    agent = ChatAgent(model=model)
    captured = {}

    def fake_stream(*args, **kwargs):
        from camel.utils.langfuse import get_current_agent_session_id

        captured["session_id"] = get_current_agent_session_id()
        return iter(())

    monkeypatch.setattr(agent, "_stream", fake_stream)

    agent.step("hello")

    assert captured["session_id"] == agent.agent_id


def test_sync_stream_restores_agent_session_when_consumed(monkeypatch):
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    model.model_config_dict["stream"] = True
    agent = ChatAgent(model=model)
    other_agent = agent.clone()
    captured = {}

    def save_response_chain_state():
        session_key = model._get_response_chain_session_key()
        response_count = len(captured.setdefault("session_keys", []))
        captured["session_keys"].append(session_key)
        model._save_response_chain_state(
            session_key, f"response-{response_count}", response_count
        )

    def fake_get_context():
        return [], 0

    def fake_stream_response(*args, **kwargs):
        save_response_chain_state()
        yield
        save_response_chain_state()
        yield

    monkeypatch.setattr(
        agent, "_get_context_with_summarization", fake_get_context
    )
    monkeypatch.setattr(agent, "_stream_response", fake_stream_response)

    response = agent.step("hello")

    from camel.utils.langfuse import (
        get_current_agent_session_id,
        set_current_agent_session_id,
    )

    previous_session_id = get_current_agent_session_id()
    stream = iter(response)
    try:
        next(stream)
        set_current_agent_session_id(other_agent.agent_id)
        next(stream)

        assert captured["session_keys"] == [agent.agent_id, agent.agent_id]
        assert model._responses_previous_response_id_by_session == {
            agent.agent_id: "response-1"
        }
        assert model._responses_last_message_count_by_session == {
            agent.agent_id: 1
        }
        with pytest.raises(StopIteration):
            next(stream)
    finally:
        set_current_agent_session_id(previous_session_id)


@pytest.mark.asyncio
async def test_async_stream_restores_agent_session_when_consumed(monkeypatch):
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    model.model_config_dict["stream"] = True
    agent = ChatAgent(model=model)
    other_agent = agent.clone()
    captured = {}

    def save_response_chain_state():
        session_key = model._get_response_chain_session_key()
        response_count = len(captured.setdefault("session_keys", []))
        captured["session_keys"].append(session_key)
        model._save_response_chain_state(
            session_key, f"response-{response_count}", response_count
        )

    async def fake_get_context():
        return [], 0

    async def fake_stream_response(*args, **kwargs):
        save_response_chain_state()
        yield
        save_response_chain_state()
        yield

    monkeypatch.setattr(
        agent, "_get_context_with_summarization_async", fake_get_context
    )
    monkeypatch.setattr(agent, "_astream_response", fake_stream_response)

    response = await agent.astep("hello")

    from camel.utils.langfuse import (
        get_current_agent_session_id,
        set_current_agent_session_id,
    )

    previous_session_id = get_current_agent_session_id()
    stream = response.__aiter__()
    try:
        await stream.__anext__()
        set_current_agent_session_id(other_agent.agent_id)
        await stream.__anext__()

        assert captured["session_keys"] == [agent.agent_id, agent.agent_id]
        assert model._responses_previous_response_id_by_session == {
            agent.agent_id: "response-1"
        }
        assert model._responses_last_message_count_by_session == {
            agent.agent_id: 1
        }
        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()
    finally:
        set_current_agent_session_id(previous_session_id)


@pytest.mark.parametrize("model_class", [OpenAIModel, OpenAICompatibleModel])
def test_sync_stream_step_sets_agent_session_id(model_class):
    model = model_class(
        model_type=ModelType.GPT_4O_MINI,
        api_mode="responses",
        api_key="test-key",
    )
    model.model_config_dict["stream"] = True
    agent = ChatAgent(model=model)

    from camel.utils.langfuse import (
        get_current_agent_session_id,
        set_current_agent_session_id,
    )

    set_current_agent_session_id(None)
    agent.step("hello")

    assert get_current_agent_session_id() == agent.agent_id
    set_current_agent_session_id(None)
