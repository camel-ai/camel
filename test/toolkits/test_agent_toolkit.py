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

import time
from types import SimpleNamespace
from typing import ClassVar, List

import pytest

from camel.toolkits.agent_toolkit import AgentToolkit
from camel.toolkits.function_tool import FunctionTool


def parent_search(query: str) -> str:
    """Search docs.

    Args:
        query (str): Search query.

    Returns:
        str: Search result.
    """
    return query


def parent_calc(expr: str) -> str:
    """Evaluate expression.

    Args:
        expr (str): Expression to evaluate.

    Returns:
        str: Evaluation result.
    """
    return expr


class FakeChatAgent:
    created_agents: ClassVar[List["FakeChatAgent"]] = []
    delay_seconds: ClassVar[float] = 0.0

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.agent_id = f"fake-agent-{len(self.created_agents) + 1}"
        self.prompts = []
        self.created_agents.append(self)

    def step(self, prompt):
        self.prompts.append(prompt)
        waited = 0.0
        while waited < self.delay_seconds:
            stop_event = getattr(self, "stop_event", None)
            if stop_event is not None and stop_event.is_set():
                return SimpleNamespace(
                    msgs=[SimpleNamespace(content=f"stopped::{prompt}")]
                )
            time.sleep(0.01)
            waited += 0.01
        return SimpleNamespace(
            msgs=[SimpleNamespace(content=f"handled::{prompt}")]
        )


class TestAgentToolkit:
    def _wait_task(self, toolkit, task_id: str, timeout: float = 2.0):
        task = toolkit._tasks[task_id]
        try:
            task.future.result(timeout=timeout)
        except Exception:
            pass
        toolkit._complete_task(task_id)
        return toolkit._tasks[task_id]

    @pytest.fixture(autouse=True)
    def reset_fake_agents(self):
        FakeChatAgent.created_agents = []
        FakeChatAgent.delay_seconds = 0.0

    @pytest.fixture
    def toolkit(self, monkeypatch):
        monkeypatch.setattr(
            "camel.agents.ChatAgent",
            FakeChatAgent,
            raising=False,
        )
        return AgentToolkit()

    @pytest.fixture
    def parent_agent(self):
        def scheduling_strategy():
            return None

        tools = [
            FunctionTool(parent_search),
            FunctionTool(parent_calc),
        ]
        return SimpleNamespace(
            agent_id="parent-agent",
            model_backend=SimpleNamespace(
                models="parent-model",
                scheduling_strategy=scheduling_strategy,
            ),
            memory=SimpleNamespace(
                window_size=12,
                get_context_creator=lambda: SimpleNamespace(token_limit=4096),
            ),
            _output_language="Chinese",
            response_terminators=["DONE"],
            max_iteration=6,
            tool_execution_timeout=18,
            prune_tool_calls_from_memory=True,
            on_request_usage=None,
            stream_accumulate=True,
            _clone_tools=lambda: (tools, ["register-me"]),
        )

    def test_run_subagent_returns_completed_result(
        self, toolkit, parent_agent
    ):
        toolkit.register_agent(parent_agent)

        result = toolkit.agent_run_subagent(
            prompt="Research Eigent AI",
            description="Research Eigent AI",
            subagent_type="research",
        )

        assert result["created"] is True
        assert result["agent_id"] == "fake-agent-1"
        assert result["status"] == "completed"
        assert result["result"] == "handled::Research Eigent AI"
        assert result["error"] is None
        assert toolkit._sessions["fake-agent-1"].turns == 1

    def test_run_subagent_resumes_existing_session(
        self, toolkit, parent_agent
    ):
        toolkit.register_agent(parent_agent)

        first = toolkit.agent_run_subagent(
            prompt="First task",
            description="Deep analysis",
            subagent_type="analysis",
        )
        second = toolkit.agent_run_subagent(
            prompt="Continue the same task",
            agent_id=first["agent_id"],
        )

        assert first["agent_id"] == second["agent_id"]
        assert second["created"] is False
        assert len(FakeChatAgent.created_agents) == 1
        assert FakeChatAgent.created_agents[0].prompts == [
            "First task",
            "Continue the same task",
        ]

    def test_run_subagent_without_wait_returns_running_task(
        self, toolkit, parent_agent
    ):
        FakeChatAgent.delay_seconds = 0.3
        toolkit.register_agent(parent_agent)

        task = toolkit.agent_run_subagent(
            prompt="Slow task",
            description="Background-style polling task",
            wait=False,
        )

        assert task["created"] is True
        assert task["status"] == "running"

    def test_get_task_output_supports_polling_and_blocking(
        self, toolkit, parent_agent
    ):
        FakeChatAgent.delay_seconds = 0.2
        toolkit.register_agent(parent_agent)

        task = toolkit.agent_run_subagent(
            prompt="Poll later",
            description="Polling task",
            wait=False,
        )
        initial = toolkit.agent_get_task_output(task["task_id"], block=False)
        final = toolkit.agent_get_task_output(
            task["task_id"], block=True, timeout=1.0
        )

        assert initial["status"] == "running"
        assert final["status"] == "completed"
        assert final["result"] == "handled::Poll later"

    def test_inherits_all_parent_tools_by_default(self, toolkit, parent_agent):
        toolkit.register_agent(parent_agent)

        toolkit.agent_run_subagent(
            prompt="Use every parent tool",
            description="All tools",
        )

        created_agent = FakeChatAgent.created_agents[0]
        tools = created_agent.kwargs["tools"]
        assert sorted(tool.get_function_name() for tool in tools) == [
            "parent_calc",
            "parent_search",
        ]
        assert created_agent.kwargs["toolkits_to_register_agent"] == [
            "register-me"
        ]

    def test_stop_running_task(self, toolkit, parent_agent):
        FakeChatAgent.delay_seconds = 0.5
        toolkit.register_agent(parent_agent)

        task = toolkit.agent_run_subagent(
            prompt="Long running task",
            description="Coding task",
            timeout=0.0,
        )
        stopped = toolkit.agent_stop_task(task["task_id"])
        output = self._wait_task(toolkit, task["task_id"])

        assert stopped["status"] in {"stopping", "stopped"}
        assert output.status == "stopped"
        assert output.result == "stopped::Long running task"

    def test_empty_prompt_rejected(self, toolkit, parent_agent):
        toolkit.register_agent(parent_agent)

        for bad_prompt in ["", "   ", None]:
            result = toolkit.agent_run_subagent(
                prompt=bad_prompt,
                description="test",
            )
            assert result["status"] == "failed"
            assert "empty" in result["error"].lower()

    def test_unknown_agent_id_returns_error(self, toolkit):
        toolkit._agent = SimpleNamespace()

        result = toolkit.agent_run_subagent(
            prompt="Continue",
            agent_id="missing-agent",
        )

        assert result["status"] == "failed"
        assert "No sub-agent session found" in result["error"]

    def test_purge_evicts_oldest_finished_tasks_when_limit_exceeded(
        self, toolkit, parent_agent
    ):
        toolkit.register_agent(parent_agent)
        toolkit._MAX_FINISHED_TASKS = 4

        ids = []
        for i in range(6):
            result = toolkit.agent_run_subagent(prompt=f"task-{i}")
            ids.append(result["task_id"])

        # oldest tasks should have been purged
        for task_id in ids[:2]:
            assert task_id not in toolkit._tasks
        # recent tasks should still exist
        for task_id in ids[2:]:
            assert toolkit._tasks[task_id].status == "completed"

    def test_requires_parent_agent(self, toolkit):
        result = toolkit.agent_run_subagent(
            prompt="Research Eigent AI",
            description="Research Eigent AI",
            subagent_type="research",
        )

        assert result["status"] == "failed"
        assert "must be registered" in result["error"]

    def test_wait_with_timeout_returns_running_on_expiry(
        self, toolkit, parent_agent
    ):
        FakeChatAgent.delay_seconds = 1.0
        toolkit.register_agent(parent_agent)

        result = toolkit.agent_run_subagent(
            prompt="Slow task",
            description="Timeout test",
            wait=True,
            timeout=0.05,
        )

        assert result["status"] == "running"

    def test_get_output_unknown_task_id_returns_error(
        self, toolkit, parent_agent
    ):
        toolkit.register_agent(parent_agent)

        result = toolkit.agent_get_task_output("missing-task-id")

        assert result["status"] == "failed"
        assert "No sub-agent task found" in result["error"]
