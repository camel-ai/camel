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
from camel.models import ModelFactory
from camel.toolkits import SubAgentToolkit
from camel.types import ModelPlatformType, ModelType


class TestSubAgentToolkit:
    def test_sub_agent_toolkit_init(self):
        """Test SubAgentToolkit initialization."""
        toolkit = SubAgentToolkit()
        assert toolkit is not None
        assert hasattr(toolkit, 'spawn_sub_agent')

    def test_get_tools(self):
        """Test that get_tools returns the expected tools."""
        toolkit = SubAgentToolkit()
        tools = toolkit.get_tools()
        assert len(tools) == 1
        assert tools[0].func == toolkit.spawn_sub_agent

    def test_spawn_sub_agent_without_registered_agent(self):
        """Test that spawn_sub_agent returns error without registered agent."""
        toolkit = SubAgentToolkit()

        result = toolkit.spawn_sub_agent(
            task="test task", system_prompt="test prompt"
        )

        assert isinstance(result, str)
        assert result.startswith("Error:")
        assert "No parent agent registered" in result

    def test_spawn_sub_agent_invalid_params(self):
        """Test spawn_sub_agent with invalid parameters."""
        toolkit = SubAgentToolkit()

        # create a mock agent and register it
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )
        agent = ChatAgent(
            system_message="test agent",
            model=model,
        )
        toolkit.register_agent(agent)

        with pytest.raises(ValueError, match="Either inherit_from_parent"):
            toolkit.spawn_sub_agent(
                task="test task",
                inherit_from_parent=False,
                system_prompt=None,  # should cause error
            )

    @pytest.mark.model_backend
    def test_spawn_sub_agent_fresh(self):
        """Test spawning a fresh sub-agent."""
        toolkit = SubAgentToolkit()

        # create main agent
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )
        ChatAgent(
            system_message="You are a helpful assistant.",
            model=model,
            toolkits_to_register_agent=[toolkit],
            tools=toolkit.get_tools(),
        )

        # test fresh sub-agent spawning
        result = toolkit.spawn_sub_agent(
            task="What is 2+2?",
            inherit_from_parent=False,
            system_prompt="You are a math tutor.",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.model_backend
    def test_spawn_sub_agent_inherit(self):
        """Test spawning a sub-agent that inherits from parent."""
        toolkit = SubAgentToolkit()

        # create main agent
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )
        main_agent = ChatAgent(
            system_message="You are a helpful assistant.",
            model=model,
            toolkits_to_register_agent=[toolkit],
            tools=toolkit.get_tools(),
        )

        # give the main agent some context
        main_agent.step("Remember that we're discussing mathematics.")

        # test inheriting sub-agent spawning
        result = toolkit.spawn_sub_agent(
            task="What is 2+2?", inherit_from_parent=True
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.model_backend
    def test_sub_agent_integration(self):
        """Test full integration with ChatAgent using tool calls."""
        toolkit = SubAgentToolkit()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        main_agent = ChatAgent(
            system_message="You are a coordinator agent that can spawn "
            "sub-agents for specialized tasks.",
            model=model,
            toolkits_to_register_agent=[toolkit],
            tools=toolkit.get_tools(),
        )

        # test that main agent can use the toolkit via tool calls
        response = main_agent.step(
            "Use spawn_sub_agent to create a math specialist (fresh agent "
            "with system_prompt='You are a math expert') and ask it to "
            "calculate 15 * 23."
        )

        assert hasattr(response, 'msg')
        assert hasattr(response.msg, 'content')
        assert len(response.msg.content) > 0
