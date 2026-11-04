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
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from camel.toolkits import DarkmoonToolkit

BASE = "http://darkmoon.test"


def _make_toolkit(handler: Callable[[httpx.Request], httpx.Response]):
    toolkit = DarkmoonToolkit(
        base_url=BASE + "/", username="pentester", password="s3cret-pass"
    )
    toolkit._client = httpx.Client(transport=httpx.MockTransport(handler))
    return toolkit


class FakeDarkmoon:
    r"""A tiny in-memory Darkmoon Dashboard API."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.logins = 0
        self.campaigns: list[dict[str, Any]] = [{"id": "camp_old_1"}]
        self.log_events: list[dict[str, Any]] = []
        self.run_started = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/api/v1/auth/login":
            self.logins += 1
            body = json.loads(request.content)
            if body["password"] != "s3cret-pass":
                return httpx.Response(401, json={"detail": "bad credentials"})
            return httpx.Response(200, json={"token": "jwt-123"})
        if request.headers.get("Authorization") != "Bearer jwt-123":
            return httpx.Response(401, json={"detail": "not authenticated"})
        if path == "/api/v1/campaigns":
            return httpx.Response(200, json={"data": self.campaigns})
        if path == "/api/v1/vulnerabilities":
            cid = request.url.params["campaign_id"]
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "stats": {"high": 1},
                    "data": [{"title": "SQLi", "campaign": cid}],
                },
            )
        if path == "/api/v1/run/campaign":
            self.run_started = True
            self.params = json.loads(request.content)
            self.campaigns.append({"id": "camp_new_example.com"})
            return httpx.Response(200, json={"run_id": "run-1"})
        if path == "/api/v1/run/logs/run-1":
            if not self.log_events:
                return httpx.Response(404, json={"detail": "no log yet"})
            return httpx.Response(200, json={"data": self.log_events})
        return httpx.Response(404, json={"detail": "not found"})


def test_init_missing_credentials(monkeypatch):
    for name in (
        "DARKMOON_BASE_URL",
        "DARKMOON_USERNAME",
        "DARKMOON_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError):
        DarkmoonToolkit()


def test_init_reads_environment(monkeypatch):
    monkeypatch.setenv("DARKMOON_BASE_URL", "http://env.test/")
    monkeypatch.setenv("DARKMOON_USERNAME", "u")
    monkeypatch.setenv("DARKMOON_PASSWORD", "p")
    toolkit = DarkmoonToolkit()
    assert toolkit._base_url == "http://env.test"


def test_get_tools_names():
    toolkit = _make_toolkit(FakeDarkmoon())
    names = {tool.get_function_name() for tool in toolkit.get_tools()}
    assert names == {
        "darkmoon_run_pentest",
        "darkmoon_get_findings",
        "darkmoon_list_campaigns",
    }


def test_list_campaigns_logs_in_once_and_sends_bearer():
    api = FakeDarkmoon()
    toolkit = _make_toolkit(api)

    first = toolkit.darkmoon_list_campaigns()
    second = toolkit.darkmoon_list_campaigns()

    assert first == {"total": 1, "campaigns": [{"id": "camp_old_1"}]}
    assert second == first
    assert api.logins == 1
    assert api.requests[1].headers["Authorization"] == "Bearer jwt-123"


def test_get_findings_success():
    toolkit = _make_toolkit(FakeDarkmoon())

    result = toolkit.darkmoon_get_findings("camp 1/x")

    assert result["campaign_id"] == "camp 1/x"
    assert result["total"] == 1
    assert result["stats"] == {"high": 1}
    assert result["findings"][0]["campaign"] == "camp 1/x"


def test_get_findings_requires_campaign_id():
    toolkit = _make_toolkit(FakeDarkmoon())
    result = toolkit.darkmoon_get_findings("  ")
    assert isinstance(result, str) and "campaign_id is required" in result


def test_login_failure_does_not_leak_password():
    toolkit = DarkmoonToolkit(
        base_url=BASE, username="pentester", password="wrong-password"
    )
    toolkit._client = httpx.Client(
        transport=httpx.MockTransport(FakeDarkmoon())
    )

    result = toolkit.darkmoon_list_campaigns()

    assert isinstance(result, str)
    assert "401" in result and "bad credentials" in result
    assert "wrong-password" not in result


def test_network_error_is_returned_as_message():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    toolkit = _make_toolkit(boom)
    result = toolkit.darkmoon_list_campaigns()
    assert isinstance(result, str) and "connection refused" in result


def test_run_pentest_requires_target():
    toolkit = _make_toolkit(FakeDarkmoon())
    result = toolkit.darkmoon_run_pentest("   ")
    assert isinstance(result, str) and "target is required" in result


def test_run_pentest_no_wait_returns_run_id():
    api = FakeDarkmoon()
    toolkit = _make_toolkit(api)

    result = toolkit.darkmoon_run_pentest(
        "example.com",
        wait_for_completion=False,
        program="acme",
        focus="auth, injection",
        severity="high",
    )

    assert result == {
        "status": "started",
        "run_id": "run-1",
        "target": "example.com",
    }
    assert api.params == {
        "target": "example.com",
        "program": "acme",
        "focus": ["auth", "injection"],
        "severity": "high",
    }


def test_run_pentest_waits_and_returns_only_new_campaign_findings():
    api = FakeDarkmoon()
    api.log_events = [{"type": "tool_call"}, {"type": "run_completed"}]
    toolkit = _make_toolkit(api)

    result = toolkit.darkmoon_run_pentest(
        "example.com", poll_interval_seconds=0.01
    )

    assert result["run_id"] == "run-1"
    assert result["campaign_id"] == "camp_new_example.com"
    assert result["timed_out"] is False
    assert result["total"] == 1
    assert result["stats"] == {"high": 1}


def test_run_pentest_polls_until_log_appears(monkeypatch):
    api = FakeDarkmoon()
    toolkit = _make_toolkit(api)
    calls = {"n": 0}

    def fake_sleep(_: float) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            api.log_events = [{"type": "run_error"}]

    monkeypatch.setattr(
        "camel.toolkits.darkmoon_toolkit.time.sleep", fake_sleep
    )

    result = toolkit.darkmoon_run_pentest("example.com")

    assert calls["n"] == 2
    assert result["timed_out"] is False


def test_run_pentest_times_out_without_looping_forever():
    api = FakeDarkmoon()  # the run log never gets a terminal event
    toolkit = _make_toolkit(api)

    result = toolkit.darkmoon_run_pentest(
        "example.com", max_wait_seconds=0, poll_interval_seconds=0.01
    )

    assert result["timed_out"] is True


def test_run_pentest_ignores_stale_campaign():
    api = FakeDarkmoon()
    api.log_events = [{"type": "run_completed"}]
    toolkit = _make_toolkit(api)
    # The run produced no new campaign: the pre-existing one must not be
    # reported as this run's result.
    original = api.__call__

    def no_new_campaign(request: httpx.Request) -> httpx.Response:
        response = original(request)
        if request.url.path == "/api/v1/run/campaign":
            api.campaigns[:] = [{"id": "camp_old_1"}]
        return response

    toolkit._client = httpx.Client(
        transport=httpx.MockTransport(no_new_campaign)
    )

    result = toolkit.darkmoon_run_pentest(
        "example.com", poll_interval_seconds=0.01
    )

    assert result["campaign_id"] is None
    assert result["findings"] == []
