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
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

import pytest

from camel.toolkits import FunctionTool, XquikToolkit


class FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


@pytest.fixture(autouse=True)
def set_xquik_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XQUIK_API_KEY", "test-api-key")


def test_xquik_get_builds_authorized_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = {
            key.lower(): value for key, value in request.header_items()
        }
        return FakeResponse({"ok": True})

    monkeypatch.setattr(
        "camel.toolkits.xquik_toolkit.urllib.request.urlopen",
        fake_urlopen,
    )

    result = XquikToolkit()._xquik_get(
        "/x/tweets/search",
        {"q": "camel ai", "limit": 10, "empty": None},
    )

    parsed_url = urlparse(captured["url"])
    assert result == {"ok": True}
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "xquik.com"
    assert parsed_url.path == "/api/v1/x/tweets/search"
    assert parse_qs(parsed_url.query) == {
        "limit": ["10"],
        "q": ["camel ai"],
    }
    assert captured["timeout"] == 15
    assert captured["headers"]["x-api-key"] == "test-api-key"
    assert captured["headers"]["accept"] == "application/json"
    assert captured["headers"]["user-agent"] == "camel-ai/1.0"


def test_xquik_search_tweets_formats_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[Tuple[str, Dict[str, Any]]] = []
    toolkit = XquikToolkit()

    def fake_xquik_get(
        path: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        calls.append((path, params or {}))
        return {
            "tweets": [
                {
                    "id": "123",
                    "text": "CAMEL adds a toolkit",
                    "createdAt": "2026-05-12T00:00:00Z",
                    "author": {
                        "username": "CamelAIOrg",
                        "name": "CAMEL-AI",
                        "verified": True,
                    },
                    "likeCount": 12,
                    "retweetCount": 3,
                    "replyCount": 2,
                    "quoteCount": 1,
                    "viewCount": 1000,
                    "bookmarkCount": 4,
                }
            ]
        }

    monkeypatch.setattr(toolkit, "_xquik_get", fake_xquik_get)

    result = json.loads(
        toolkit.xquik_search_tweets(
            "from:CamelAIOrg -is:retweet",
            max_results=500,
            sort_order="Latest",
        )
    )

    assert calls == [
        (
            "/x/tweets/search",
            {
                "limit": 200,
                "q": "from:CamelAIOrg -is:retweet",
                "queryType": "Latest",
            },
        )
    ]
    assert result == {
        "count": 1,
        "query": "from:CamelAIOrg -is:retweet",
        "tweets": [
            {
                "author": {
                    "name": "CAMEL-AI",
                    "username": "CamelAIOrg",
                    "verified": True,
                },
                "created_at": "2026-05-12T00:00:00Z",
                "id": "123",
                "metrics": {
                    "bookmarks": 4,
                    "likes": 12,
                    "quotes": 1,
                    "replies": 2,
                    "retweets": 3,
                    "views": 1000,
                },
                "text": "CAMEL adds a toolkit",
                "url": "https://x.com/CamelAIOrg/status/123",
            }
        ],
    }

    calls.clear()
    toolkit.xquik_search_tweets("CAMEL-AI", max_results=1)

    assert calls == [
        (
            "/x/tweets/search",
            {"limit": 1, "q": "CAMEL-AI", "queryType": "Top"},
        )
    ]


def test_xquik_get_tweet_formats_single_tweet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[Tuple[str, Dict[str, Any] | None]] = []
    toolkit = XquikToolkit()

    def fake_xquik_get(
        path: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        calls.append((path, params))
        return {
            "tweet": {
                "id": "456",
                "text": "A specific tweet",
                "createdAt": "2026-05-12T01:00:00Z",
                "likeCount": 5,
                "retweetCount": 4,
                "replyCount": 3,
                "quoteCount": 2,
                "viewCount": 100,
                "bookmarkCount": 1,
            },
            "author": {"username": "CamelAIOrg", "name": "CAMEL-AI"},
        }

    monkeypatch.setattr(toolkit, "_xquik_get", fake_xquik_get)

    result = json.loads(toolkit.xquik_get_tweet("456"))

    assert calls == [("/x/tweets/456", None)]
    assert result["id"] == "456"
    assert result["author"]["username"] == "CamelAIOrg"
    assert result["metrics"]["likes"] == 5
    assert result["url"] == "https://x.com/CamelAIOrg/status/456"


def test_xquik_get_user_info_strips_at_sign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[Tuple[str, Dict[str, Any] | None]] = []
    toolkit = XquikToolkit()

    def fake_xquik_get(
        path: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        calls.append((path, params))
        return {
            "description": "Multi-agent framework",
            "followers": 100,
            "following": 10,
            "id": "789",
            "name": "CAMEL-AI",
            "statusesCount": 50,
            "username": "CamelAIOrg",
            "verified": True,
        }

    monkeypatch.setattr(toolkit, "_xquik_get", fake_xquik_get)

    result = json.loads(toolkit.xquik_get_user_info("@CamelAIOrg"))

    assert calls == [("/x/users/CamelAIOrg", None)]
    assert result == {
        "description": "Multi-agent framework",
        "followers": 100,
        "following": 10,
        "id": "789",
        "name": "CAMEL-AI",
        "tweet_count": 50,
        "url": "https://x.com/CamelAIOrg",
        "username": "CamelAIOrg",
        "verified": True,
    }


def test_xquik_get_trends_clamps_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: List[Tuple[str, Dict[str, Any]]] = []
    toolkit = XquikToolkit()

    def fake_xquik_get(
        path: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        calls.append((path, params or {}))
        return {"trends": [{"name": "CAMEL", "tweet_volume": 1234}]}

    monkeypatch.setattr(toolkit, "_xquik_get", fake_xquik_get)

    result = json.loads(toolkit.xquik_get_trends(woeid=23424977, count=99))

    assert calls == [("/x/trends", {"count": 50, "woeid": 23424977})]
    assert result == {"trends": [{"name": "CAMEL", "tweet_volume": 1234}]}

    result = json.loads(toolkit.xquik_get_trends(woeid=1, count=-1))

    assert calls[-1] == ("/x/trends", {"count": 1, "woeid": 1})
    assert result == {"trends": [{"name": "CAMEL", "tweet_volume": 1234}]}


def test_xquik_toolkit_get_tools() -> None:
    tools = XquikToolkit().get_tools()

    assert len(tools) == 4
    assert all(isinstance(tool, FunctionTool) for tool in tools)
    assert [tool.get_function_name() for tool in tools] == [
        "xquik_search_tweets",
        "xquik_get_tweet",
        "xquik_get_user_info",
        "xquik_get_trends",
    ]


def test_xquik_toolkit_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("XQUIK_API_KEY")

    with pytest.raises(ValueError, match="XQUIK_API_KEY"):
        XquikToolkit()
