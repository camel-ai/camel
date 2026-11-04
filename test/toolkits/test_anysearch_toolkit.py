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

from unittest.mock import patch

import pytest

from camel.toolkits import AnySearchToolkit


def _response(payload, status=200):
    class Response:
        status_code = status

        def raise_for_status(self):
            if status >= 400:
                raise RuntimeError(f"http {status}")

        def json(self):
            return payload
    return Response()


def _envelope(results):
    return {"code": 0, "message": "success",
            "request_id": "test", "data": {"results": results}}


@pytest.fixture
def toolkit():
    return AnySearchToolkit(api_key="sk-test")


def test_anonymous_toolkit_has_no_auth_header():
    tk = AnySearchToolkit()
    assert "Authorization" not in tk._headers()


def test_api_key_adds_bearer_header(toolkit):
    assert toolkit._headers()["Authorization"] == "Bearer sk-test"


def test_invalid_zone_raises():
    with pytest.raises(ValueError):
        AnySearchToolkit(zone="eu")


def test_invalid_extract_url_raises(toolkit):
    with pytest.raises(ValueError):
        toolkit.extract("not-a-url")


def test_search_returns_normalized_results(toolkit):
    raw = [{"title": "t", "url": "https://x.com", "snippet": "s",
            "content": "c"}]
    with patch("requests.post", return_value=_response(_envelope(raw))):
        out = toolkit.search("q")
    assert out == [{"title": "t", "link": "https://x.com",
                    "snippet": "s", "content": "c"}]


def test_search_clamps_num_results(toolkit):
    seen = {}

    def capture(url, json=None, headers=None, timeout=None):
        seen.update(json)
        return _response(_envelope([]))

    with patch("requests.post", side_effect=capture):
        toolkit.search("q", num_results=0)
        assert seen["max_results"] == 1
        toolkit.search("q", num_results=99)
        assert seen["max_results"] == 10


def test_search_forwards_tag_and_params(toolkit):
    seen = {}

    def capture(url, json=None, headers=None, timeout=None):
        seen.update(json)
        return _response(_envelope([]))

    with patch("requests.post", side_effect=capture):
        toolkit.search("q", tag="code.doc", params={"library": "golang"})
    assert seen["tag"] == "code.doc"
    assert seen["params"] == {"library": "golang"}


def test_business_error_returns_empty(toolkit):
    payload = {"code": 400, "message": "bad tag"}
    with patch("requests.post", return_value=_response(payload)):
        assert toolkit.search("q") == []


def test_http_error_returns_empty(toolkit):
    with patch("requests.post", return_value=_response({}, status=500)):
        assert toolkit.search("q") == []
        assert toolkit.extract("https://example.com") == {}


def test_malformed_rows_are_skipped(toolkit):
    raw = [{"title": "t", "url": "https://x.com"}, "junk", 42]
    with patch("requests.post", return_value=_response(_envelope(raw))):
        assert len(toolkit.search("q")) == 1


def test_extract_returns_page_content(toolkit):
    payload = {"code": 0, "data": {"url": "https://example.com",
                                   "title": "Example Domain",
                                   "content": "body"}}
    with patch("requests.post", return_value=_response(payload)):
        page = toolkit.extract("https://example.com")
    assert page["title"] == "Example Domain"
    assert page["content"] == "body"


def test_parallel_search_maps_every_query(toolkit):
    with patch("requests.post",
               return_value=_response(_envelope(
                   [{"title": "t", "url": "https://x.com"}]))):
        out = toolkit.search_parallel(["a", "b", "a"], num_results=2)
    assert sorted(out.keys()) == ["a", "b"]
    assert all(len(v) == 1 for v in out.values())


def test_parallel_search_empty_input(toolkit):
    assert toolkit.search_parallel([]) == {}


def test_get_tools_exposes_four_tools(toolkit):
    names = {t.func.__name__ for t in toolkit.get_tools()}
    assert names == {"search", "search_vertical", "search_parallel",
                     "extract"}
