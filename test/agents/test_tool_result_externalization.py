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
import time
from unittest.mock import MagicMock

import pytest

from camel.agents import ChatAgent, ToolResultExternalizationConfig
from camel.agents.tool_result_externalization import (
    TOOL_RESULT_LIST_TOOL_NAME,
    TOOL_RESULT_READ_TOOL_NAME,
    TOOL_RESULT_SEARCH_TOOL_NAME,
    ToolResultExternalizer,
)
from camel.models import BaseModelBackend
from camel.storages import (
    FileToolResultStore,
    InMemoryToolResultStore,
    ToolResultRecord,
)
from camel.toolkits import FunctionTool
from camel.types import ModelType, OpenAIBackendRole


def _mock_model() -> BaseModelBackend:
    model = MagicMock(spec=BaseModelBackend)
    model.model_type = ModelType.DEFAULT
    model.token_limit = 4096
    model.token_counter = MagicMock()
    return model


def _config(store=None, scope_id="test-scope"):
    return ToolResultExternalizationConfig(
        threshold_chars=100,
        preview_chars=20,
        max_read_chars=40,
        store=store,
        scope_id=scope_id,
    )


def _large_output() -> str:
    return "HEAD-" + ("x" * 1_000) + "-Needle-" + ("y" * 1_000) + "-TAIL"


def test_externalizer_round_trip_search_and_list():
    externalizer = ToolResultExternalizer(_config(), "unused-agent-id")
    original = _large_output()

    externalized = externalizer.externalize(
        original, tool_name="shell_view", tool_call_id="call-1"
    )

    assert externalized is not None
    assert externalized.ref.startswith(
        "camel://tool-results/test-scope/tr_call-1_"
    )
    assert original not in externalized.preview
    assert "HEAD-" in externalized.preview
    assert "-TAIL" in externalized.preview

    read_result = externalizer.read(externalized.ref, offset=990, limit=1000)
    assert read_result["returned_chars"] == 40
    assert read_result["has_more"] is True
    assert read_result["offset_unit"] == "unicode_code_point"

    search_result = externalizer.search(
        externalized.ref, "needle", context_chars=10
    )
    assert search_result["matches"][0]["offset"] == original.index("Needle")
    assert "Needle" in search_result["matches"][0]["snippet"]

    listed = externalizer.list(tool_name="shell_view")
    assert listed["tool_results"][0]["ref"] == externalized.ref
    assert "content" not in listed["tool_results"][0]


def test_externalizer_keeps_result_inline_when_preview_is_larger():
    externalizer = ToolResultExternalizer(_config(), "unused-agent-id")

    externalized = externalizer.externalize(
        "x" * 101, tool_name="shell_view", tool_call_id="call-small"
    )

    assert externalized is None
    assert externalizer.list()["tool_results"] == []


def test_externalizer_caps_list_results():
    externalizer = ToolResultExternalizer(
        ToolResultExternalizationConfig(
            threshold_chars=100,
            preview_chars=20,
            max_list_results=2,
            scope_id="test-scope",
        ),
        "unused-agent-id",
    )
    for index in range(3):
        assert externalizer.externalize(
            _large_output() + str(index),
            tool_name="shell_view",
            tool_call_id=f"call-{index}",
        )

    assert len(externalizer.list(limit=100)["tool_results"]) == 2


def test_externalizer_storage_failure_modes():
    store = MagicMock()
    store.save.side_effect = OSError("storage unavailable")
    inline_externalizer = ToolResultExternalizer(
        _config(store=store), "unused-agent-id"
    )

    assert (
        inline_externalizer.externalize(
            _large_output(),
            tool_name="shell_view",
            tool_call_id="call-inline",
        )
        is None
    )

    raise_externalizer = ToolResultExternalizer(
        ToolResultExternalizationConfig(
            threshold_chars=100,
            preview_chars=20,
            failure_mode="raise",
            scope_id="test-scope",
            store=store,
        ),
        "unused-agent-id",
    )
    with pytest.raises(OSError, match="storage unavailable"):
        raise_externalizer.externalize(
            _large_output(),
            tool_name="shell_view",
            tool_call_id="call-raise",
        )


def test_file_store_persists_payload_and_metadata_separately(tmp_path):
    first_store = FileToolResultStore(tmp_path)
    externalizer = ToolResultExternalizer(
        _config(store=first_store), "unused-agent-id"
    )
    original = _large_output()
    externalized = externalizer.externalize(
        original, tool_name="pytest", tool_call_id="call-file"
    )
    assert externalized is not None

    result_dir = tmp_path / "test-scope" / externalized.record.result_id
    assert (result_dir / "output.txt").read_text() == original
    metadata = json.loads((result_dir / "metadata.json").read_text())
    assert "content" not in metadata
    assert metadata["sha256"] == externalized.record.sha256

    second_store = FileToolResultStore(tmp_path)
    restored = second_store.get("test-scope", externalized.record.result_id)
    assert restored is not None
    assert restored.content == original

    (result_dir / "output.txt").write_text("corrupted")
    listed = second_store.list("test-scope")
    assert listed[0]["ref"] == externalized.ref
    with pytest.raises(ValueError, match="SHA-256"):
        second_store.get("test-scope", externalized.record.result_id)

    metadata["scope_id"] = "other-scope"
    (result_dir / "metadata.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="identity"):
        second_store.get("test-scope", externalized.record.result_id)


@pytest.mark.parametrize(
    ("scope_id", "result_id"),
    [
        (".", "safe-result"),
        ("..", "safe-result"),
        ("safe-scope", "."),
        ("safe-scope", ".."),
    ],
)
def test_file_store_rejects_reserved_path_components(
    tmp_path, scope_id, result_id
):
    store = FileToolResultStore(tmp_path / "store")
    record = ToolResultRecord(
        result_id=result_id,
        scope_id=scope_id,
        ref=f"camel://tool-results/{scope_id}/{result_id}",
        tool_name="tool",
        tool_call_id="call-path",
        content="payload",
        created_at=time.time(),
        expires_at=None,
        original_chars=7,
        sha256="unused-before-save",
    )

    with pytest.raises(ValueError, match="Invalid"):
        store.save(record)
    with pytest.raises(ValueError, match="Invalid"):
        store.get(scope_id, result_id)
    with pytest.raises(ValueError, match="Invalid"):
        store.delete(scope_id, result_id)
    if scope_id in {".", ".."}:
        with pytest.raises(ValueError, match="Invalid"):
            store.list(scope_id)


def test_in_memory_store_lazily_removes_expired_results():
    store = InMemoryToolResultStore()
    record = ToolResultRecord(
        result_id="tr_expired",
        scope_id="test-scope",
        ref="camel://tool-results/test-scope/tr_expired",
        tool_name="tool",
        tool_call_id="call-expired",
        content="expired",
        created_at=time.time() - 10,
        expires_at=time.time() - 1,
        original_chars=7,
        sha256="unused-in-memory",
    )
    store.save(record)

    assert store.get("test-scope", "tr_expired") is None
    assert store.list("test-scope") == []


def test_chat_agent_externalizes_only_the_memory_copy_and_registers_tools():
    agent = ChatAgent(
        model=_mock_model(), tool_result_externalization=_config()
    )
    original = _large_output()

    tool_record = agent._record_tool_calling(
        "shell_view", {"path": "large.log"}, original, "call-agent"
    )

    assert tool_record.result == original
    assert tool_record.result_externalized is True
    assert tool_record.result_ref is not None
    assert {
        TOOL_RESULT_READ_TOOL_NAME,
        TOOL_RESULT_SEARCH_TOOL_NAME,
        TOOL_RESULT_LIST_TOOL_NAME,
    }.issubset(agent.tool_dict)

    memory_records = agent.memory.retrieve()
    tool_messages = [
        record.memory_record.message
        for record in memory_records
        if record.memory_record.role_at_backend == OpenAIBackendRole.FUNCTION
    ]
    assert len(tool_messages) == 1
    assert original not in str(tool_messages[0].result)
    assert tool_record.result_ref in str(tool_messages[0].result)


def test_read_tool_result_is_not_externalized_again():
    agent = ChatAgent(
        model=_mock_model(), tool_result_externalization=_config()
    )
    original_record = agent._record_tool_calling(
        "shell_view", {}, _large_output(), "call-original"
    )
    assert original_record.result_ref is not None

    read_output = agent.tool_dict[TOOL_RESULT_READ_TOOL_NAME](
        ref=original_record.result_ref, offset=0, limit=40
    )
    read_record = agent._record_tool_calling(
        TOOL_RESULT_READ_TOOL_NAME,
        {"ref": original_record.result_ref, "offset": 0, "limit": 40},
        read_output,
        "call-read",
    )

    assert read_record.result_externalized is False
    assert read_record.result_ref is None
    assert "[CAMEL externalized tool result chunk]" in read_output


def test_clone_with_memory_preserves_result_scope_and_store():
    agent = ChatAgent(
        model=_mock_model(), tool_result_externalization=_config(scope_id=None)
    )
    tool_record = agent._record_tool_calling(
        "shell_view", {}, _large_output(), "call-clone"
    )
    assert tool_record.result_ref is not None

    cloned = agent.clone(with_memory=True)
    read_output = cloned.tool_dict[TOOL_RESULT_READ_TOOL_NAME](
        ref=tool_record.result_ref, offset=0, limit=20
    )

    assert not read_output.startswith("Error reading")
    assert "HEAD-" in read_output


def _streaming_large_tool() -> str:
    r"""Return a large result for stream-path tests."""
    return _large_output()


def test_stream_tool_execution_externalizes_result():
    agent = ChatAgent(
        model=_mock_model(),
        tools=[FunctionTool(_streaming_large_tool)],
        tool_result_externalization=_config(),
    )
    tool_call = {
        "id": "call-stream",
        "function": {
            "name": "_streaming_large_tool",
            "arguments": "{}",
        },
    }

    record = agent._execute_tool_from_stream_data(tool_call)

    assert record is not None
    assert record.result_externalized is True
    assert record.result_ref is not None


def test_masked_stream_tool_result_is_not_externalized():
    store = InMemoryToolResultStore()
    agent = ChatAgent(
        model=_mock_model(),
        tools=[FunctionTool(_streaming_large_tool)],
        mask_tool_output=True,
        tool_result_externalization=_config(store=store),
    )
    tool_call = {
        "id": "call-masked-stream",
        "function": {
            "name": "_streaming_large_tool",
            "arguments": "{}",
        },
    }

    record = agent._execute_tool_from_stream_data(tool_call)

    assert record is not None
    assert record.result_externalized is False
    assert record.result_ref is None
    assert "output from the tool is masked" in record.result
    assert store.list("test-scope") == []


def test_stream_tool_externalization_raise_mode_propagates_storage_failure():
    store = MagicMock()
    store.save.side_effect = OSError("storage unavailable")
    agent = ChatAgent(
        model=_mock_model(),
        tools=[FunctionTool(_streaming_large_tool)],
        tool_result_externalization=ToolResultExternalizationConfig(
            threshold_chars=100,
            preview_chars=20,
            failure_mode="raise",
            scope_id="test-scope",
            store=store,
        ),
    )
    tool_call = {
        "id": "call-stream-raise",
        "function": {
            "name": "_streaming_large_tool",
            "arguments": "{}",
        },
    }

    with pytest.raises(OSError, match="storage unavailable"):
        agent._execute_tool_from_stream_data(tool_call)


@pytest.mark.asyncio
async def test_async_stream_tool_execution_externalizes_result():
    agent = ChatAgent(
        model=_mock_model(),
        tools=[FunctionTool(_streaming_large_tool)],
        tool_result_externalization=_config(),
    )
    tool_call = {
        "id": "call-async-stream",
        "function": {
            "name": "_streaming_large_tool",
            "arguments": "{}",
        },
    }

    record = await agent._aexecute_tool_from_stream_data(tool_call)

    assert record is not None
    assert record.result_externalized is True
    assert record.result_ref is not None


@pytest.mark.asyncio
async def test_async_stream_raise_mode_propagates_storage_failure():
    store = MagicMock()
    store.save.side_effect = OSError("storage unavailable")
    agent = ChatAgent(
        model=_mock_model(),
        tools=[FunctionTool(_streaming_large_tool)],
        tool_result_externalization=ToolResultExternalizationConfig(
            threshold_chars=100,
            preview_chars=20,
            failure_mode="raise",
            scope_id="test-scope",
            store=store,
        ),
    )
    tool_call = {
        "id": "call-async-stream-raise",
        "function": {
            "name": "_streaming_large_tool",
            "arguments": "{}",
        },
    }

    with pytest.raises(OSError, match="storage unavailable"):
        await agent._aexecute_tool_from_stream_data(tool_call)
