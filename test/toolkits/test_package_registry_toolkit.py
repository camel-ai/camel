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

import httpx
import pytest

from camel.toolkits import FunctionTool, PackageRegistryToolkit


@pytest.fixture
def toolkit():
    return PackageRegistryToolkit(request_timeout=5.0)


# ============================================================================
# PyPI Info Tests
# ============================================================================


def test_package_get_pypi_info_success(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "info": {
                    "name": "requests",
                    "version": "2.31.0",
                    "summary": "Python HTTP for Humans.",
                    "home_page": "https://requests.readthedocs.io",
                    "license": "Apache-2.0",
                    "requires_dist": [
                        "charset_normalizer<4,>=2",
                        "idna<4,>=2.5",
                        "urllib3<3,>=1.26",
                    ],
                }
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_get_pypi_info("requests")
    data = json.loads(res_str)

    assert data["name"] == "requests"
    assert data["version"] == "2.31.0"
    assert data["summary"] == "Python HTTP for Humans."
    assert data["home_page"] == "https://requests.readthedocs.io"
    assert data["license"] == "Apache-2.0"
    assert len(data["dependencies"]) == 3
    assert data["requires_dist"] == data["dependencies"]


def test_package_get_pypi_info_project_urls_and_classifier_license(
    toolkit, monkeypatch
):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "info": {
                    "name": "my-pkg",
                    "version": "1.0.0",
                    "summary": "Sample package",
                    "home_page": None,
                    "project_urls": {
                        "Homepage": "https://example.com/my-pkg",
                    },
                    "license": "",
                    "classifiers": [
                        "Programming Language :: Python :: 3",
                        "License :: OSI Approved :: MIT License",
                    ],
                    "requires_dist": None,
                }
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_get_pypi_info("my-pkg")
    data = json.loads(res_str)

    assert data["name"] == "my-pkg"
    assert data["home_page"] == "https://example.com/my-pkg"
    assert data["license"] == "MIT License"
    assert data["dependencies"] == []


def test_package_get_pypi_info_not_found(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_get_pypi_info("non-existent-pkg")
    assert "not found on PyPI" in res


def test_package_get_pypi_info_http_error(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(500, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_get_pypi_info("error-pkg")
    assert "Error querying PyPI" in res
    assert "500" in res


def test_package_get_pypi_info_network_error(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_get_pypi_info("requests")
    assert "Error querying PyPI" in res or "Network error" in res
    assert "Connection refused" in res


def test_package_get_pypi_info_empty_name(toolkit):
    res = toolkit.package_get_pypi_info("")
    assert "Error" in res


# ============================================================================
# PyPI Search Tests
# ============================================================================


def test_package_search_pypi_html_success(toolkit, monkeypatch):
    html_content = """
    <ul class="unstyled" aria-label="Search results">
      <li>
        <a class="package-snippet" href="/project/pkg-a/">
          <h3 class="package-snippet__title">
            <span class="package-snippet__name">pkg-a</span>
            <span class="package-snippet__version">1.0.0</span>
          </h3>
          <p class="package-snippet__description">
            Package A description &amp; more
          </p>
        </a>
      </li>
      <li>
        <a class="package-snippet" href="/project/pkg-b/">
          <h3 class="package-snippet__title">
            <span class="package-snippet__name">pkg-b</span>
            <span class="package-snippet__version">2.1.0</span>
          </h3>
          <p class="package-snippet__description">Package B description</p>
        </a>
      </li>
    </ul>
    """

    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            headers={"content-type": "text/html"},
            text=html_content,
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_search_pypi("pkg", limit=5)
    results = json.loads(res_str)

    assert len(results) == 2
    assert results[0]["name"] == "pkg-a"
    assert results[0]["version"] == "1.0.0"
    assert results[0]["description"] == "Package A description & more"
    assert results[1]["name"] == "pkg-b"


def test_package_search_pypi_limit_respected(toolkit, monkeypatch):
    html_content = (
        '<a class="package-snippet">'
        '<span class="package-snippet__name">p1</span>'
        '<span class="package-snippet__version">1</span>'
        '<p class="package-snippet__description">d1</p></a>'
        '<a class="package-snippet">'
        '<span class="package-snippet__name">p2</span>'
        '<span class="package-snippet__version">2</span>'
        '<p class="package-snippet__description">d2</p></a>'
        '<a class="package-snippet">'
        '<span class="package-snippet__name">p3</span>'
        '<span class="package-snippet__version">3</span>'
        '<p class="package-snippet__description">d3</p></a>'
    )

    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req, text=html_content)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_search_pypi("p", limit=2)
    results = json.loads(res_str)
    assert len(results) == 2
    assert results[0]["name"] == "p1"
    assert results[1]["name"] == "p2"


def test_package_search_pypi_fallback_to_json(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        if "pypi.org/search" in url:
            # Emulate blocked search / no snippet
            return httpx.Response(403, request=req, text="Forbidden")
        if "pypi.org/pypi/exact-pkg/json" in url:
            return httpx.Response(
                200,
                request=req,
                json={
                    "info": {
                        "name": "exact-pkg",
                        "version": "3.0.0",
                        "summary": "Exact matching package",
                    }
                },
            )
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_search_pypi("exact-pkg", limit=5)
    results = json.loads(res_str)

    assert len(results) == 1
    assert results[0]["name"] == "exact-pkg"
    assert results[0]["version"] == "3.0.0"
    assert results[0]["description"] == "Exact matching package"


def test_package_search_pypi_no_results(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_search_pypi("non-existent-pkg")
    results = json.loads(res_str)
    assert results == []


def test_package_search_pypi_empty_query(toolkit):
    res = toolkit.package_search_pypi("")
    assert "Error" in res


def test_package_search_pypi_network_error(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        raise httpx.ReadTimeout("Read timed out")

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_search_pypi("requests")
    assert "Error searching PyPI" in res
    assert "Read timed out" in res


# ============================================================================
# NPM Info Tests
# ============================================================================


def test_package_get_npm_info_success(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "name": "express",
                "description": "Fast web framework",
                "license": "MIT",
                "dist-tags": {"latest": "4.18.2"},
                "versions": {
                    "4.18.2": {
                        "name": "express",
                        "version": "4.18.2",
                        "description": "Fast web framework",
                        "license": "MIT",
                        "dependencies": {
                            "accepts": "~1.3.8",
                            "cookie": "0.5.0",
                        },
                    }
                },
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_get_npm_info("express")
    data = json.loads(res_str)

    assert data["name"] == "express"
    assert data["version"] == "4.18.2"
    assert data["description"] == "Fast web framework"
    assert data["license"] == "MIT"
    assert data["dependencies"] == {"accepts": "~1.3.8", "cookie": "0.5.0"}


def test_package_get_npm_info_scoped_package(toolkit, monkeypatch):
    requested_url = None

    def fake_get(self, url, **kwargs):
        nonlocal requested_url
        requested_url = url
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "name": "@types/node",
                "description": "TypeScript definitions for node",
                "license": {"type": "MIT"},
                "dist-tags": {"latest": "20.0.0"},
                "versions": {
                    "20.0.0": {
                        "dependencies": {"undici-types": "~5.26.4"},
                    }
                },
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_get_npm_info("@types/node")
    data = json.loads(res_str)

    assert "@types%2Fnode" in requested_url
    assert data["name"] == "@types/node"
    assert data["version"] == "20.0.0"
    assert data["license"] == "MIT"
    assert "undici-types" in data["dependencies"]


def test_package_get_npm_info_not_found(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_get_npm_info("non-existent-npm-pkg")
    assert "not found on npm" in res


def test_package_get_npm_info_http_error(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(500, request=req)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_get_npm_info("err-pkg")
    assert "Error querying npm" in res
    assert "500" in res


def test_package_get_npm_info_network_error(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        raise httpx.ConnectTimeout("Connection timed out")

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_get_npm_info("express")
    assert "Error querying npm" in res
    assert "Connection timed out" in res


def test_package_get_npm_info_empty_name(toolkit):
    res = toolkit.package_get_npm_info("")
    assert "Error" in res


# ============================================================================
# NPM Search Tests
# ============================================================================


def test_package_search_npm_success(toolkit, monkeypatch):
    def fake_get(self, url, params=None, **kwargs):
        req = httpx.Request("GET", url, params=params)
        return httpx.Response(
            200,
            request=req,
            json={
                "total": 2,
                "objects": [
                    {
                        "package": {
                            "name": "react",
                            "version": "18.2.0",
                            "description": "React is a JavaScript library",
                            "links": {
                                "npm": "https://www.npmjs.com/package/react"
                            },
                        }
                    },
                    {
                        "package": {
                            "name": "react-dom",
                            "version": "18.2.0",
                            "description": (
                                "React package for working with DOM"
                            ),
                            "links": {
                                "npm": "https://www.npmjs.com/package/react-dom"
                            },
                        }
                    },
                ],
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_search_npm("react", limit=5)
    results = json.loads(res_str)

    assert len(results) == 2
    assert results[0]["name"] == "react"
    assert results[0]["version"] == "18.2.0"
    assert "React is a JavaScript library" in results[0]["description"]
    assert results[0]["links"]["npm"] == "https://www.npmjs.com/package/react"


def test_package_search_npm_limit(toolkit, monkeypatch):
    def fake_get(self, url, params=None, **kwargs):
        req = httpx.Request("GET", url, params=params)
        size = params.get("size", 5) if params else 5
        objects = [
            {"package": {"name": f"pkg-{i}", "version": f"1.{i}.0"}}
            for i in range(10)
        ]
        return httpx.Response(
            200, request=req, json={"total": 10, "objects": objects[:size]}
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res_str = toolkit.package_search_npm("pkg", limit=3)
    results = json.loads(res_str)
    assert len(results) == 3


def test_package_search_npm_empty_query(toolkit):
    res = toolkit.package_search_npm("")
    assert "Error" in res


def test_package_search_npm_network_error(toolkit, monkeypatch):
    def fake_get(self, url, **kwargs):
        raise httpx.RequestError("Host unreachable")

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    res = toolkit.package_search_npm("react")
    assert "Error searching npm" in res
    assert "Host unreachable" in res


# ============================================================================
# Toolkit Setup and Tools Tests
# ============================================================================


def test_get_tools(toolkit):
    tools = toolkit.get_tools()
    assert len(tools) == 4
    tool_names = {t.func.__name__ for t in tools}
    assert tool_names == {
        "package_get_pypi_info",
        "package_search_pypi",
        "package_get_npm_info",
        "package_search_npm",
    }
    for t in tools:
        assert isinstance(t, FunctionTool)
        schema = t.get_openai_tool_schema()
        assert "function" in schema
        assert schema["function"]["name"] == t.func.__name__


def test_toolkit_timeout_configuration():
    tk1 = PackageRegistryToolkit(timeout=15.0)
    assert tk1._get_http_timeout() == 15.0

    tk2 = PackageRegistryToolkit(request_timeout=25.0)
    assert tk2._get_http_timeout() == 25.0

    with pytest.raises(ValueError):
        PackageRegistryToolkit(timeout=-1)
