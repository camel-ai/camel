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
from unittest.mock import MagicMock, patch

import pytest
import requests

from camel.toolkits import APIVerveToolkit, FunctionTool
from camel.toolkits import apiverve_toolkit as module

API_KEY = "test-apiverve-key"

CATALOG = {
    "apis": {
        "emailvalidator": {
            "title": "Email Validator",
            "category": "Validation",
            "description": "Validate an email address",
            "method": "GET",
            "path": "/v1/emailvalidator",
            "params": [
                {
                    "name": "email",
                    "type": "string",
                    "required": True,
                    "in": "query",
                }
            ],
        },
        "vatrates": {
            "title": "VAT Rates",
            "category": "Finance",
            "description": "VAT rates by country",
            "method": "GET",
            "path": "/v1/vatrates",
            "params": [],
        },
        "gravatarlookup": {
            "title": "Gravatar Lookup",
            "category": "Social",
            "description": "Look up a Gravatar profile",
            "method": "GET",
            "path": "/v1/gravatarlookup",
            "params": [],
        },
        "texttopdf": {
            "title": "Text to PDF",
            "category": "Documents",
            "description": "Make a PDF",
            "method": "POST",
            "path": "/v1/texttopdf",
            "params": [
                {
                    "name": "text",
                    "type": "string",
                    "required": True,
                    "in": "body",
                },
                {"name": "title", "type": "string", "in": "query"},
            ],
        },
    }
}


def _response(status_code=200, body=None):
    response = MagicMock()
    response.status_code = status_code
    response.ok = status_code < 400
    response.json.return_value = body
    response.raise_for_status.side_effect = (
        requests.HTTPError(str(status_code)) if status_code >= 400 else None
    )
    return response


@pytest.fixture
def toolkit():
    return APIVerveToolkit(api_key=API_KEY)


@pytest.fixture
def catalog_get():
    with patch.object(
        module.requests, "get", return_value=_response(body=CATALOG)
    ) as mock_get:
        yield mock_get


def test_init_missing_key(monkeypatch):
    monkeypatch.delenv("APIVERVE_API_KEY", raising=False)

    with pytest.raises(ValueError):
        APIVerveToolkit()


def test_init_reads_key_from_env(monkeypatch):
    monkeypatch.setenv("APIVERVE_API_KEY", API_KEY)

    assert APIVerveToolkit().api_key == API_KEY


def test_get_tools(toolkit):
    tools = toolkit.get_tools()

    assert all(isinstance(tool, FunctionTool) for tool in tools)
    assert [tool.get_function_name() for tool in tools] == [
        "search_apis",
        "call_api",
    ]


def test_search_ranks_word_starts(toolkit, catalog_get):
    rows = toolkit.search_apis(query="vat")

    assert [row["api"] for row in rows] == ["vatrates"]
    assert "x-api-key" not in catalog_get.call_args.kwargs["headers"]


def test_search_returns_parameters(toolkit, catalog_get):
    rows = toolkit.search_apis(query="email validator")

    assert rows[0]["api"] == "emailvalidator"
    assert rows[0]["parameters"][0] == {
        "name": "email",
        "type": "string",
        "required": True,
        "description": None,
        "example": None,
    }


def test_catalog_is_cached(toolkit, catalog_get):
    toolkit.search_apis(query="vat")
    toolkit.search_apis(query="pdf")

    assert catalog_get.call_count == 1


def test_malformed_catalog_is_an_error(toolkit):
    with patch.object(
        module.requests, "get", return_value=_response(body={"apis": []})
    ):
        result = toolkit.search_apis(query="vat")

    assert result.startswith("Error: The APIVerve catalog could not be")
    assert toolkit._catalog is None


def test_failed_refresh_serves_stale_catalog_and_backs_off(
    toolkit, catalog_get
):
    toolkit.search_apis(query="vat")
    toolkit._catalog_at -= module.CATALOG_TTL_SECONDS + 1

    with patch.object(
        module.requests,
        "get",
        side_effect=requests.ConnectionError("down"),
    ) as failing_get:
        rows = toolkit.search_apis(query="vat")
        toolkit.search_apis(query="pdf")

    assert [row["api"] for row in rows] == ["vatrates"]
    assert failing_get.call_count == 1


def test_call_get_sends_key_to_fixed_host(toolkit, catalog_get):
    with patch.object(
        module.requests,
        "request",
        return_value=_response(
            body={"status": "ok", "data": {"isValid": True}}
        ),
    ) as mock_request:
        result = toolkit.call_api(
            api="emailvalidator", parameters={"email": "jane@example.com"}
        )

    assert result == {"isValid": True}
    args, kwargs = mock_request.call_args
    assert args == ("GET", "https://api.apiverve.com/v1/emailvalidator")
    assert kwargs["params"] == {"email": "jane@example.com"}
    assert kwargs["json"] is None
    assert kwargs["headers"]["x-api-key"] == API_KEY
    assert kwargs["allow_redirects"] is False


def test_call_post_places_query_and_body_per_catalog(toolkit, catalog_get):
    with patch.object(
        module.requests,
        "request",
        return_value=_response(body={"status": "ok", "data": {"pdf": "x"}}),
    ) as mock_request:
        result = toolkit.call_api(
            api="texttopdf", parameters={"text": "hi", "title": "T"}
        )

    assert result == {"pdf": "x"}
    args, kwargs = mock_request.call_args
    assert args == ("POST", "https://api.apiverve.com/v1/texttopdf")
    assert kwargs["params"] == {"title": "T"}
    assert kwargs["json"] == {"text": "hi"}


def test_call_reports_missing_required_parameter(toolkit, catalog_get):
    result = toolkit.call_api(api="emailvalidator", parameters={})

    assert result == "Error: emailvalidator needs: email."


def test_call_reports_unknown_api(toolkit, catalog_get):
    result = toolkit.call_api(api="nope")

    assert result.startswith('Error: Unknown APIVerve API "nope"')


def test_call_reports_bad_key(toolkit, catalog_get):
    with patch.object(
        module.requests,
        "request",
        return_value=_response(
            401, {"status": "error", "error": "Unauthorized"}
        ),
    ):
        result = toolkit.call_api(
            api="emailvalidator", parameters={"email": "jane@example.com"}
        )

    assert result == "Error: APIVerve rejected the API key."


def test_call_never_echoes_the_key(toolkit, catalog_get):
    body = {"status": "ok", "data": {"note": f"called with {API_KEY}"}}
    error = {"status": "error", "error": f"bad key {API_KEY}"}

    with patch.object(
        module.requests, "request", return_value=_response(body=body)
    ):
        ok = toolkit.call_api(
            api="emailvalidator", parameters={"email": "jane@example.com"}
        )
    with patch.object(
        module.requests, "request", return_value=_response(400, error)
    ):
        failed = toolkit.call_api(
            api="emailvalidator", parameters={"email": "jane@example.com"}
        )

    assert ok == {"note": "called with [redacted]"}
    assert failed == "Error: APIVerve returned HTTP 400: bad key [redacted]"
