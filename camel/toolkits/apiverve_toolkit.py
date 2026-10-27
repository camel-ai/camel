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
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required

API_BASE = "https://api.apiverve.com"
CATALOG_URL = "https://assets.apiverve.com/cli-manifest.json"
CATALOG_TTL_SECONDS = 3600.0


def _redact(value: Any, secret: str) -> Any:
    r"""Replaces every occurrence of ``secret`` in nested data."""
    if isinstance(value, str):
        return value.replace(secret, "[redacted]")
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {
            _redact(k, secret): _redact(v, secret) for k, v in value.items()
        }
    return value


def _query_value(value: Any) -> str:
    r"""Serializes a parameter value for a query string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_query_value(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def _error_message(status: int, payload: Any) -> str:
    r"""Maps an APIVerve error response to a short message."""
    detail = ""
    if isinstance(payload, dict):
        detail = str(payload.get("error") or payload.get("message") or "")
    if status == 401:
        return "APIVerve rejected the API key."
    if status == 403:
        suffix = f": {detail}" if detail else "."
        return f"This API key is not allowed to make this call{suffix}"
    if status == 429:
        return (
            "Rate limit reached or monthly credits used up. Retry "
            "shortly, or upgrade at https://dashboard.apiverve.com."
        )
    if detail:
        return f"APIVerve returned HTTP {status}: {detail}"
    return f"APIVerve returned HTTP {status}."


@MCPServer()
class APIVerveToolkit(BaseToolkit):
    r"""A toolkit for calling the APIVerve catalog of REST APIs.

    APIVerve offers about 380 APIs behind one key: email and phone
    validation, IP, DNS, WHOIS and SSL lookups, exchange and VAT rates, VIN
    decoding, document and image conversion, and more. Rather than one tool
    per API, the toolkit exposes two tools: one searches the catalog, the
    other calls any API in it by id.

    Requests go only to ``https://api.apiverve.com`` with the key in the
    ``x-api-key`` header. Redirects are not followed, and the key is removed
    from anything returned to the agent.

    Notes:
        To use this toolkit, set the APIVERVE_API_KEY environment variable
        (or pass ``api_key`` to the constructor). A free key is available at
        https://dashboard.apiverve.com.
    """

    @api_keys_required([("api_key", "APIVERVE_API_KEY")])
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initializes the APIVerveToolkit.

        Args:
            api_key (Optional[str]): The APIVerve API key. If not provided, it
                is read from the APIVERVE_API_KEY environment variable.
                (default: :obj:`None`)
            timeout (Optional[float]): The timeout for API requests, in
                seconds. (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.api_key = (
            api_key or os.environ.get("APIVERVE_API_KEY", "")
        ).strip()
        self._request_timeout = timeout if timeout is not None else 60
        self._catalog: Optional[Dict[str, Dict[str, Any]]] = None
        self._catalog_at = 0.0

    def _load_catalog(self) -> Dict[str, Dict[str, Any]]:
        r"""Returns ``{api_id: definition}`` from the public catalog.

        The catalog is cached for an hour. If a refresh fails, the cached copy
        is served and the next retry waits a full hour.
        """
        if (
            self._catalog is not None
            and time.monotonic() - self._catalog_at < CATALOG_TTL_SECONDS
        ):
            return self._catalog
        try:
            response = requests.get(
                CATALOG_URL,
                headers={"accept": "application/json"},
                timeout=self._request_timeout,
                allow_redirects=False,
            )
            response.raise_for_status()
            apis = response.json()["apis"]
            if not isinstance(apis, dict):
                raise TypeError("Catalog 'apis' must be an object.")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            if self._catalog is not None:
                self._catalog_at = time.monotonic()
                return self._catalog
            raise RuntimeError(
                "The APIVerve catalog could not be loaded. Retry in a moment."
            )
        self._catalog, self._catalog_at = apis, time.monotonic()
        return apis

    def search_apis(
        self, query: str, max_results: int = 10
    ) -> Union[List[Dict[str, Any]], str]:
        r"""Searches the APIVerve catalog for APIs that fit a task.

        Use this first to find the id and parameters of an API, then pass them
        to `call_api`.

        Args:
            query (str): What you need, in a few words, e.g.
                ``"validate email"`` or ``"vat rates"``.
            max_results (int): The maximum number of APIs to return.
                (default: :obj:`10`)

        Returns:
            Union[List[Dict[str, Any]], str]: The best matching APIs, each with
                its ``api`` id, title, category, description and parameters,
                or an error message string if the catalog could not be loaded.
        """
        try:
            apis = self._load_catalog()
        except RuntimeError as e:
            return f"Error: {e}"
        words = [w for w in query.lower().split() if w]
        scored = []
        for api_id, api in apis.items():
            title = (api.get("title") or "").lower()
            category = (api.get("category") or "").lower()
            description = (api.get("description") or "").lower()
            score = 0
            for word in words:
                # Word-start matches, so "vat" finds VAT Rates, not Gravatar.
                starts = re.compile(r"\b" + re.escape(word))
                if api_id.startswith(word) or (
                    len(word) >= 4 and word in api_id
                ):
                    score += 4
                if starts.search(title):
                    score += 4
                if starts.search(category):
                    score += 2
                if starts.search(description):
                    score += 1
            if score or not words:
                scored.append((score, api_id, api))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [
            {
                "api": api_id,
                "title": api.get("title"),
                "category": api.get("category"),
                "description": api.get("description"),
                "parameters": [
                    {
                        "name": p.get("name"),
                        "type": p.get("type"),
                        "required": bool(p.get("required")),
                        "description": p.get("description"),
                        "example": p.get("example"),
                    }
                    for p in api.get("params", [])
                ],
            }
            for _, api_id, api in scored[:max_results]
        ]

    def call_api(
        self, api: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], List[Any], str]:
        r"""Calls one APIVerve API by id and returns its response data.

        Args:
            api (str): The API id from `search_apis`, e.g. ``emailvalidator``,
                ``iplookup`` or ``vindecoder``.
            parameters (Optional[Dict[str, Any]]): The API's parameters, e.g.
                ``{"email": "jane@example.com"}``. (default: :obj:`None`)

        Returns:
            Union[Dict[str, Any], List[Any], str]: The ``data`` of the API's
                response if successful, or an error message string starting
                with ``Error:`` if failed.
        """
        try:
            apis = self._load_catalog()
        except RuntimeError as e:
            return f"Error: {e}"

        api_id = api.strip().lower()
        definition = apis.get(api_id)
        if definition is None:
            return (
                f'Error: Unknown APIVerve API "{api_id}". Use search_apis '
                "to look up the id."
            )
        params = {
            k: v
            for k, v in (parameters or {}).items()
            if v is not None and v != ""
        }
        declared = {p["name"]: p for p in definition.get("params", [])}
        missing = [
            n
            for n, p in declared.items()
            if p.get("required") and n not in params
        ]
        if missing:
            return f"Error: {api_id} needs: {', '.join(missing)}."
        path = definition.get("path") or ""
        if not path.startswith("/v1/"):
            return f'Error: The catalog entry for "{api_id}" is invalid.'

        method = (
            "POST"
            if (definition.get("method") or "GET").upper() == "POST"
            else "GET"
        )
        query: Dict[str, str] = {}
        body: Dict[str, Any] = {}
        for name, value in params.items():
            location = declared.get(name, {}).get("in")
            if location == "query" or (location is None and method == "GET"):
                query[name] = _query_value(value)
            else:
                body[name] = value

        try:
            response = requests.request(
                method,
                API_BASE + quote(path, safe="/"),
                params=query,
                json=body if method == "POST" else None,
                headers={
                    "x-api-key": self.api_key,
                    "accept": "application/json",
                },
                timeout=self._request_timeout,
                allow_redirects=False,
            )
        except requests.Timeout:
            return "Error: APIVerve did not respond in time. Retry shortly."
        except requests.RequestException:
            return "Error: APIVerve could not be reached. Retry shortly."

        try:
            payload = response.json()
        except ValueError:
            payload = None
        if not response.ok or (
            isinstance(payload, dict) and payload.get("status") == "error"
        ):
            return _redact(
                "Error: " + _error_message(response.status_code, payload),
                self.api_key,
            )
        if payload is None:
            return "Error: APIVerve returned a non-JSON response."
        result = (
            payload.get("data", payload)
            if isinstance(payload, dict)
            else payload
        )
        return _redact(result, self.api_key)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for the
                toolkit methods.
        """
        return [
            FunctionTool(self.search_apis),
            FunctionTool(self.call_api),
        ]
