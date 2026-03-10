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

from types import SimpleNamespace

import httpx

from camel.toolkits.web_fetch_toolkit import WebFetchToolkit


class FakeChatAgent:
    last_prompt = None
    reset_count = 0

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def step(self, prompt):
        FakeChatAgent.last_prompt = prompt
        return SimpleNamespace(msgs=[SimpleNamespace(content="summary")])

    def reset(self):
        FakeChatAgent.reset_count += 1


def _fake_get(self, url):
    request = httpx.Request("GET", url)
    return httpx.Response(
        200,
        request=request,
        headers={"content-type": "text/html"},
        text=(
            "<html><body><h1>Pricing</h1>"
            "<p>Free</p><p>Pro</p></body></html>"
        ),
    )


def test_web_fetch_analyzes_page(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_get)
    monkeypatch.setattr("camel.agents.ChatAgent", FakeChatAgent, raising=False)

    toolkit = WebFetchToolkit(default_model="test-model")
    result = toolkit.web_fetch_and_analyze(
        url="https://example.com/pricing",
        prompt="Extract the pricing tiers",
    )

    assert result == "summary"
    assert "Extract the pricing tiers" in FakeChatAgent.last_prompt
    assert "Pricing Free Pro" in FakeChatAgent.last_prompt


def test_web_fetch_reuses_agent_with_reset(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_get)
    monkeypatch.setattr("camel.agents.ChatAgent", FakeChatAgent, raising=False)
    FakeChatAgent.reset_count = 0

    toolkit = WebFetchToolkit(default_model="test-model")
    toolkit.web_fetch_and_analyze(url="https://example.com/a", prompt="first")
    toolkit.web_fetch_and_analyze(url="https://example.com/b", prompt="second")

    assert FakeChatAgent.reset_count == 1


def test_web_fetch_tool_name():
    toolkit = WebFetchToolkit(default_model="test-model")
    tool = toolkit.get_tools()[0]

    assert tool.get_function_name() == "web_fetch_and_analyze"


def test_web_fetch_returns_error_when_no_model(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_get)

    toolkit = WebFetchToolkit(default_model=None)
    result = toolkit.web_fetch_and_analyze(
        url="https://example.com",
        prompt="Summarize the page",
    )

    assert result.startswith("Error:")


def test_web_fetch_rejects_non_http_scheme():
    toolkit = WebFetchToolkit(default_model="test-model")
    result = toolkit.web_fetch_and_analyze(
        url="file:///etc/passwd",
        prompt="read it",
    )

    assert result.startswith("Error:")
    assert "not allowed" in result


def test_web_fetch_handles_http_error(monkeypatch):
    def fake_get_500(self, url):
        request = httpx.Request("GET", url)
        return httpx.Response(500, request=request)

    monkeypatch.setattr(httpx.Client, "get", fake_get_500)

    toolkit = WebFetchToolkit(default_model="test-model")
    result = toolkit.web_fetch_and_analyze(
        url="https://example.com",
        prompt="Summarize",
    )

    assert result.startswith("Error:")
    assert "500" in result


def test_web_fetch_handles_plain_text(monkeypatch):
    def fake_get_text(self, url):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/plain"},
            text="Hello world",
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get_text)
    monkeypatch.setattr("camel.agents.ChatAgent", FakeChatAgent, raising=False)

    toolkit = WebFetchToolkit(default_model="test-model")
    result = toolkit.web_fetch_and_analyze(
        url="https://example.com/data.txt",
        prompt="Summarize",
    )

    assert result == "summary"
    assert "Hello world" in FakeChatAgent.last_prompt
