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
import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

from camel.runtimes.base import _auth_headers, _resolve_api_key

ADD_BODY = {"args": [1, 2], "kwargs": {}, "redirect_stdout": False}


def _load_api(monkeypatch, api_key):
    r"""Import `camel.runtimes.api` with one toolkit registered.

    The module reads its configuration from ``sys.argv`` and the environment
    at import time, so each case reloads it under a patched environment.
    """
    monkeypatch.setattr(sys, "argv", ["api.py", "camel.toolkits.MathToolkit"])
    if api_key is None:
        monkeypatch.delenv("CAMEL_RUNTIME_API_KEY", raising=False)
    else:
        monkeypatch.setenv("CAMEL_RUNTIME_API_KEY", api_key)
    monkeypatch.delenv("CAMEL_RUNTIME", raising=False)

    api = importlib.import_module("camel.runtimes.api")
    api = importlib.reload(api)
    assert "math_add" in api._registered_endpoints
    return api


def _reload_api_after_failure():
    r"""Leave `camel.runtimes.api` importable for whatever test runs next.

    A reload that raises leaves the module object in a half-initialised state,
    so put a usable one back.
    """
    os.environ["CAMEL_RUNTIME_API_KEY"] = "cleanup-key"
    sys.argv = ["api.py", "camel.toolkits.MathToolkit"]
    importlib.reload(importlib.import_module("camel.runtimes.api"))
    del os.environ["CAMEL_RUNTIME_API_KEY"]


def test_tool_endpoint_requires_a_key(monkeypatch):
    api = _load_api(monkeypatch, "secret-key")
    client = TestClient(api.app)

    resp = client.post("/math_add", json=ADD_BODY)

    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"


def test_tool_endpoint_rejects_a_wrong_key(monkeypatch):
    api = _load_api(monkeypatch, "secret-key")
    client = TestClient(api.app)

    resp = client.post(
        "/math_add", json=ADD_BODY, headers={"X-API-Key": "secret-ke"}
    )

    assert resp.status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"X-API-Key": "secret-key"},
        {"Authorization": "Bearer secret-key"},
        {"authorization": "bearer secret-key"},
    ],
)
def test_tool_endpoint_accepts_a_valid_key(monkeypatch, headers):
    api = _load_api(monkeypatch, "secret-key")
    client = TestClient(api.app)

    resp = client.post("/math_add", json=ADD_BODY, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["output"] == "3"


def test_health_requires_a_key(monkeypatch):
    r"""`/health` lists the loaded toolkits, so it is not public either."""
    api = _load_api(monkeypatch, "secret-key")
    client = TestClient(api.app)

    assert client.get("/health").status_code == 401
    authorized = client.get("/health", headers={"X-API-Key": "secret-key"})
    assert authorized.status_code == 200
    assert authorized.json()["endpoints"] == api._registered_endpoints


def test_any_of_several_configured_keys_is_accepted(monkeypatch):
    api = _load_api(monkeypatch, "first-key, second-key")
    client = TestClient(api.app)

    for key in ("first-key", "second-key"):
        resp = client.post(
            "/math_add", json=ADD_BODY, headers={"X-API-Key": key}
        )
        assert resp.status_code == 200


def test_unset_key_refuses_to_start(monkeypatch):
    r"""Rather than invent a key it would then have to log somewhere."""
    try:
        with pytest.raises(
            RuntimeError, match="CAMEL_RUNTIME_API_KEY is not set"
        ):
            _load_api(monkeypatch, None)
    finally:
        _reload_api_after_failure()


def test_empty_key_disables_authentication(monkeypatch):
    api = _load_api(monkeypatch, "")
    client = TestClient(api.app)

    assert api._API_KEYS == []
    assert client.post("/math_add", json=ADD_BODY).status_code == 200


def test_keys_equal(monkeypatch):
    api = _load_api(monkeypatch, "secret-key")

    assert api._keys_equal("abc", "abc")
    assert not api._keys_equal("abc", "abz")
    assert not api._keys_equal("abc", "abcd")
    # A header can hold characters that compare_digest will not take as
    # str, so these must return an answer instead of raising.
    assert api._keys_equal("ké", "ké")
    assert not api._keys_equal("ké", "abc")


def test_resolve_api_key_prefers_the_explicit_value(monkeypatch):
    monkeypatch.setenv("CAMEL_RUNTIME_API_KEY", "from-env")
    assert _resolve_api_key("explicit") == "explicit"


def test_resolve_api_key_falls_back_to_the_environment(monkeypatch):
    monkeypatch.setenv("CAMEL_RUNTIME_API_KEY", "from-env")
    assert _resolve_api_key() == "from-env"


def test_resolve_api_key_honours_an_explicit_empty_value(monkeypatch):
    monkeypatch.setenv("CAMEL_RUNTIME_API_KEY", "")
    assert _resolve_api_key() == ""
    assert _resolve_api_key("") == ""


def test_resolve_api_key_generates_a_distinct_key_when_unconfigured(
    monkeypatch,
):
    monkeypatch.delenv("CAMEL_RUNTIME_API_KEY", raising=False)
    first, second = _resolve_api_key(), _resolve_api_key()
    assert len(first) >= 32
    assert first != second


def test_auth_headers():
    assert _auth_headers("k") == {"X-API-Key": "k"}
    assert _auth_headers("") == {}


def test_remote_http_runtime_sends_its_key(monkeypatch):
    from camel.runtimes import RemoteHttpRuntime
    from camel.toolkits import MathToolkit

    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"output": "3"}

    def fake_post(url, json, headers):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse()

    runtime = RemoteHttpRuntime("localhost", api_key="shared-key").add(
        MathToolkit().get_tools(), "camel.toolkits.MathToolkit"
    )
    monkeypatch.setattr(
        "camel.runtimes.remote_http_runtime.requests.post", fake_post
    )

    math_add = runtime.tools_map["math_add"]
    assert math_add.func(1, 2) == 3
    assert captured["headers"] == {"X-API-Key": "shared-key"}


def test_remote_http_runtime_passes_its_key_to_the_server(monkeypatch):
    from camel.runtimes import RemoteHttpRuntime

    captured = {}

    def fake_popen(cmd, env):
        captured["env"] = env

        class FakeProcess:
            @staticmethod
            def poll():
                return 0

        return FakeProcess()

    monkeypatch.setattr(
        "camel.runtimes.remote_http_runtime.subprocess.Popen", fake_popen
    )
    RemoteHttpRuntime("localhost", api_key="shared-key").build()

    assert captured["env"]["CAMEL_RUNTIME_API_KEY"] == "shared-key"
    # The rest of the parent environment must survive, since the server needs
    # it (PATH, provider credentials, and so on).
    assert "PATH" in captured["env"] or "Path" in captured["env"]


def test_docker_runtime_sends_its_key(monkeypatch):
    pytest.importorskip("docker")
    from camel.runtimes import DockerRuntime
    from camel.toolkits import MathToolkit

    class FakeImages:
        @staticmethod
        def list(name):
            return [name]

    class FakeClient:
        images = FakeImages()

    monkeypatch.setattr("docker.from_env", lambda: FakeClient())

    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"output": "3"}

    def fake_post(url, json, headers):
        captured["headers"] = headers
        return FakeResponse()

    runtime = DockerRuntime("some-image", api_key="shared-key").add(
        MathToolkit().get_tools(), "camel.toolkits.MathToolkit"
    )
    monkeypatch.setattr(
        "camel.runtimes.docker_runtime.requests.post", fake_post
    )

    math_add = runtime.tools_map["math_add"]
    assert math_add.func(1, 2) == 3
    assert captured["headers"] == {"X-API-Key": "shared-key"}
