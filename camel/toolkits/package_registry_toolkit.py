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

import html
import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class PackageRegistryToolkit(BaseToolkit):
    r"""A toolkit for interacting with package registries such as PyPI
    and npm.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        request_timeout: float = 10.0,
    ) -> None:
        r"""Initializes the PackageRegistryToolkit.

        Args:
            timeout (Optional[float]): The timeout value for the toolkit in
                seconds. (default: :obj:`None`)
            request_timeout (float): The default HTTP request timeout in
                seconds. (default: :obj:`10.0`)
        """
        super().__init__(timeout=timeout)
        self.request_timeout = request_timeout
        self._headers = {
            "User-Agent": "camel-ai-PackageRegistryToolkit/1.0",
            "Accept": "application/json",
        }

    def _get_http_timeout(self) -> float:
        r"""Returns the effective HTTP timeout in seconds."""
        if self.timeout is not None:
            return float(self.timeout)
        return self.request_timeout

    def package_get_pypi_info(self, package_name: str) -> str:
        r"""Query PyPI for information about a specified Python package.

        Args:
            package_name (str): The name of the Python package to query.

        Returns:
            str: A JSON-formatted string containing package details including
                name, version, summary, home page, license, and dependencies,
                or an error message if the package is not found or the request
                fails.
        """
        if not package_name or not package_name.strip():
            return "Error: package_name must not be empty."

        clean_name = package_name.strip()
        quoted_name = urllib.parse.quote(clean_name)
        url = f"https://pypi.org/pypi/{quoted_name}/json"

        try:
            with httpx.Client(
                headers=self._headers,
                timeout=self._get_http_timeout(),
            ) as client:
                response = client.get(url)
                if response.status_code == 404:
                    return f"Package '{clean_name}' not found on PyPI."
                response.raise_for_status()
                data = response.json()

            info = data.get("info", {})
            name = info.get("name", clean_name)
            version = info.get("version", "Unknown")
            summary = info.get("summary", "")
            project_urls = info.get("project_urls") or {}
            home_page = (
                info.get("home_page")
                or project_urls.get("Homepage")
                or project_urls.get("Home")
                or project_urls.get("homepage")
                or ""
            )

            license_info = info.get("license", "")
            if not license_info:
                for classifier in info.get("classifiers", []):
                    if classifier.startswith("License ::"):
                        parts = classifier.split("::")
                        license_info = parts[-1].strip()
                        break

            dependencies = info.get("requires_dist") or []

            result = {
                "name": name,
                "version": version,
                "summary": summary,
                "home_page": home_page,
                "license": license_info,
                "dependencies": dependencies,
                "requires_dist": dependencies,
            }
            return json.dumps(result, indent=2)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Package '{clean_name}' not found on PyPI."
            logger.warning(
                f"HTTP error querying PyPI for package '{clean_name}': {e}"
            )
            return f"Error querying PyPI for package '{clean_name}': {e}"
        except httpx.RequestError as e:
            logger.warning(
                f"Network error querying PyPI for package '{clean_name}': {e}"
            )
            return f"Error querying PyPI for package '{clean_name}': {e}"
        except Exception as e:
            logger.warning(
                f"Unexpected error querying PyPI for package '{clean_name}': "
                f"{e}"
            )
            return f"Error querying PyPI for package '{clean_name}': {e}"

    def package_search_pypi(self, query: str, limit: int = 5) -> str:
        r"""Search PyPI for packages matching a query string.

        Args:
            query (str): The search query string.
            limit (int, optional): The maximum number of results to return.
                (default: :obj:`5`)

        Returns:
            str: A JSON-formatted string containing a list of matching
                packages with name, version, and description, or an error
                message if the search fails.
        """
        if not query or not query.strip():
            return "Error: query must not be empty."

        clean_query = query.strip()
        effective_limit = max(1, limit)
        search_url = "https://pypi.org/search/"
        headers = {
            **self._headers,
            "Accept": "text/html,application/json",
        }

        try:
            with httpx.Client(
                headers=headers,
                timeout=self._get_http_timeout(),
            ) as client:
                response = client.get(
                    search_url,
                    params={"q": clean_query},
                )
                packages = []

                if response.status_code == 200:
                    html_text = response.text
                    snippets = re.findall(
                        r'<a[^>]*class=[\"\'][^\"\']*package-snippet'
                        r'[^\"\']*[\"\'][^>]*>.*?</a>',
                        html_text,
                        re.DOTALL,
                    )
                    for snippet in snippets:
                        name_m = re.search(
                            r'class=[\"\']package-snippet__name[\"\']'
                            r'>([^<]+)</span>',
                            snippet,
                        )
                        ver_m = re.search(
                            r'class=[\"\']package-snippet__version[\"\']'
                            r'>([^<]+)</span>',
                            snippet,
                        )
                        desc_m = re.search(
                            r'<p[^>]*class=[\"\']package-snippet__description'
                            r'[\"\']>([^<]*)</p>',
                            snippet,
                            re.DOTALL,
                        )
                        if name_m and ver_m:
                            name = name_m.group(1).strip()
                            ver = ver_m.group(1).strip()
                            desc = ""
                            if desc_m:
                                desc = html.unescape(
                                    re.sub(r'<[^>]+>', '', desc_m.group(1))
                                ).strip()
                            packages.append(
                                {
                                    "name": name,
                                    "version": ver,
                                    "description": desc,
                                }
                            )
                            if len(packages) >= effective_limit:
                                break

                # Fallback: if HTML search returns no results, try querying
                # the exact package name on PyPI JSON endpoint
                if not packages:
                    try:
                        quoted_query = urllib.parse.quote(clean_query)
                        direct_resp = client.get(
                            f"https://pypi.org/pypi/{quoted_query}/json"
                        )
                        if direct_resp.status_code == 200:
                            direct_info = direct_resp.json().get("info", {})
                            packages.append(
                                {
                                    "name": direct_info.get(
                                        "name", clean_query
                                    ),
                                    "version": direct_info.get(
                                        "version", "Unknown"
                                    ),
                                    "description": direct_info.get(
                                        "summary", ""
                                    ),
                                }
                            )
                    except Exception:
                        pass

                return json.dumps(packages, indent=2)

        except httpx.RequestError as e:
            logger.warning(
                f"Network error searching PyPI for '{clean_query}': {e}"
            )
            return f"Error searching PyPI for '{clean_query}': {e}"
        except Exception as e:
            logger.warning(
                f"Unexpected error searching PyPI for '{clean_query}': {e}"
            )
            return f"Error searching PyPI for '{clean_query}': {e}"

    def package_get_npm_info(self, package_name: str) -> str:
        r"""Query npm registry for information about a specified
        JavaScript/Node.js package.

        Args:
            package_name (str): The name of the npm package to query,
                including any scope (e.g. "@types/node").

        Returns:
            str: A JSON-formatted string containing package details including
                name, version, description, license, and dependencies,
                or an error message if the package is not found or the request
                fails.
        """
        if not package_name or not package_name.strip():
            return "Error: package_name must not be empty."

        clean_name = package_name.strip()
        quoted_name = urllib.parse.quote(clean_name, safe="@")
        url = f"https://registry.npmjs.org/{quoted_name}"

        try:
            with httpx.Client(
                headers=self._headers,
                timeout=self._get_http_timeout(),
            ) as client:
                response = client.get(url)
                if response.status_code == 404:
                    return f"Package '{clean_name}' not found on npm."
                response.raise_for_status()
                data = response.json()

            dist_tags = data.get("dist-tags", {})
            latest_version = (
                dist_tags.get("latest") or data.get("version") or "Unknown"
            )
            description = data.get("description", "")
            license_info = data.get("license", "")
            if isinstance(license_info, dict):
                license_info = license_info.get("type", "")

            dependencies: Dict[str, Any] = {}
            versions = data.get("versions", {})
            if latest_version in versions:
                ver_data = versions[latest_version]
                description = ver_data.get("description") or description
                ver_license = ver_data.get("license")
                if ver_license:
                    if isinstance(ver_license, dict):
                        license_info = ver_license.get("type", "")
                    else:
                        license_info = ver_license
                dependencies = ver_data.get("dependencies") or {}
            elif "dependencies" in data:
                dependencies = data.get("dependencies") or {}

            result = {
                "name": data.get("name", clean_name),
                "version": latest_version,
                "description": description,
                "license": license_info,
                "dependencies": dependencies,
            }
            return json.dumps(result, indent=2)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Package '{clean_name}' not found on npm."
            logger.warning(
                f"HTTP error querying npm for package '{clean_name}': {e}"
            )
            return f"Error querying npm for package '{clean_name}': {e}"
        except httpx.RequestError as e:
            logger.warning(
                f"Network error querying npm for package '{clean_name}': {e}"
            )
            return f"Error querying npm for package '{clean_name}': {e}"
        except Exception as e:
            logger.warning(
                f"Unexpected error querying npm for package '{clean_name}': "
                f"{e}"
            )
            return f"Error querying npm for package '{clean_name}': {e}"

    def package_search_npm(self, query: str, limit: int = 5) -> str:
        r"""Search the npm registry for packages matching a query.

        Args:
            query (str): The search query string.
            limit (int, optional): The maximum number of results to return.
                (default: :obj:`5`)

        Returns:
            str: A JSON-formatted string containing a list of top matching
                packages with name, version, description, and links, or an
                error message if the search fails.
        """
        if not query or not query.strip():
            return "Error: query must not be empty."

        clean_query = query.strip()
        effective_limit = max(1, limit)
        url = "https://registry.npmjs.org/-/v1/search"

        try:
            with httpx.Client(
                headers=self._headers,
                timeout=self._get_http_timeout(),
            ) as client:
                response = client.get(
                    url,
                    params={"text": clean_query, "size": effective_limit},
                )
                response.raise_for_status()
                data = response.json()

            packages = []
            for obj in data.get("objects", [])[:effective_limit]:
                pkg = obj.get("package", {})
                packages.append(
                    {
                        "name": pkg.get("name", ""),
                        "version": pkg.get("version", ""),
                        "description": pkg.get("description", ""),
                        "links": pkg.get("links", {}),
                    }
                )
            return json.dumps(packages, indent=2)

        except httpx.RequestError as e:
            logger.warning(
                f"Network error searching npm for '{clean_query}': {e}"
            )
            return f"Error searching npm for '{clean_query}': {e}"
        except Exception as e:
            logger.warning(
                f"Unexpected error searching npm for '{clean_query}': {e}"
            )
            return f"Error searching npm for '{clean_query}': {e}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.package_get_pypi_info),
            FunctionTool(self.package_search_pypi),
            FunctionTool(self.package_get_npm_info),
            FunctionTool(self.package_search_npm),
        ]
