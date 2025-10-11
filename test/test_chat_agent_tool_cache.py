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
import pytest

from camel.agents import ChatAgent
from camel.messages import FunctionCallingMessage
from camel.models.stub_model import StubModel
from camel.types import ModelType


@pytest.mark.parametrize("threshold", [20])
def test_tool_output_caching(tmp_path, threshold):
    agent = ChatAgent(
        system_message="You are a tester.",
        model=StubModel(model_type=ModelType.STUB),
        enable_tool_output_cache=True,
        tool_output_cache_threshold=threshold,
        tool_output_cache_dir=tmp_path,
    )

    long_result = "A" * (threshold + 10)
    short_result = "short"

    agent._record_tool_calling(
        "dummy_tool",
        args={"value": 1},
        result=long_result,
        tool_call_id="call-1",
    )

    history = [
        entry
        for entry in agent._tool_output_history
        if entry.tool_call_id == "call-1"
    ]
    assert history and not history[0].cached

    agent._record_tool_calling(
        "dummy_tool",
        args={"value": 2},
        result=short_result,
        tool_call_id="call-2",
    )

    cached_entry = next(
        entry
        for entry in agent._tool_output_history
        if entry.tool_call_id == "call-1"
    )
    assert cached_entry.cached
    assert cached_entry.cache_id

    cache_file = tmp_path / f"{cached_entry.cache_id}.txt"
    assert cache_file.exists()
    assert long_result in cache_file.read_text(encoding="utf-8")

    records = agent.memory.retrieve()
    cached_message = None
    for record in records:
        message = record.memory_record.message
        if (
            isinstance(message, FunctionCallingMessage)
            and getattr(message, "tool_call_id", "") == "call-1"
        ):
            cached_message = message
            break

    assert cached_message is not None
    assert cached_entry.cache_id in cached_message.result
    assert agent._cache_lookup_tool_name in cached_message.result
    assert long_result not in cached_message.result

    retrieved = agent.retrieve_cached_tool_output(cached_entry.cache_id)
    assert long_result in retrieved


def test_tool_output_history_cleared_on_reset(tmp_path):
    agent = ChatAgent(
        system_message="Cache reset tester.",
        model=StubModel(model_type=ModelType.STUB),
        enable_tool_output_cache=True,
        tool_output_cache_threshold=10,
        tool_output_cache_dir=tmp_path,
    )

    agent._record_tool_calling(
        "dummy_tool",
        args={"value": "a"},
        result="A" * 20,
        tool_call_id="call-initial",
    )
    assert agent._tool_output_history

    agent.clear_memory()
    assert agent._tool_output_history == []

    agent._record_tool_calling(
        "dummy_tool",
        args={"value": "b"},
        result="B" * 20,
        tool_call_id="call-after-clear",
    )
    assert len(agent._tool_output_history) == 1

    agent.reset()
    assert agent._tool_output_history == []
