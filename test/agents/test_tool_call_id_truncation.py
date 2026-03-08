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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from camel.agents import ChatAgent
from camel.agents._types import ToolCallRequest
from camel.agents.chat_agent import _OPENAI_MAX_TOOL_CALL_ID_LEN
from camel.models import ModelManager
from camel.models.openai_model import OpenAIModel
from camel.types import RoleType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LONG_ID = "call_" + "x" * 60  # 65 chars — well over the 40-char limit
BOUNDARY_ID = "call_" + "b" * (40 - len("call_"))  # exactly 40 chars
SHORT_ID = "call_abc123"  # well under limit


def _make_openai_agent() -> ChatAgent:
    r"""Create a ChatAgent backed by a mocked OpenAIModel."""
    mock_model = MagicMock(spec=OpenAIModel)
    mock_model.token_limit = 4096
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "gpt-4o"
    mock_model.model_platform = MagicMock()
    mock_model.token_counter = MagicMock(return_value=0)
    mock_model.model_config_dict = {}
    mock_model.model_type.is_openai = True

    # Wrap in a ModelManager since model_backend is always a ModelManager
    manager = MagicMock(spec=ModelManager)
    manager.current_model = mock_model
    manager.model_type = mock_model.model_type
    manager.token_limit = mock_model.token_limit
    manager.token_counter = mock_model.token_counter

    agent = ChatAgent.__new__(ChatAgent)
    agent.model_backend = manager
    agent._internal_tools = {}
    agent.role_name = "assistant"
    agent.role_type = RoleType.ASSISTANT
    return agent


def _make_non_openai_agent() -> ChatAgent:
    r"""Create a ChatAgent backed by a mocked non-OpenAI model."""
    mock_model = MagicMock()  # plain Mock, not OpenAIModel spec
    mock_model.token_limit = 4096
    mock_model.model_type = MagicMock()
    mock_model.model_type.value_for_tiktoken = "claude-3"
    mock_model.model_config_dict = {}
    mock_model.token_counter = MagicMock(return_value=0)

    # Wrap in a ModelManager since model_backend is always a ModelManager
    manager = MagicMock(spec=ModelManager)
    manager.current_model = mock_model
    manager.model_type = mock_model.model_type
    manager.token_limit = mock_model.token_limit
    manager.token_counter = mock_model.token_counter

    agent = ChatAgent.__new__(ChatAgent)
    agent.model_backend = manager
    agent._internal_tools = {}
    agent.role_name = "assistant"
    agent.role_type = RoleType.ASSISTANT
    return agent


def _fake_tool_calls(tool_call_id: str):
    r"""Build a minimal OpenAI-style tool_calls list with the given ID."""
    func = SimpleNamespace(name="my_tool", arguments='{"x": 1}')
    tc = SimpleNamespace(id=tool_call_id, function=func, extra_content=None)
    return [tc]


def _fake_response(tool_call_id: str):
    r"""Build a minimal ChatCompletion-like object with one tool call."""
    # content="" so _handle_batch_response skips message body building
    # but still processes tool_calls
    message = SimpleNamespace(
        content="",
        role="assistant",
        tool_calls=_fake_tool_calls(tool_call_id),
        function_call=None,
        parsed=None,
        reasoning_content=None,
    )
    choice = SimpleNamespace(
        message=message,
        finish_reason="tool_calls",
        index=0,
        logprobs=None,
    )
    response = MagicMock()
    response.choices = [choice]
    response.usage = None
    response.id = "resp_001"
    return response


def test_constant_value():
    r"""The constant must be 40 per OpenAI spec."""
    assert _OPENAI_MAX_TOOL_CALL_ID_LEN == 40


def test_is_openai_platform_true():
    r"""Returns True when the backend is an OpenAIModel instance."""
    agent = _make_openai_agent()
    assert agent._is_openai_platform() is True


def test_is_openai_platform_false_for_non_openai():
    r"""Returns False when the backend is not an OpenAIModel instance."""
    agent = _make_non_openai_agent()
    assert agent._is_openai_platform() is False


def test_is_openai_platform_with_model_manager():
    r"""Reads current_model from a ModelManager wrapper."""
    openai_mock = MagicMock(spec=OpenAIModel)
    manager = MagicMock(spec=ModelManager)
    manager.current_model = openai_mock

    agent = ChatAgent.__new__(ChatAgent)
    agent.model_backend = manager
    agent._internal_tools = {}

    assert agent._is_openai_platform() is True


def test_is_openai_platform_false_with_non_openai_in_manager():
    r"""Returns False when ModelManager's current_model is non-OpenAI."""
    non_openai_mock = MagicMock()  # no OpenAIModel spec
    manager = MagicMock(spec=ModelManager)
    manager.current_model = non_openai_mock

    agent = ChatAgent.__new__(ChatAgent)
    agent.model_backend = manager
    agent._internal_tools = {}

    assert agent._is_openai_platform() is False


def _run_batch_response(agent, tool_call_id: str, is_openai: bool):
    r"""Run _handle_batch_response and return the list of ToolCallRequests
    that were constructed, without requiring a real ChatCompletion object."""
    response = _fake_response(tool_call_id)
    captured_requests = []

    real_tool_call_request = ToolCallRequest

    def _capture_tool_call_request(**kwargs):
        req = real_tool_call_request(**kwargs)
        captured_requests.append(req)
        return req

    with (
        patch.object(agent, '_is_openai_platform', return_value=is_openai),
        patch('camel.agents.chat_agent.handle_logprobs', return_value=None),
        patch(
            'camel.agents.chat_agent.ToolCallRequest',
            side_effect=_capture_tool_call_request,
        ),
        patch(
            'camel.agents.chat_agent.ModelResponse',
            return_value=MagicMock(),
        ),
        patch(
            'camel.agents.chat_agent.safe_model_dump',
            return_value={},
        ),
    ):
        agent._handle_batch_response(response)

    return captured_requests


def test_batch_response_truncates_long_id_on_openai():
    r"""OpenAI: tool_call IDs > 40 chars must be truncated to 40."""
    agent = _make_openai_agent()
    requests = _run_batch_response(agent, LONG_ID, is_openai=True)
    assert len(requests) == 1
    result_id = requests[0].tool_call_id
    assert len(result_id) == 40
    assert result_id == LONG_ID[:40]


def test_batch_response_preserves_boundary_id_on_openai():
    r"""OpenAI: a 40-char ID must pass through unchanged."""
    assert len(BOUNDARY_ID) == 40
    agent = _make_openai_agent()
    requests = _run_batch_response(agent, BOUNDARY_ID, is_openai=True)
    assert len(requests) == 1
    assert requests[0].tool_call_id == BOUNDARY_ID


def test_batch_response_preserves_short_id_on_openai():
    r"""OpenAI: an ID shorter than 40 chars must not be modified."""
    assert len(SHORT_ID) < 40
    agent = _make_openai_agent()
    requests = _run_batch_response(agent, SHORT_ID, is_openai=True)
    assert len(requests) == 1
    assert requests[0].tool_call_id == SHORT_ID


def test_batch_response_preserves_long_id_on_non_openai():
    r"""Non-OpenAI: long IDs must NOT be truncated."""
    agent = _make_non_openai_agent()
    requests = _run_batch_response(agent, LONG_ID, is_openai=False)
    assert len(requests) == 1
    result_id = requests[0].tool_call_id
    assert result_id == LONG_ID
    assert len(result_id) > 40


def _delta_tool_call(tool_call_id: str, name: str = "", args: str = ""):
    r"""Build a minimal streaming tool-call delta."""
    func = SimpleNamespace(name=name, arguments=args)
    return SimpleNamespace(
        id=tool_call_id,
        index=0,
        function=func,
        extra_content=None,
    )


def test_accumulate_truncates_long_id_on_openai():
    r"""Streaming/OpenAI: accumulated tool_call ID must be capped at 40."""
    agent = _make_openai_agent()
    agent._internal_tools = {
        "my_tool": MagicMock()
    }  # register so completeness check passes

    accumulated: dict = {}
    delta = _delta_tool_call(LONG_ID, name="my_tool", args='{"x":1}')

    with patch.object(agent, '_is_openai_platform', return_value=True):
        agent._accumulate_tool_calls([delta], accumulated)

    # The entry key is derived from the ID; find it
    keys = [k for k in accumulated if k != '_index_to_key_map']
    assert len(keys) == 1
    entry = accumulated[keys[0]]
    stored_id = entry['id']
    assert len(stored_id) == 40
    assert stored_id == LONG_ID[:40]


def test_accumulate_preserves_long_id_on_non_openai():
    r"""Streaming/non-OpenAI: long IDs must NOT be truncated."""
    agent = _make_non_openai_agent()
    agent._internal_tools = {"my_tool": MagicMock()}

    accumulated: dict = {}
    delta = _delta_tool_call(LONG_ID, name="my_tool", args='{"x":1}')

    with patch.object(agent, '_is_openai_platform', return_value=False):
        agent._accumulate_tool_calls([delta], accumulated)

    keys = [k for k in accumulated if k != '_index_to_key_map']
    assert len(keys) == 1
    entry = accumulated[keys[0]]
    stored_id = entry['id']
    assert stored_id == LONG_ID
    assert len(stored_id) > 40


def test_accumulate_preserves_short_id_on_openai():
    r"""Streaming/OpenAI: short IDs (< 40 chars) must not be modified."""
    agent = _make_openai_agent()
    agent._internal_tools = {"my_tool": MagicMock()}

    accumulated: dict = {}
    delta = _delta_tool_call(SHORT_ID, name="my_tool", args='{"x":1}')

    with patch.object(agent, '_is_openai_platform', return_value=True):
        agent._accumulate_tool_calls([delta], accumulated)

    keys = [k for k in accumulated if k != '_index_to_key_map']
    assert len(keys) == 1
    entry = accumulated[keys[0]]
    assert entry['id'] == SHORT_ID


def test_accumulate_multiple_tool_calls_truncated_independently():
    r"""Each tool call entry's ID is independently truncated on OpenAI."""
    agent = _make_openai_agent()
    agent._internal_tools = {
        "tool_a": MagicMock(),
        "tool_b": MagicMock(),
    }

    id_a = "call_a_" + "a" * 50  # 57 chars
    id_b = "call_b_" + "b" * 50  # 57 chars

    accumulated: dict = {}
    delta_a = SimpleNamespace(
        id=id_a,
        index=0,
        function=SimpleNamespace(name="tool_a", arguments='{"a":1}'),
        extra_content=None,
    )
    delta_b = SimpleNamespace(
        id=id_b,
        index=1,
        function=SimpleNamespace(name="tool_b", arguments='{"b":2}'),
        extra_content=None,
    )

    with patch.object(agent, '_is_openai_platform', return_value=True):
        agent._accumulate_tool_calls([delta_a, delta_b], accumulated)

    entries = {
        k: v for k, v in accumulated.items() if k != '_index_to_key_map'
    }
    assert len(entries) == 2
    for entry in entries.values():
        assert len(entry['id']) == 40


def test_tool_call_request_preserves_long_id():
    r"""ToolCallRequest must NOT truncate IDs — that's ChatAgent's job now."""
    req = ToolCallRequest(
        tool_name="fn",
        args={},
        tool_call_id=LONG_ID,
    )
    assert req.tool_call_id == LONG_ID


def test_tool_call_request_preserves_short_id():
    r"""IDs within 40 chars should not be modified."""
    req = ToolCallRequest(
        tool_name="fn",
        args={},
        tool_call_id=SHORT_ID,
    )
    assert req.tool_call_id == SHORT_ID


def test_truncation_at_exact_boundary():
    r"""An ID of exactly 41 chars on OpenAI should be trimmed to 40."""
    id_41 = "x" * 41
    agent = _make_openai_agent()
    accumulated: dict = {}
    delta = _delta_tool_call(id_41, name="my_tool", args='{}')
    agent._internal_tools = {"my_tool": MagicMock()}

    with patch.object(agent, '_is_openai_platform', return_value=True):
        agent._accumulate_tool_calls([delta], accumulated)

    keys = [k for k in accumulated if k != '_index_to_key_map']
    entry = accumulated[keys[0]]
    assert len(entry['id']) == 40
    assert entry['id'] == id_41[:40]


def test_empty_tool_call_id_unchanged():
    r"""Empty IDs should pass through both branches without error."""
    agent = _make_openai_agent()
    accumulated: dict = {}
    # id='' means no truncation attempted; entry uses index as fallback key
    delta = SimpleNamespace(
        id='',
        index=0,
        function=SimpleNamespace(name="my_tool", arguments='{}'),
        extra_content=None,
    )
    agent._internal_tools = {"my_tool": MagicMock()}

    # Should not raise
    with patch.object(agent, '_is_openai_platform', return_value=True):
        agent._accumulate_tool_calls([delta], accumulated)

    # ID remains empty since no id was provided
    keys = [k for k in accumulated if k != '_index_to_key_map']
    assert len(keys) == 1
    entry = accumulated[keys[0]]
    assert entry['id'] == ''
