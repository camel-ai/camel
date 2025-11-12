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
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from camel.messages import BaseMessage
from camel.services.agent_openapi_server import ChatAgentOpenAPIServer
from camel.toolkits import FunctionTool, SearchToolkit


@pytest.fixture
def client_with_tool():
    r"""Creates a FastAPI test client with a registered tool."""
    tool = FunctionTool(SearchToolkit().search_wiki)
    server = ChatAgentOpenAPIServer(tool_registry={"search_wiki": [tool]})
    client = TestClient(server.get_app())
    return client


@pytest.mark.model_backend
def test_init_agent(client_with_tool):
    r"""Tests the /v1/agents/init endpoint initializes an agent correctly."""
    response = client_with_tool.post(
        "/v1/agents/init",
        json={
            "agent_id": "test_agent",
            "tools_names": ["search_wiki"],
            "system_message": "You are a helpful assistant.",
        },
    )
    assert response.status_code == 200
    assert response.json()["agent_id"] == "test_agent"


@pytest.mark.model_backend
def test_step_interaction(client_with_tool):
    r"""Tests /v1/agents/step returns a valid agent response with a tool."""
    client_with_tool.post(
        "/v1/agents/init",
        json={
            "agent_id": "test_agent",
            "tools_names": ["search_wiki"],
            "system_message": "You are a helpful assistant.",
        },
    )
    response = client_with_tool.post(
        "/v1/agents/step/test_agent",
        json={"input_message": "Search: What is machine learning?"},
    )
    result = response.json()
    assert response.status_code == 200
    assert isinstance(result, dict)
    assert "msgs" in result
    assert isinstance(result["msgs"], list)


@pytest.mark.model_backend
def test_get_history(client_with_tool):
    r"""Tests /v1/agents/history returns a list of message history."""
    client_with_tool.post(
        "/v1/agents/init",
        json={
            "agent_id": "test_agent",
            "tools_names": ["search_wiki"],
            "system_message": "You are a helpful assistant.",
        },
    )
    client_with_tool.post(
        "/v1/agents/step/test_agent",
        json={"input_message": "Search: What is machine learning?"},
    )
    history = client_with_tool.get("/v1/agents/history/test_agent")
    assert history.status_code == 200
    assert isinstance(history.json(), list)


def test_reset_agent(client_with_tool):
    r"""Tests /v1/agents/reset resets the agent successfully."""
    client_with_tool.post("/v1/agents/init", json={"agent_id": "test_agent"})
    response = client_with_tool.post("/v1/agents/reset/test_agent")
    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()


@pytest.mark.asyncio
@pytest.mark.model_backend
async def test_async_step_route_with_tool():
    r"""Tests the /v1/agents/astep endpoint with an async client.

    Initializes an agent with a tool and sends an async message to verify
    the full pipeline works, including tool invocation and message return.
    """

    # Lazily create the app with tool
    tool_registry = {
        "search_wiki": [FunctionTool(SearchToolkit().search_wiki)]
    }
    server = ChatAgentOpenAPIServer(tool_registry=tool_registry)
    app = server.get_app()

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Init
        resp = await ac.post(
            "/v1/agents/init",
            json={
                "agent_id": "demo",
                "tools_names": ["search_wiki"],
                "system_message": "You are a helpful assistant"
                " with wiki access.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "demo"

        # Step 2: Async step with tool
        resp = await ac.post(
            "/v1/agents/astep/demo",
            json={"input_message": "Search: What is machine learning?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("msgs"), list)
        assert any(
            "machine learning" in m["content"].lower()
            for m in data["msgs"]
            if "content" in m
        )


def test_parse_input_message_for_step_string():
    r"""Tests parsing a plain string input message."""
    server = ChatAgentOpenAPIServer()

    # Test string input
    result = server._parse_input_message_for_step("Hello, world!")

    assert isinstance(result, BaseMessage)
    assert result.content == "Hello, world!"
    assert result.role_name == "User"


def test_resolve_response_format_for_step():
    r"""Tests response format resolution with valid and invalid names."""

    # Create a dummy response format for testing
    class TestResponseFormat(BaseModel):
        message: str
        status: int

    # Server with registered response format
    server = ChatAgentOpenAPIServer(
        response_format_registry={"test_format": TestResponseFormat}
    )

    # Test None input (should return None)
    result = server._resolve_response_format_for_step(None)
    assert result is None

    # Test valid format name
    result = server._resolve_response_format_for_step("test_format")
    assert result == TestResponseFormat

    # Test invalid format name
    with pytest.raises(HTTPException) as exc_info:
        server._resolve_response_format_for_step("invalid_format")

    assert exc_info.value.status_code == 400
    assert "Unknown response_format: invalid_format" in str(
        exc_info.value.detail
    )
