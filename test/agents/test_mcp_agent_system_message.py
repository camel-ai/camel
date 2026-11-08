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
import sys

from camel.agents import MCPAgent
from camel.models import BaseModelBackend
from camel.types import ModelType

FULL_TOOL_PROMPT = (
    "You are a helpful assistant, and you prefer "
    "to use tools provided by the user to solve problems."
)


class _StubBackend(BaseModelBackend):
    r"""Offline backend stub so the agent can be built without API keys."""

    @property
    def token_counter(self):
        return None

    def _run(self, messages, response_format=None, tools=None):
        raise RuntimeError("no network access in this test")

    async def _arun(self, messages, response_format=None, tools=None):
        raise RuntimeError("no network access in this test")


def _make_agent(function_calling_available: bool) -> MCPAgent:
    r"""Build an MCPAgent with a never-connected dummy stdio server so the
    toolkit can be initialized offline (no process is spawned until
    ``connect()`` is called)."""
    return MCPAgent(
        model=_StubBackend(ModelType.GPT_4O_MINI, model_config_dict={}),
        function_calling_available=function_calling_available,
        local_config={
            "mcpServers": {
                "dummy": {
                    "command": sys.executable,
                    "args": ["-c", "pass"],
                }
            }
        },
    )


def test_function_calling_system_message_is_complete() -> None:
    r"""The default system prompt for a function-calling MCPAgent must carry
    the complete instruction instead of ending mid-sentence."""
    agent = _make_agent(function_calling_available=True)

    assert agent.system_message is not None
    assert agent.system_message.content == FULL_TOOL_PROMPT


def test_text_mode_system_message_uses_detailed_prompt() -> None:
    r"""The text-mode branch must keep using the detailed routing prompt."""
    agent = _make_agent(function_calling_available=False)

    assert agent.system_message is not None
    assert "server_idx" in agent.system_message.content
