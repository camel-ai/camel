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

import json
from unittest.mock import patch

import httpx
import pytest

from camel.agents import ChatAgent
from camel.memories import (
    MemantoMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage, FunctionCallingMessage
from camel.storages import InMemoryKeyValueStorage
from camel.types import ModelType, OpenAIBackendRole, RoleType
from camel.utils import OpenAITokenCounter


def make_record(content, role=OpenAIBackendRole.USER):
    return MemoryRecord(
        message=BaseMessage.make_user_message(
            role_name="User", content=content
        ),
        role_at_backend=role,
    )


@pytest.fixture
def memanto_http():
    requests = []
    archive = [
        {"id": "old-memory", "content": "User prefers Python", "tags": []}
    ]
    responses = []

    def handle(request):
        requests.append(request)
        operation = request.url.path.rsplit("/", 1)[-1]
        if operation == "activate":
            return httpx.Response(200, json={"session_token": "test-token"})
        if responses:
            return responses.pop(0)
        payload = json.loads(request.content)
        if operation == "remember":
            memory_id = str(len(archive))
            archive.append({"id": memory_id, **payload})
            return httpx.Response(200, json={"memory_id": memory_id})
        assert operation == "recall"
        return httpx.Response(200, json={"memories": list(archive)})

    storage = InMemoryKeyValueStorage()
    creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 10000
    )
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with patch("httpx.Client", return_value=client):
            memory = MemantoMemory(
                context_creator=creator,
                agent_id="test-agent",
                base_url="https://memanto.example/",
                storage=storage,
            )
        try:
            yield memory, storage, archive, requests, responses
        finally:
            memory.close()


def test_agent_automatically_writes_and_recalls_without_tools(
    memanto_http, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    memory, storage, archive, requests, _ = memanto_http
    agent = ChatAgent(
        system_message="Be helpful.",
        model=ModelType.STUB,
        memory=memory,
        agent_id="test-agent",
    )
    with patch.object(
        agent.model_backend.models[0],
        "_run",
        wraps=agent.model_backend.models[0]._run,
    ) as run:
        agent.step("Which language do I prefer?")
    messages = run.call_args.kwargs.get("messages") or run.call_args.args[0]
    assert messages[0]["role"] == "system"
    assert any(
        "Recalled memory" in m.get("content", "") and "Python" in m["content"]
        for m in messages
    )
    assert messages[-1]["content"] == "Which language do I prefer?"
    assert archive[0]["id"] == "old-memory"
    assert any(r.url.path.endswith("/remember") for r in requests)
    assert any(r.url.path.endswith("/recall") for r in requests)
    assert all(r.method == "POST" for r in requests)
    assert not agent._internal_tools


def test_roles_and_tool_results_survive_roundtrip(memanto_http):
    memory, storage, archive, _, _ = memanto_http
    call = FunctionCallingMessage(
        role_name="Agent",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="",
        func_name="weather",
        args={"city": "Paris"},
        tool_call_id="call_1",
    )
    result = FunctionCallingMessage(
        role_name="Agent",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="",
        func_name="weather",
        result="Sunny, 25 C",
        tool_call_id="call_1",
    )
    records = [
        make_record("Follow policy", OpenAIBackendRole.SYSTEM),
        make_record("Weather?"),
        MemoryRecord(
            message=call, role_at_backend=OpenAIBackendRole.ASSISTANT
        ),
        MemoryRecord(
            message=result, role_at_backend=OpenAIBackendRole.FUNCTION
        ),
    ]
    memory.write_records(records)
    assert storage.load() == [r.to_dict() for r in records]
    messages, _ = memory.get_context()
    conversation = [
        m
        for m in messages
        if not m.get("content", "").startswith("Recalled memory")
    ]
    assert conversation == [r.to_openai_message() for r in records]
    assert conversation[-1]["content"] == "Sunny, 25 C"
    assert len(archive) == 2  # Existing memory and the user text only.


def test_recall_payload_and_current_record_deduplication(memanto_http):
    memory, _, _, requests, _ = memanto_http
    record = make_record("Preferred language?")
    memory.write_record(record)
    messages, _ = memory.get_context()
    assert len(messages) == 2  # One historical memory plus current user input.
    remember = next(r for r in requests if r.url.path.endswith("/remember"))
    assert json.loads(remember.content) == {
        "content": "user: Preferred language?",
        "type": "context",
        "tags": [f"camel-record:{record.uuid}"],
    }
    assert json.loads(requests[-1].content) == {
        "query": "Preferred language?",
        "limit": 3,
    }
    assert requests[-1].headers["X-Session-Token"] == "test-token"


def test_rollback_keeps_all_other_history_and_remote_memories(memanto_http):
    memory, storage, archive, requests, _ = memanto_http
    memory.write_records([make_record(str(i)) for i in range(150)])
    before = list(archive)
    request_count = len(requests)
    removed = memory.pop_records(1)
    assert len(storage.load()) == 149
    assert removed[0].message.content == "149"
    memory.remove_records_by_indices([0])
    assert len(storage.load()) == 148
    assert archive == before
    assert len(requests) == request_count


def test_clear_and_new_session_preserve_long_term_memory(memanto_http):
    memory, storage, archive, requests, _ = memanto_http
    memory.write_record(make_record("My preference is Python"))
    before = list(archive)
    request_count = len(requests)
    memory.clear()
    assert storage.load() == []
    assert memory.retrieve() == []
    assert archive == before
    assert len(requests) == request_count
    memory.write_record(make_record("What was my preference?"))
    assert any(
        "My preference is Python" in r.memory_record.message.content
        for r in memory.retrieve()
    )


def test_recall_refreshes_context_token_count(memanto_http):
    memory, _, archive, _, _ = memanto_http
    memory.write_record(make_record("Preference?"))
    messages, tokens = memory.get_context()
    memory.get_context_creator().set_cached_token_count(tokens, len(messages))
    archive[0]["content"] = "A much longer remembered preference. " * 100
    new_messages, new_tokens = memory.get_context()
    assert len(new_messages) == len(messages)
    assert new_tokens > tokens


def test_expired_session_retries_with_new_token(memanto_http):
    memory, _, _, requests, responses = memanto_http
    memory._client._session_token = "expired"
    responses.extend(
        [httpx.Response(401), httpx.Response(200, json={"memory_id": "new"})]
    )
    memory.write_record(make_record("A fact"))
    assert [r.url.path.rsplit("/", 1)[-1] for r in requests] == [
        "activate",
        "remember",
        "activate",
        "remember",
    ]
    assert requests[1].headers["X-Session-Token"] == "expired"
    assert requests[3].headers["X-Session-Token"] == "test-token"
    assert requests[1].content == requests[3].content


@pytest.mark.parametrize("status", [401, 500])
def test_failed_write_raises_and_keeps_local_record(memanto_http, status):
    memory, storage, _, requests, responses = memanto_http
    responses.extend([httpx.Response(status), httpx.Response(status)])
    record = make_record("Keep this record")
    with pytest.raises(httpx.HTTPStatusError):
        memory.write_record(record)
    assert storage.load() == [record.to_dict()]
    assert len(requests) == (4 if status == 401 else 2)


def test_failed_recall_raises(memanto_http):
    memory, _, _, _, responses = memanto_http
    memory.write_record(make_record("Question"))
    responses.append(httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        memory.retrieve()


def test_invalid_configuration_fails_before_http(monkeypatch):
    monkeypatch.delenv("MEMANTO_AGENT_ID", raising=False)
    with patch("httpx.Client") as client:
        with pytest.raises(ValueError, match="agent_id"):
            MemantoMemory(context_creator=None)
        with pytest.raises(ValueError, match="retrieve_limit"):
            MemantoMemory(
                context_creator=None, agent_id="test", retrieve_limit=101
            )
        client.assert_not_called()


def test_failed_activation_closes_client():
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(404))
    ) as client:
        with patch("httpx.Client", return_value=client):
            with pytest.raises(httpx.HTTPStatusError):
                MemantoMemory(context_creator=None, agent_id="missing")
        assert client.is_closed


def test_close_preserves_memories(memanto_http):
    memory, storage, archive, _, _ = memanto_http
    memory.write_record(make_record("Keep this"))
    local = storage.load()
    remote = list(archive)
    memory.close()
    assert memory._client._client.is_closed
    assert storage.load() == local and archive == remote
