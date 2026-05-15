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
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)

_BASE = "https://xquik.com/api/v1"


@MCPServer()
class XquikToolkit(BaseToolkit):
    r"""A toolkit for read-only X (Twitter) operations via the Xquik API.

    Provides tweet search, tweet lookup, user profile lookup, and trending
    topics. Requires only ``XQUIK_API_KEY`` (1 env var) and no OAuth setup.

    For write operations (posting, deleting tweets), use
    :class:`TwitterToolkit` instead.

    References:
        https://xquik.com

    Notes:
        To use this toolkit, set the ``XQUIK_API_KEY`` environment variable.
        Get a key at https://xquik.com
    """

    @api_keys_required([(None, "XQUIK_API_KEY")])
    def __init__(self, timeout: Optional[float] = None):
        r"""Initialize the XquikToolkit with API credentials from env vars."""
        super().__init__(timeout=timeout)
        self.api_key = os.environ.get("XQUIK_API_KEY", "")

    def _xquik_get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        r"""Make a GET request to the Xquik API.

        Args:
            path (str): API endpoint path.
            params (Optional[Dict[str, Any]]): Query parameters.

        Returns:
            Dict[str, Any]: Parsed JSON response.

        Raises:
            RuntimeError: If the API request fails.
        """
        url = f"{_BASE}{path}"
        if params:
            qs = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url = f"{url}?{qs}"

        req = urllib.request.Request(
            url,
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "camel-ai/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def xquik_search_tweets(
        self,
        query: str,
        max_results: int = 10,
        sort_order: str = "Top",
    ) -> str:
        r"""Search for tweets on X (Twitter).

        Supports X search operators: ``from:user``, ``#hashtag``,
        ``"exact phrase"``, ``since:YYYY-MM-DD``, ``until:YYYY-MM-DD``,
        ``-is:retweet``, ``-is:reply``, ``has:media``.

        Args:
            query (str): The search query.
            max_results (int): Maximum number of tweets to return (1-200).
                (default: :obj:`10`)
            sort_order (str): Sort order, "Top" (engagement) or "Latest"
                (chronological). (default: :obj:`"Top"`)

        Returns:
            str: A JSON-formatted string containing the search results with
                tweet text, author info, engagement metrics, and URLs.
        """
        try:
            max_results = max(1, min(max_results, 200))
            data = self._xquik_get(
                "/x/tweets/search",
                {"q": query, "limit": max_results, "queryType": sort_order},
            )
            tweets = data.get("tweets", [])
            results = []
            for tweet in tweets:
                author = tweet.get("author", {})
                results.append(
                    {
                        "id": tweet.get("id", ""),
                        "text": tweet.get("text", ""),
                        "created_at": tweet.get("createdAt", ""),
                        "author": {
                            "username": author.get("username", ""),
                            "name": author.get("name", ""),
                            "verified": author.get("verified", False),
                        },
                        "metrics": {
                            "likes": tweet.get("likeCount", 0),
                            "retweets": tweet.get("retweetCount", 0),
                            "replies": tweet.get("replyCount", 0),
                            "quotes": tweet.get("quoteCount", 0),
                            "views": tweet.get("viewCount", 0),
                            "bookmarks": tweet.get("bookmarkCount", 0),
                        },
                        "url": (
                            "https://x.com/"
                            f"{author.get('username', 'unknown')}"
                            f"/status/{tweet.get('id', '')}"
                        ),
                    }
                )
            return json.dumps(
                {"query": query, "count": len(results), "tweets": results},
                indent=2,
            )
        except Exception as e:
            logger.exception("Error searching tweets via Xquik")
            return json.dumps({"error": str(e), "query": query})

    def xquik_get_tweet(self, tweet_id: str) -> str:
        r"""Retrieve a single tweet by ID with full engagement metrics.

        Args:
            tweet_id (str): The tweet ID to look up.

        Returns:
            str: A JSON-formatted string containing the tweet text, author
                info, and engagement metrics.
        """
        try:
            data = self._xquik_get(f"/x/tweets/{tweet_id}")
            tweet = data.get("tweet")
            if not isinstance(tweet, dict):
                tweet = data
            author = data.get("author")
            if not isinstance(author, dict):
                author = tweet.get("author", {})
            result = {
                "id": tweet.get("id", ""),
                "text": tweet.get("text", ""),
                "created_at": tweet.get("createdAt", ""),
                "author": {
                    "username": author.get("username", ""),
                    "name": author.get("name", ""),
                    "verified": author.get("verified", False),
                },
                "metrics": {
                    "likes": tweet.get("likeCount", 0),
                    "retweets": tweet.get("retweetCount", 0),
                    "replies": tweet.get("replyCount", 0),
                    "quotes": tweet.get("quoteCount", 0),
                    "views": tweet.get("viewCount", 0),
                    "bookmarks": tweet.get("bookmarkCount", 0),
                },
                "url": (
                    f"https://x.com/{author.get('username', 'unknown')}"
                    f"/status/{tweet.get('id', '')}"
                ),
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.exception("Error fetching tweet via Xquik")
            return json.dumps({"error": str(e)})

    def xquik_get_user_info(self, username: str) -> str:
        r"""Retrieve information about a specific X (Twitter) user.

        Args:
            username (str): The username (without @) to look up.

        Returns:
            str: A JSON-formatted string with the user's profile information.
        """
        try:
            data = self._xquik_get(f"/x/users/{username.lstrip('@')}")
            result = {
                "id": data.get("id", ""),
                "name": data.get("name", ""),
                "username": data.get("username", ""),
                "description": data.get("description", ""),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
                "tweet_count": data.get("statusesCount", 0),
                "verified": data.get("verified", False),
                "url": f"https://x.com/{data.get('username', username)}",
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.exception("Error fetching user info via Xquik")
            return json.dumps({"error": str(e)})

    def xquik_get_trends(self, woeid: int = 1, count: int = 20) -> str:
        r"""Get trending topics on X (Twitter).

        Args:
            woeid (int): WOEID for region. 1=Global, 23424977=US,
                23424975=UK. (default: :obj:`1`)
            count (int): Number of trends to return (1-50).
                (default: :obj:`20`)

        Returns:
            str: A JSON-formatted string with a list of trending topics.
        """
        try:
            count = max(1, min(count, 50))
            data = self._xquik_get(
                "/x/trends", {"woeid": woeid, "count": count}
            )
            return json.dumps({"trends": data.get("trends", [])}, indent=2)
        except Exception as e:
            logger.exception("Error fetching trends via Xquik")
            return json.dumps({"error": str(e)})

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.xquik_search_tweets),
            FunctionTool(self.xquik_get_tweet),
            FunctionTool(self.xquik_get_user_info),
            FunctionTool(self.xquik_get_trends),
        ]
