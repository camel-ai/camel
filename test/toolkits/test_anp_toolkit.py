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
from unittest.mock import patch

import pytest

from camel.toolkits import ANPTool
from camel.toolkits.function_tool import FunctionTool


@pytest.fixture
def anp_toolkit():
    """Create an ANPTool instance with mocked authentication for testing."""
    with patch("agent_connect.authentication.DIDWbaAuthHeader") as mock_auth:
        toolkit = ANPTool()
        yield toolkit


def test_get_tools(anp_toolkit):
    """Test the get_tools method."""
    # Get the tools
    tools = anp_toolkit.get_tools()
    
    # Verify the result
    assert len(tools) == 1
    assert isinstance(tools[0], FunctionTool)
    assert callable(tools[0].func)
    
    # Verify the tool has the correct schema
    assert tools[0].openai_tool_schema["type"] == "function"
    assert tools[0].openai_tool_schema["function"]["name"] == "anp_tool"
    assert "description" in tools[0].openai_tool_schema["function"]


def test_tool_parameters():
    """Test the tool parameters structure."""
    # Verify the tool parameters
    assert ANPTool.parameters["type"] == "function"
    assert ANPTool.parameters["function"]["name"] == "anp_tool"
    assert "description" in ANPTool.parameters["function"]
    assert ANPTool.parameters["function"]["parameters"]["required"] == ["url"]
    
    # Verify parameter properties
    properties = ANPTool.parameters["function"]["parameters"]["properties"]
    assert "url" in properties
    assert "method" in properties
    assert "headers" in properties
    assert "params" in properties
    assert "body" in properties
    
    # Verify method enum values
    assert "GET" in properties["method"]["enum"]
    assert "POST" in properties["method"]["enum"]
    assert "PUT" in properties["method"]["enum"]
    assert "DELETE" in properties["method"]["enum"]
    assert "PATCH" in properties["method"]["enum"]
