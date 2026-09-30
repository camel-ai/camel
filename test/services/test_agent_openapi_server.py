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

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from camel.messages import BaseMessage
from camel.services.agent_openapi_server import ChatAgentOpenAPIServer
from camel.toolkits import FunctionTool, SearchToolkit

TEST_API_KEY = "test-key-12345"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest.fixture(autouse=True)
def _fake_model_api_key(monkeypatch):
    r"""ModelFactory must not require real provider credentials here."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-placeholder")


@pytest.fixture
def client_with_tool():
    r"""Creates an authenticated FastAPI test client with a registered
    tool."""
    tool = FunctionTool(SearchToolkit().search_wiki)
    server = ChatAgentOpenAPIServer(
        tool_registry={"search_wiki": [tool]},
        api_keys=[TEST_API_KEY],
    )
    client = TestClient(server.get_app(), headers=AUTH_HEADERS)
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
    server = ChatAgentOpenAPIServer(
        tool_registry=tool_registry, api_keys=[TEST_API_KEY]
    )
    app = server.get_app()

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Init
        resp = await ac.post(
            "/v1/agents/init",
            headers=AUTH_HEADERS,
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
            headers=AUTH_HEADERS,
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


# ----------------------------------------------
# API-key authentication and agent ownership
# (issues #4352)
# ----------------------------------------------
def _client_with_keys(*keys: str) -> TestClient:
    r"""Creates an unauthenticated-wrapped client for the given keys."""
    server = ChatAgentOpenAPIServer(api_keys=list(keys))
    return TestClient(server.get_app())


def test_missing_api_key_rejected():
    r"""Requests without any key must be rejected with 401."""
    client = _client_with_keys("secret-key")

    for method, url in [
        ("post", "/v1/agents/init"),
        ("get", "/v1/agents/list_agent_ids"),
        ("get", "/v1/agents/history/whatever"),
        ("post", "/v1/agents/step/whatever"),
        ("post", "/v1/agents/astep/whatever"),
        ("post", "/v1/agents/reset/whatever"),
        ("post", "/v1/agents/delete/whatever"),
    ]:
        kwargs = {"json": {"input_message": "hi"}} if method == "post" else {}
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, url


def test_invalid_api_key_rejected():
    r"""Requests with a wrong key must be rejected with 401."""
    client = _client_with_keys("secret-key")

    response = client.get(
        "/v1/agents/list_agent_ids",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_bearer_and_header_auth_both_accepted():
    r"""Both Authorization: Bearer and X-API-Key authenticate."""
    client = _client_with_keys("secret-key")

    for headers in (
        {"Authorization": "Bearer secret-key"},
        {"X-API-Key": "secret-key"},
    ):
        response = client.get("/v1/agents/list_agent_ids", headers=headers)
        assert response.status_code == 200


def test_generated_api_key_authenticates_when_none_configured():
    r"""With api_keys=None the server mints an ephemeral key that works."""
    server = ChatAgentOpenAPIServer()
    assert server.api_key  # an ephemeral key was generated

    client = TestClient(server.get_app())
    response = client.get("/v1/agents/list_agent_ids")
    assert response.status_code == 401

    client = TestClient(
        server.get_app(), headers={"X-API-Key": server.api_key}
    )
    response = client.get("/v1/agents/list_agent_ids")
    assert response.status_code == 200
    assert response.json() == {"agent_ids": []}


def test_empty_api_keys_disables_auth():
    r"""api_keys=[] explicitly runs the legacy unauthenticated mode."""
    server = ChatAgentOpenAPIServer(api_keys=[])
    client = TestClient(server.get_app())

    response = client.get("/v1/agents/list_agent_ids")
    assert response.status_code == 200


def test_agent_inventory_not_disclosed_across_owners():
    r"""list_agent_ids only reports the caller's own agents (issue #4352)."""
    server = ChatAgentOpenAPIServer(api_keys=["alice-key", "bob-key"])
    alice = TestClient(server.get_app(), headers={"X-API-Key": "alice-key"})
    bob = TestClient(server.get_app(), headers={"X-API-Key": "bob-key"})

    alice.post("/v1/agents/init", json={"agent_id": "alice_agent"})
    bob.post("/v1/agents/init", json={"agent_id": "bob_agent"})

    assert alice.get("/v1/agents/list_agent_ids").json() == {
        "agent_ids": ["alice_agent"]
    }
    assert bob.get("/v1/agents/list_agent_ids").json() == {
        "agent_ids": ["bob_agent"]
    }


def test_cross_owner_access_returns_404():
    r"""One owner's agent is invisible to another owner (issue #4352)."""
    server = ChatAgentOpenAPIServer(api_keys=["alice-key", "bob-key"])
    alice = TestClient(server.get_app(), headers={"X-API-Key": "alice-key"})
    bob = TestClient(server.get_app(), headers={"X-API-Key": "bob-key"})

    alice.post("/v1/agents/init", json={"agent_id": "victim"})

    for method, url in [
        ("get", "/v1/agents/history/victim"),
        ("post", "/v1/agents/reset/victim"),
        ("post", "/v1/agents/delete/victim"),
        ("post", "/v1/agents/step/victim"),
        ("post", "/v1/agents/astep/victim"),
    ]:
        kwargs = {"json": {"input_message": "hi"}} if method == "post" else {}
        response = getattr(bob, method)(url, **kwargs)
        assert response.status_code == 404, url

    # The agent still works for its owner.
    response = alice.get("/v1/agents/history/victim")
    assert response.status_code == 200


def test_cross_owner_history_content_not_disclosed():
    r"""The owner's system prompt must not leak via history (issue #4352)."""
    server = ChatAgentOpenAPIServer(api_keys=["alice-key", "bob-key"])
    alice = TestClient(server.get_app(), headers={"X-API-Key": "alice-key"})
    bob = TestClient(server.get_app(), headers={"X-API-Key": "bob-key"})

    secret = "The production VPN password is Vpn-Poc#Marker92."
    alice.post(
        "/v1/agents/init",
        json={"agent_id": "victim", "system_message": secret},
    )

    leaked = bob.get("/v1/agents/history/victim")
    assert leaked.status_code == 404
    assert secret not in leaked.text


def test_cross_owner_init_conflicts_with_409():
    r"""A second owner cannot silently adopt an existing agent id."""
    server = ChatAgentOpenAPIServer(api_keys=["alice-key", "bob-key"])
    alice = TestClient(server.get_app(), headers={"X-API-Key": "alice-key"})
    bob = TestClient(server.get_app(), headers={"X-API-Key": "bob-key"})

    alice.post("/v1/agents/init", json={"agent_id": "shared"})

    response = bob.post("/v1/agents/init", json={"agent_id": "shared"})
    assert response.status_code == 409

    # Same owner idempotently gets the existing agent back.
    response = alice.post("/v1/agents/init", json={"agent_id": "shared"})
    assert response.status_code == 200
    assert "already exists" in response.json()["message"]


def test_delete_removes_agent_and_allows_recreate():
    r"""Deleting frees the id for the same owner afterwards."""
    client = _client_with_keys("secret-key")
    headers = {"X-API-Key": "secret-key"}

    client.post("/v1/agents/init", json={"agent_id": "tmp"}, headers=headers)
    response = client.post("/v1/agents/delete/tmp", headers=headers)
    assert response.status_code == 200

    response = client.post(
        "/v1/agents/init", json={"agent_id": "tmp"}, headers=headers
    )
    assert response.status_code == 200
    assert "initialized" in response.json()["message"]


def test_non_ascii_api_key_header_rejected():
    r"""A non-ASCII header value must 401, not crash the handler."""
    client = _client_with_keys("secret-key")

    # Raw latin-1 bytes, as a non-conforming client would put on the
    # wire (httpx itself refuses str header values outside ASCII).
    wire_value = "ñ-üñï".encode("latin-1")

    response = client.get(
        "/v1/agents/list_agent_ids",
        headers={"X-API-Key": wire_value},
    )

    assert response.status_code == 401


def test_authenticated_missing_agent_returns_404():
    r"""A valid key querying an id that never existed gets a bare 404."""
    client = _client_with_keys("secret-key")
    headers = {"X-API-Key": "secret-key"}

    for method, url in [
        ("get", "/v1/agents/history/never-existed"),
        ("post", "/v1/agents/reset/never-existed"),
        ("post", "/v1/agents/delete/never-existed"),
    ]:
        kwargs = {"json": {"input_message": "hi"}} if method == "post" else {}
        response = getattr(client, method)(url, headers=headers, **kwargs)
        assert response.status_code == 404, url


def test_open_mode_shares_one_identity():
    r"""With authentication disabled every caller reaches every agent —
    the documented single-user semantics of api_keys=[]."""
    server = ChatAgentOpenAPIServer(api_keys=[])
    first = TestClient(server.get_app())
    second = TestClient(server.get_app())

    first.post("/v1/agents/init", json={"agent_id": "shared"})

    assert second.post("/v1/agents/reset/shared").status_code == 200
    assert first.get("/v1/agents/list_agent_ids").json() == {
        "agent_ids": ["shared"]
    }


def test_401_carries_www_authenticate_header():
    r"""401 responses advertise the Bearer scheme (RFC 6750)."""
    client = _client_with_keys("secret-key")

    response = client.get("/v1/agents/list_agent_ids")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# ----------------------------------------------
# Coverage: registry lookup, HTTPException re-raise guards, key encoding
# ----------------------------------------------
def test_init_returns_400_for_unknown_tool():
    r"""A tools_names entry missing from the registry is a 400."""
    client = _client_with_keys("secret-key")
    headers = {"X-API-Key": "secret-key"}

    response = client.post(
        "/v1/agents/init",
        json={
            "agent_id": "tool-agent",
            "tools_names": ["no_such_tool"],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "not found in registry" in response.json()["detail"]


def test_init_resolves_registered_tool():
    r"""A tools_names entry present in the registry initializes cleanly."""

    def dummy_tool(q: str) -> str:
        """Dummy tool for registry lookup."""
        return q

    server = ChatAgentOpenAPIServer(
        tool_registry={"dummy_tool": [FunctionTool(dummy_tool)]},
        api_keys=["secret-key"],
    )
    client = TestClient(server.get_app(), headers={"X-API-Key": "secret-key"})

    response = client.post(
        "/v1/agents/init",
        json={
            "agent_id": "tool-agent",
            "tools_names": ["dummy_tool"],
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Agent initialized."


def test_keys_equal_never_raises_on_unencodable_values():
    r"""Lone surrogates cannot be UTF-8 encoded; _keys_equal treats them
    as unequal instead of raising."""
    server = ChatAgentOpenAPIServer(api_keys=["secret-key"])

    assert server._keys_equal("\ud800", "\ud800") is False
    assert server._keys_equal("a", "\ud800") is False
    assert server._keys_equal("a", "a") is True


def _patched_agent_cls(step_side_effect):
    """Build a ChatAgent stand-in whose step/astep raise as instructed."""

    class _FakeAgent:
        def __init__(self, **_: object) -> None:
            pass

        @staticmethod
        def _raise():
            raise HTTPException(status_code=409, detail="in-flight conflict")

        def step(self, *, input_message, response_format=None):
            self._raise()

        async def astep(self, *, input_message, response_format=None):
            self._raise()

    return _FakeAgent, step_side_effect


def test_step_reraises_http_exception_from_agent():
    r"""An HTTPException raised mid-step propagates with its status code
    instead of being flattened into a 500."""

    class _FakeAgent:
        def __init__(self, **_: object) -> None:
            pass

        def step(self, *, input_message, response_format=None):
            raise HTTPException(status_code=409, detail="conflict-test")

    server = ChatAgentOpenAPIServer(api_keys=["secret-key"])
    client = TestClient(server.get_app(), headers={"X-API-Key": "secret-key"})

    with client:
        with patch(
            "camel.services.agent_openapi_server.ChatAgent", _FakeAgent
        ):
            client.post("/v1/agents/init", json={"agent_id": "conflict-agent"})
            response = client.post(
                "/v1/agents/step/conflict-agent",
                json={"input_message": "hi"},
            )

    assert response.status_code == 409
    assert "conflict-test" in response.json()["detail"]


def test_astep_reraises_http_exception_from_agent():
    r"""Same re-raise contract for the async step endpoint."""

    class _FakeAgent:
        def __init__(self, **_: object) -> None:
            pass

        async def astep(self, *, input_message, response_format=None):
            raise HTTPException(status_code=409, detail="conflict-test")

        def step(self, *, input_message, response_format=None):
            raise AssertionError("sync step must not run")

    server = ChatAgentOpenAPIServer(api_keys=["secret-key"])
    client = TestClient(server.get_app(), headers={"X-API-Key": "secret-key"})

    with client:
        with patch(
            "camel.services.agent_openapi_server.ChatAgent", _FakeAgent
        ):
            client.post("/v1/agents/init", json={"agent_id": "conflict-agent"})
            response = client.post(
                "/v1/agents/astep/conflict-agent",
                json={"input_message": "hi"},
            )

    assert response.status_code == 409
    assert "conflict-test" in response.json()["detail"]
