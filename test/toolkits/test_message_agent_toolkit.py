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

from unittest.mock import Mock

from camel.toolkits.message_agent_toolkit import MessageAgentTool


class TestMessageAgentTool:
    """Test cases for MessageAgentTool."""

    def test_initialization_empty(self):
        """Test MessageAgentTool initialization with no agents."""
        toolkit = MessageAgentTool()
        assert toolkit.agents == {}
        assert len(toolkit.agents) == 0

    def test_initialization_with_agents(self):
        """Test MessageAgentTool initialization with predefined agents."""
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        agents = {"agent1": mock_agent1, "agent2": mock_agent2}

        toolkit = MessageAgentTool(agents=agents)
        assert toolkit.agents == agents
        assert len(toolkit.agents) == 2

    def test_register_agent_new(self):
        """Test registering a new agent."""
        toolkit = MessageAgentTool()
        mock_agent = Mock()

        result = toolkit.register_agent("test_agent", mock_agent)

        assert "test_agent" in toolkit.agents
        assert toolkit.agents["test_agent"] == mock_agent
        assert "registered successfully" in result.lower()

    def test_register_agent_overwrite(self):
        """Test overwriting an existing agent."""
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        toolkit = MessageAgentTool({"existing_agent": mock_agent1})

        result = toolkit.register_agent("existing_agent", mock_agent2)

        assert toolkit.agents["existing_agent"] == mock_agent2
        assert "registered successfully" in result.lower()

    def test_message_agent_success(self):
        """Test successful message sending to an agent."""
        mock_agent = Mock()
        mock_response = Mock()
        mock_response.msgs = [Mock(content="Hello back!")]
        mock_agent.step.return_value = mock_response

        toolkit = MessageAgentTool({"target_agent": mock_agent})

        result = toolkit.message_agent("Hello", "target_agent")

        mock_agent.step.assert_called_once_with("Hello")
        assert result == "Hello back!"

    def test_message_agent_success_string_response(self):
        """Test successful message sending with string response."""
        mock_agent = Mock()
        mock_agent.step.return_value = "Simple string response"

        toolkit = MessageAgentTool({"target_agent": mock_agent})

        result = toolkit.message_agent("Hello", "target_agent")

        mock_agent.step.assert_called_once_with("Hello")
        assert result == "Simple string response"

    def test_message_agent_not_found(self):
        """Test messaging a non-existent agent."""
        toolkit = MessageAgentTool()

        result = toolkit.message_agent("Hello", "nonexistent_agent")

        assert "Error" in result
        assert "not found" in result

    def test_message_agent_communication_error(self):
        """Test handling communication errors."""
        mock_agent = Mock()
        mock_agent.step.side_effect = Exception("Communication failed")

        toolkit = MessageAgentTool({"error_agent": mock_agent})

        result = toolkit.message_agent("Hello", "error_agent")

        assert "Error" in result
        assert "Failed to communicate" in result
        assert "Communication failed" in result

    def test_list_available_agents_empty(self):
        """Test listing agents when none are registered."""
        toolkit = MessageAgentTool()

        result = toolkit.list_available_agents()

        assert "No agents registered" in result

    def test_list_available_agents_with_agents(self):
        """Test listing agents when multiple agents are registered."""
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        agents = {"agent1": mock_agent1, "agent2": mock_agent2}
        toolkit = MessageAgentTool(agents)

        result = toolkit.list_available_agents()

        assert "Available agents:" in result
        assert "agent1" in result
        assert "agent2" in result

    def test_remove_agent_success(self):
        """Test successfully removing an agent."""
        mock_agent = Mock()
        toolkit = MessageAgentTool({"test_agent": mock_agent})

        result = toolkit.remove_agent("test_agent")

        assert "test_agent" not in toolkit.agents
        assert "removed successfully" in result.lower()

    def test_remove_agent_not_found(self):
        """Test removing a non-existent agent."""
        toolkit = MessageAgentTool()

        result = toolkit.remove_agent("nonexistent_agent")

        assert "Error" in result
        assert "not found" in result

    def test_get_agent_count_empty(self):
        """Test getting agent count when no agents are registered."""
        toolkit = MessageAgentTool()

        result = toolkit.get_agent_count()

        assert "Total registered agents: 0" in result

    def test_get_agent_count_with_agents(self):
        """Test getting agent count with multiple agents."""
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        mock_agent3 = Mock()
        agents = {
            "agent1": mock_agent1,
            "agent2": mock_agent2,
            "agent3": mock_agent3,
        }
        toolkit = MessageAgentTool(agents)

        result = toolkit.get_agent_count()

        assert "Total registered agents: 3" in result

    def test_get_tools_returns_correct_functions(self):
        """Test that get_tools returns all expected function tools."""
        toolkit = MessageAgentTool()

        tools = toolkit.get_tools()

        assert len(tools) == 5
        tool_names = [tool.get_function_name() for tool in tools]

        expected_functions = [
            "message_agent",
            "register_agent",
            "list_available_agents",
            "remove_agent",
            "get_agent_count",
        ]

        for expected_func in expected_functions:
            assert expected_func in tool_names

    def test_timeout_parameter(self):
        """Test initialization with timeout parameter."""
        toolkit = MessageAgentTool(timeout=30.0)

        assert toolkit.timeout == 30.0

    def test_agent_registration_flow(self):
        """Test complete agent registration and communication flow."""
        # Create toolkit
        toolkit = MessageAgentTool()

        # Register multiple agents
        mock_agent1 = Mock()
        mock_agent2 = Mock()

        # Set up mock responses
        mock_response1 = Mock()
        mock_response1.msgs = [Mock(content="Response from agent 1")]
        mock_agent1.step.return_value = mock_response1

        mock_response2 = Mock()
        mock_response2.msgs = [Mock(content="Response from agent 2")]
        mock_agent2.step.return_value = mock_response2

        # Register agents
        toolkit.register_agent("agent1", mock_agent1)
        toolkit.register_agent("agent2", mock_agent2)

        # Test agent count
        count_result = toolkit.get_agent_count()
        assert "2" in count_result

        # Test listing agents
        list_result = toolkit.list_available_agents()
        assert "agent1" in list_result
        assert "agent2" in list_result

        # Test messaging agents
        response1 = toolkit.message_agent("Hello agent 1", "agent1")
        assert response1 == "Response from agent 1"

        response2 = toolkit.message_agent("Hello agent 2", "agent2")
        assert response2 == "Response from agent 2"

        # Test removing agent
        remove_result = toolkit.remove_agent("agent1")
        assert "removed successfully" in remove_result.lower()
        assert "agent1" not in toolkit.agents
        assert "agent2" in toolkit.agents

        # Test final count
        final_count = toolkit.get_agent_count()
        assert "1" in final_count
