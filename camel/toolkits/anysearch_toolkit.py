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
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlsplit

import httpx

from camel.toolkits.base import BaseToolkit, manual_timeout
from camel.toolkits.function_tool import FunctionTool

_BASE_URL = "https://api.anysearch.com"


def _search_payload(
    query: str,
    max_results: Optional[int],
    tag: Optional[str],
    zone: Optional[str],
    language: Optional[str],
    params: Optional[Dict[str, Any]],
    format: Optional[str],
) -> Dict[str, Any]:
    r"""Validate search arguments and omit unspecified API options."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")
    count = 10 if max_results is None else max_results
    if type(count) is not int or not 1 <= count <= 10:
        raise ValueError("max_results must be an integer between 1 and 10.")
    if zone is not None and zone not in ("cn", "intl"):
        raise ValueError("zone must be 'cn' or 'intl'.")
    if format is not None and format not in ("json", "markdown"):
        raise ValueError("format must be 'json' or 'markdown'.")
    for name, text_value in (("tag", tag), ("language", language)):
        if text_value is not None and (
            not isinstance(text_value, str) or not text_value.strip()
        ):
            raise ValueError(f"{name} must be a non-empty string.")
    if params is not None and not isinstance(params, dict):
        raise ValueError("params must be a JSON object.")
    payload: Dict[str, Any] = {"query": query, "max_results": count}
    for name, value in (
        ("tag", tag),
        ("zone", zone),
        ("language", language),
        ("params", params),
        ("format", format),
    ):
        if value is not None:
            payload[name] = value
    try:
        json.dumps(payload, allow_nan=False, ensure_ascii=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("Search arguments must be valid JSON.") from None
    return payload


def _request_id(value: Any) -> Optional[str]:
    r"""Accept only short, printable request identifiers."""
    if isinstance(value, str) and re.fullmatch(
        r"[A-Za-z0-9._:-]{1,128}", value
    ):
        if not value.lower().startswith(("as_sk_", "sk-", "bearer")):
            return value
    return None


class AnySearchToolkit(BaseToolkit):
    r"""A toolkit for web search and page extraction with AnySearch.

    Search supports general queries and vertical sources discovered through
    :meth:`anysearch_list_subdomains`. Batch search sends up to five separate
    requests concurrently. Each request counts toward the service quota.

    Args:
        api_key (Optional[str]): AnySearch API key. If not provided, reads
            :obj:`ANYSEARCH_API_KEY`. If neither is set, requests are
            anonymous. (default: :obj:`None`)
        anonymous (bool): Omit authentication even if a key is available.
            Anonymous requests are subject to the service's IP-based limits.
            (default: :obj:`False`)
        timeout (Optional[float]): HTTPX timeout in seconds for each network
            phase. Set to :obj:`None` to disable it. (default: :obj:`30.0`)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        anonymous: bool = False,
        timeout: Optional[float] = 30.0,
    ) -> None:
        super().__init__(timeout=timeout)
        key = (
            api_key if api_key is not None else os.getenv("ANYSEARCH_API_KEY")
        )
        self._api_key = None if anonymous else key

    @manual_timeout
    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Tuple[Tuple[str, str], ...]] = None,
    ) -> Dict[str, Any]:
        r"""Send a request without exposing service error bodies."""
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            with httpx.Client(follow_redirects=False) as client:
                response = client.request(
                    method,
                    f"{_BASE_URL}{path}",
                    headers=headers,
                    json=payload,
                    params=params,
                    timeout=self.timeout,
                )
        except httpx.TimeoutException:
            return {"error": "The AnySearch request timed out."}
        except httpx.RequestError:
            return {"error": "Unable to connect to AnySearch."}
        except (ValueError, TypeError, UnicodeError):
            return {"error": "Unable to encode the AnySearch request."}

        metadata: Dict[str, Any] = {}
        request_id = _request_id(response.headers.get("X-Request-ID"))
        if request_id and request_id != self._api_key:
            metadata["request_id"] = request_id
        if not response.is_success:
            messages = {
                401: "AnySearch authentication failed. Check your API key.",
                403: "AnySearch denied access. Check your key permissions.",
                402: "AnySearch quota is exhausted. Check your account quota.",
                429: "AnySearch rate limit exceeded. Try again later.",
            }
            # Anonymous quota errors can contain newly issued credentials.
            # Never pass the response body or an HTTP exception to the agent.
            error = messages.get(
                response.status_code, "AnySearch rejected the request."
            )
            retry_after = response.headers.get("Retry-After", "")
            if response.status_code == 429 and re.fullmatch(
                r"[0-9]{1,10}", retry_after
            ):
                metadata["retry_after"] = int(retry_after)
            return {
                "error": error,
                "status_code": response.status_code,
                **metadata,
            }
        try:
            body = response.json()
        except ValueError:
            return {"error": "AnySearch returned invalid JSON.", **metadata}
        if not isinstance(body, dict):
            return {
                "error": "AnySearch returned an invalid response.",
                **metadata,
            }
        request_id = _request_id(body.get("request_id"))
        if request_id and request_id != self._api_key:
            metadata["request_id"] = request_id
        if type(body.get("code")) is not int or body["code"] != 0:
            return {
                "error": "AnySearch could not complete the request.",
                **metadata,
            }
        if not isinstance(body.get("data"), (dict, list)):
            return {
                "error": "AnySearch returned an invalid response.",
                **metadata,
            }
        return {
            "code": 0,
            "message": "success",
            "data": body["data"],
            **metadata,
        }

    @manual_timeout
    def anysearch_search_web(
        self,
        query: str,
        max_results: Optional[int] = None,
        tag: Optional[str] = None,
        zone: Optional[Literal["cn", "intl"]] = None,
        language: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        format: Optional[Literal["json", "markdown"]] = None,
    ) -> Dict[str, Any]:
        r"""Search the web or an AnySearch vertical source.

        Use anysearch_list_subdomains to discover tags and their required
        parameters before selecting a vertical source.

        Args:
            query (str): The search query.
            max_results (Optional[int]): Number of results, from 1 to 10.
                If None, uses 10. (default: :obj:`None`)
            tag (Optional[str]): Vertical source in domain.subdomain form.
                If None, uses general search. (default: :obj:`None`)
            zone (Optional[Literal["cn", "intl"]]): Source region.
                (default: :obj:`None`)
            language (Optional[str]): Preferred result language.
                (default: :obj:`None`)
            params (Optional[Dict[str, Any]]): Parameters required by the
                selected vertical source. (default: :obj:`None`)
            format (Optional[Literal["json", "markdown"]]): Result format.
                The response envelope is always JSON. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Service envelope with code, message, data and an
                optional request_id. Search data contains results and service
                metadata. On failure, contains error and optional status_code,
                request_id and retry_after (seconds).
        """
        try:
            payload = _search_payload(
                query, max_results, tag, zone, language, params, format
            )
        except ValueError as exc:
            return {"error": str(exc)}
        return self._request("POST", "/v1/search", payload=payload)

    @manual_timeout
    def anysearch_search_batch(
        self,
        queries: List[str],
        max_results: Optional[int] = None,
        tag: Optional[str] = None,
        zone: Optional[Literal["cn", "intl"]] = None,
        language: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        format: Optional[Literal["json", "markdown"]] = None,
    ) -> Dict[str, Any]:
        r"""Search one to five queries concurrently with shared options.

        Each query makes a separate search request and consumes its own quota.
        Results retain input order, including individual request failures.

        Args:
            queries (List[str]): One to five non-empty search queries.
            max_results (Optional[int]): Results per query, from 1 to 10.
                If None, uses 10. (default: :obj:`None`)
            tag (Optional[str]): Vertical source in domain.subdomain form.
                Discover available tags with anysearch_list_subdomains.
                (default: :obj:`None`)
            zone (Optional[Literal["cn", "intl"]]): Source region.
                (default: :obj:`None`)
            language (Optional[str]): Preferred result language.
                (default: :obj:`None`)
            params (Optional[Dict[str, Any]]): Parameters required by the
                selected vertical source. (default: :obj:`None`)
            format (Optional[Literal["json", "markdown"]]): Result format.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A results list whose entries contain query and
                response. Each response is a search envelope or an error
                dictionary. Invalid batch arguments return an error dictionary.
        """
        if not isinstance(queries, list) or not 1 <= len(queries) <= 5:
            return {"error": "queries must contain between 1 and 5 strings."}
        try:
            for query in queries:
                _search_payload(
                    query, max_results, tag, zone, language, params, format
                )
        except ValueError as exc:
            return {"error": str(exc)}
        search = partial(
            self.anysearch_search_web,
            max_results=max_results,
            tag=tag,
            zone=zone,
            language=language,
            params=params,
            format=format,
        )
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            responses = executor.map(search, queries)
            return {
                "results": [
                    {"query": query, "response": response}
                    for query, response in zip(queries, responses)
                ]
            }

    @manual_timeout
    def anysearch_list_subdomains(self, domains: List[str]) -> Dict[str, Any]:
        r"""List vertical search sources and their parameter requirements.

        Args:
            domains (List[str]): One to five domain names, such as 'code'
                or 'finance'.

        Returns:
            Dict[str, Any]: Service envelope whose data describes domains,
                subdomains and parameters, or an error dictionary. This
                directory request does not consume search quota.
        """
        if (
            not isinstance(domains, list)
            or not 1 <= len(domains) <= 5
            or any(
                not isinstance(domain, str) or not domain.strip()
                for domain in domains
            )
        ):
            return {"error": "domains must contain between 1 and 5 strings."}
        params = tuple(("domain", domain) for domain in domains)
        return self._request("GET", "/v1/sub-domains", params=params)

    @manual_timeout
    def anysearch_extract_page(self, url: str) -> Dict[str, Any]:
        r"""Extract readable content from a public HTTP or HTTPS URL.

        Supports HTML, XHTML, text, JSON and Markdown. PDF and media files are
        not supported. The service may truncate HTML and text to 50,000
        characters; oversized JSON and Markdown are rejected.

        Args:
            url (str): Public URL to extract. The UTF-8 JSON request must not
                exceed 16 KiB.

        Returns:
            Dict[str, Any]: Service envelope with url, title and content in
                data, or an error dictionary.
        """
        try:
            if not isinstance(url, str) or not url.strip():
                raise ValueError
            parsed = urlsplit(url)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError
            payload = {"url": url}
            size = len(
                json.dumps(
                    payload, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
            )
        except (ValueError, UnicodeError):
            return {"error": "url must be an HTTP(S) URL without credentials."}
        if size > 16 * 1024:
            return {"error": "The extract request must not exceed 16 KiB."}
        return self._request("POST", "/v1/extract", payload=payload)

    @manual_timeout
    def get_tools(self) -> List[FunctionTool]:
        r"""Return the web search, batch, directory and extraction tools.

        Returns:
            List[FunctionTool]: Tools available to a CAMEL agent.
        """
        return [
            FunctionTool(self.anysearch_search_web),
            FunctionTool(self.anysearch_search_batch),
            FunctionTool(self.anysearch_list_subdomains),
            FunctionTool(self.anysearch_extract_page),
        ]
