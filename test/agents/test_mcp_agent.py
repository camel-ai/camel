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

import asyncio
import threading
from typing import Any, List, Union

import pytest

from camel.agents.mcp_agent import MCPAgent
from camel.messages import BaseMessage
from camel.parsers.mcp_tool_call_parser import extract_tool_calls_from_text
from camel.responses import ChatAgentResponse


@pytest.mark.parametrize(
    "content,expected",
    [
        (
            """Here is the call:
```json
{
  \"server_idx\": 0,
  \"tool_name\": \"search_tool\",
  \"tool_args\": {\"query\": \"hello\"}
}
```
""",
            [
                {
                    "server_idx": 0,
                    "tool_name": "search_tool",
                    "tool_args": {"query": "hello"},
                }
            ],
        ),
        (
            """Please run this: {\"server_idx\": 1, \"tool_name\": \"math\",
            \"tool_args\": {\"a\": 1, \"b\": 2}}""",
            [
                {
                    "server_idx": 1,
                    "tool_name": "math",
                    "tool_args": {"a": 1, "b": 2},
                }
            ],
        ),
        (
            """Tool candidate {'server_idx': 0, 'tool_name': 'search',
            'tool_args': {'query': 'plan 2'}}""",
            [
                {
                    "server_idx": 0,
                    "tool_name": "search",
                    "tool_args": {"query": "plan 2"},
                }
            ],
        ),
        (
            """Multiple calls: [{\"server_idx\": 0, \"tool_name\": \"alpha\",
            \"tool_args\": {}}, {\"server_idx\": 1, \"tool_name\": \"beta\",
            \"tool_args\": {\"q\": \"x\"}}]""",
            [
                {"server_idx": 0, "tool_name": "alpha", "tool_args": {}},
                {
                    "server_idx": 1,
                    "tool_name": "beta",
                    "tool_args": {"q": "x"},
                },
            ],
        ),
    ],
)
def test_extract_tool_calls_from_text(
    content: str, expected: List[dict]
) -> None:
    tool_calls = extract_tool_calls_from_text(content)

    assert len(tool_calls) == len(expected)
    for idx, tool_call in enumerate(tool_calls):
        for key, value in expected[idx].items():
            assert tool_call[key] == value


def test_extract_tool_calls_without_payload() -> None:
    assert extract_tool_calls_from_text("No calls available") == []


def test_extract_tool_calls_from_yaml_block() -> None:
    pytest.importorskip("yaml")

    content = (
        "Here is the YAML call:\n"
        "```yaml\n"
        "server_idx: 2\n"
        "tool_name: yaml_tool\n"
        "tool_args:\n"
        "  prompt: Hello\n"
        "```\n"
    )

    expected = {
        "server_idx": 2,
        "tool_name": "yaml_tool",
        "tool_args": {"prompt": "Hello"},
    }

    tool_calls = extract_tool_calls_from_text(content)

    assert len(tool_calls) == 1
    assert tool_calls[0] == expected


class _StepRecordingAgent(MCPAgent):
    r"""An MCPAgent whose ``astep`` records the loop it was awaited on.

    ``MCPAgent.__init__`` builds a model backend and an MCP toolkit, neither
    of which is needed to exercise the sync/async bridging in ``step``, so
    construction is bypassed entirely.
    """

    def __init__(self) -> None:
        self.astep_calls: List[str] = []
        self.astep_loops: List[asyncio.AbstractEventLoop] = []
        self.astep_threads: List[int] = []

    async def astep(  # type: ignore[override]
        self,
        input_message: Union[BaseMessage, str],
        *args: Any,
        **kwargs: Any,
    ) -> ChatAgentResponse:
        await asyncio.sleep(0)
        self.astep_calls.append(str(input_message))
        self.astep_loops.append(asyncio.get_running_loop())
        self.astep_threads.append(threading.get_ident())
        return ChatAgentResponse(msgs=[], terminated=False, info={})


def _step_from_inside_a_running_loop(
    agent: MCPAgent, *args: Any, **kwargs: Any
) -> Any:
    r"""Call ``agent.step`` from a thread that is *running* an event loop.

    ``step`` must be invoked on the loop thread itself -- that is what
    ``Jupyter``/``FastAPI`` handlers do, and it is the only way to reach the
    ``loop.is_running()`` branch. Offloading with ``asyncio.to_thread``
    would leave the worker without a running loop and silently exercise the
    plain ``asyncio.run`` branch instead.

    The call runs on a daemon thread with a join timeout, so a regression
    that deadlocks fails the test instead of hanging the suite.
    """
    outcome: dict = {}

    def target() -> None:
        async def main() -> None:
            try:
                outcome["value"] = agent.step(*args, **kwargs)
            except BaseException as exc:
                outcome["error"] = exc

        asyncio.run(main())

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=30)

    assert not thread.is_alive(), (
        "step() did not return: the coroutine is being driven by the "
        "caller's own loop, which step() blocks while waiting."
    )
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def test_step_outside_event_loop() -> None:
    r"""Baseline: with no running loop ``step`` drives ``astep`` directly."""
    agent = _StepRecordingAgent()

    response = agent.step("hello")

    assert isinstance(response, ChatAgentResponse)
    assert agent.astep_calls == ["hello"]


def test_step_inside_running_event_loop() -> None:
    r"""``step`` must still work when called from inside a running loop.

    This is the Jupyter/FastAPI case the branch was written for. Passing an
    already-scheduled task to ``asyncio.run_coroutine_threadsafe`` raised
    ``TypeError: A coroutine object is required``, and handing it the bare
    coroutine instead would deadlock, because ``step`` occupies the very
    thread the target loop runs on.
    """
    agent = _StepRecordingAgent()

    response = _step_from_inside_a_running_loop(agent, "hello")

    assert isinstance(response, ChatAgentResponse)
    assert agent.astep_calls == ["hello"]


def test_step_inside_running_loop_uses_a_separate_loop() -> None:
    r"""The coroutine must not be scheduled on the caller's loop.

    Driving it on the caller's loop is what deadlocks, so the guarantee is
    checked directly rather than only via the absence of a timeout.
    """
    caller_loops: List[asyncio.AbstractEventLoop] = []
    caller_threads: List[int] = []

    class _Probing(_StepRecordingAgent):
        def step(self, *args: Any, **kwargs: Any) -> ChatAgentResponse:
            caller_loops.append(asyncio.get_running_loop())
            caller_threads.append(threading.get_ident())
            return super().step(*args, **kwargs)

    agent = _Probing()

    _step_from_inside_a_running_loop(agent, "hello")

    assert agent.astep_loops[0] is not caller_loops[0]
    assert agent.astep_threads[0] != caller_threads[0]


def test_step_inside_running_loop_propagates_exceptions() -> None:
    r"""Failures inside ``astep`` must surface to the synchronous caller."""

    class _Failing(_StepRecordingAgent):
        async def astep(  # type: ignore[override]
            self,
            input_message: Union[BaseMessage, str],
            *args: Any,
            **kwargs: Any,
        ) -> ChatAgentResponse:
            raise RuntimeError("astep failed")

    agent = _Failing()

    with pytest.raises(RuntimeError, match="astep failed"):
        _step_from_inside_a_running_loop(agent, "hello")


def test_step_inside_running_loop_forwards_arguments() -> None:
    r"""Positional and keyword arguments reach ``astep`` unchanged."""
    captured: dict = {}

    class _Capturing(_StepRecordingAgent):
        async def astep(  # type: ignore[override]
            self,
            input_message: Union[BaseMessage, str],
            *args: Any,
            **kwargs: Any,
        ) -> ChatAgentResponse:
            captured["input_message"] = input_message
            captured["args"] = args
            captured["kwargs"] = kwargs
            return ChatAgentResponse(msgs=[], terminated=False, info={})

    agent = _Capturing()

    _step_from_inside_a_running_loop(agent, "hello", 1, flag=True)

    assert captured["input_message"] == "hello"
    assert captured["args"] == (1,)
    assert captured["kwargs"] == {"flag": True}
