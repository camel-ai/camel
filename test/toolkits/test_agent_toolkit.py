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

        return SimpleNamespace(
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
            _clone_tools=lambda: (["parent-tool"], ["register-me"]),
        )

    def test_spawns_subagent_and_returns_result(self, toolkit, parent_agent):
        """New sub-agent is created, executes prompt, and returns output."""
        toolkit.register_agent(parent_agent)
        result = toolkit.agent_run_subagent(
            prompt="Research Eigent AI",
            description="Research Eigent AI",
            subagent_type="research",
        )

        assert result["created"] is True
        assert result["agent_id"] == "fake-agent-1"
        assert result["task_id"]
        assert result["subagent_type"] == "research"
        assert result["description"] == "Research Eigent AI"
        assert result["status"] in {"running", "completed"}

        output = toolkit.agent_get_task_output(result["task_id"], block=True)
        assert output["result"] == "handled::Research Eigent AI"
        assert output["status"] == "completed"
        assert toolkit._sessions["fake-agent-1"].turns == 1

    def test_resumes_existing_subagent(self, toolkit, parent_agent):
        """Passing agent_id reuses the same sub-agent
        with accumulated state."""
        toolkit.register_agent(parent_agent)
        first = toolkit.agent_run_subagent(
            prompt="First task",
            description="Deep analysis",
            subagent_type="analysis",
        )
        toolkit.agent_get_task_output(first["task_id"], block=True)
        second = toolkit.agent_run_subagent(
            prompt="Continue the same task",
            agent_id=first["agent_id"],
        )

        toolkit.agent_get_task_output(second["task_id"], block=True)

        assert first["agent_id"] == second["agent_id"]
        assert second["created"] is False
        assert len(FakeChatAgent.created_agents) == 1
        assert FakeChatAgent.created_agents[0].prompts == [
            "First task",
            "Continue the same task",
        ]
        assert toolkit._sessions[first["agent_id"]].turns == 2

    def test_error_for_unknown_agent_id(self, toolkit):
        """Resuming a non-existent agent_id returns a clear error."""
        toolkit._agent = SimpleNamespace()
        result = toolkit.agent_run_subagent(
            prompt="Continue",
            agent_id="missing-agent",
        )

        assert result["status"] == "failed"
        assert "No sub-agent session found" in result["error"]

    def test_requires_parent_agent(self, toolkit):
        """Spawning without a registered parent agent fails gracefully."""
        result = toolkit.agent_run_subagent(
            prompt="Research Eigent AI",
            description="Research Eigent AI",
            subagent_type="research",
        )

        assert result["status"] == "failed"
        assert "must be registered" in result["error"]

    def test_inherits_parent_config_with_shared_tools(
        self, toolkit, parent_agent
    ):
        """Sub-agent inherits model, tools, and settings from parent."""
        toolkit.share_parent_tools = True
        toolkit.register_agent(parent_agent)

        toolkit.agent_run_subagent(
            prompt="Implement the fix",
            description="Coding task",
            subagent_type="coding",
        )

        created_agent = FakeChatAgent.created_agents[0]
        assert created_agent.kwargs["model"] == "parent-model"
        assert created_agent.kwargs["tools"] == ["parent-tool"]
        assert created_agent.kwargs["toolkits_to_register_agent"] == [
            "register-me"
        ]
        assert created_agent.kwargs["output_language"] == "Chinese"
        assert created_agent.kwargs["message_window_size"] == 12
        assert created_agent.kwargs["token_limit"] == 4096

    def test_stop_running_task(self, toolkit, parent_agent):
        """A long-running task can be stopped via agent_stop_task."""
        FakeChatAgent.delay_seconds = 0.5
        toolkit.register_agent(parent_agent)

        task = toolkit.agent_run_subagent(
            prompt="Long running task",
            description="Coding task",
            subagent_type="coding",
        )
        stopped = toolkit.agent_stop_task(task["task_id"])
        output = toolkit.agent_get_task_output(task["task_id"], block=True)

        assert stopped["status"] in {"stopping", "stopped"}
        assert output["status"] == "stopped"
        assert output["result"] == "stopped::Long running task"

    def test_empty_prompt_rejected(self, toolkit, parent_agent):
        """An empty or whitespace-only prompt is rejected."""
        toolkit.register_agent(parent_agent)

        for bad_prompt in ["", "   ", None]:
            result = toolkit.agent_run_subagent(
                prompt=bad_prompt,
                description="test",
            )
            assert result["status"] == "failed"
            assert "empty" in result["error"].lower() or result["error"]

    def test_get_output_for_unknown_task_id(self, toolkit, parent_agent):
        """Querying a non-existent task_id returns an error."""
        toolkit.register_agent(parent_agent)

        result = toolkit.agent_get_task_output("nonexistent-task-id")

        assert result["status"] == "failed"
        assert "No sub-agent task found" in result["error"]

    def test_stop_unknown_task_id(self, toolkit, parent_agent):
        """Stopping a non-existent task_id returns an error."""
        toolkit.register_agent(parent_agent)

        result = toolkit.agent_stop_task("nonexistent-task-id")

        assert result["status"] == "failed"
        assert "No sub-agent task found" in result["error"]

    def test_stop_already_completed_task(self, toolkit, parent_agent):
        """Stopping an already-completed task reports it is not running."""
        toolkit.register_agent(parent_agent)
        task = toolkit.agent_run_subagent(
            prompt="Quick task",
            description="test",
        )
        toolkit.agent_get_task_output(task["task_id"], block=True)

        result = toolkit.agent_stop_task(task["task_id"])

        assert result["status"] == "completed"
        assert result["message"] == "Task is not running."

    def test_clone_for_new_session_has_no_old_state(
        self, toolkit, parent_agent
    ):
        """Cloned toolkit keeps config but drops all sessions and tasks."""
        toolkit.register_agent(parent_agent)
        toolkit.agent_run_subagent(
            prompt="Original task",
            description="test",
        )

        cloned = toolkit.clone_for_new_session()

        assert cloned._sessions == {}
        assert cloned._tasks == {}
        assert cloned.share_parent_tools == toolkit.share_parent_tools
        assert cloned.default_tools == toolkit.default_tools

    def test_default_tools_fallback(self, toolkit, parent_agent):
        """When share_parent_tools is False, default_tools are used."""

        def sentinel_tool():
            return None

        toolkit.default_tools = [sentinel_tool]
        toolkit.share_parent_tools = False
        toolkit.register_agent(parent_agent)

        toolkit.agent_run_subagent(
            prompt="Use default tools",
            description="test",
        )

        created_agent = FakeChatAgent.created_agents[0]
        assert created_agent.kwargs["tools"] == [sentinel_tool]
        assert created_agent.kwargs["toolkits_to_register_agent"] is None

    def test_get_output_nonblocking_returns_running(
        self, toolkit, parent_agent
    ):
        """Non-blocking get_output returns 'running' for an in-flight task."""
        FakeChatAgent.delay_seconds = 0.5
        toolkit.register_agent(parent_agent)

        task = toolkit.agent_run_subagent(
            prompt="Slow task",
            description="test",
        )
        output = toolkit.agent_get_task_output(task["task_id"], block=False)

        assert output["status"] == "running"
        assert output["result"] is None

        toolkit.agent_stop_task(task["task_id"])
        toolkit.agent_get_task_output(task["task_id"], block=True)
