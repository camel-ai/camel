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
"""HeadlessBrowserSearchToolkit Example

Demonstrates how to use the HeadlessBrowserSearchToolkit to perform
structured web searches via a headless browser with stealth mode.

Supported engines: "brave" (recommended), "bing", "google"

Note:
  - Brave Search: Best overall. No anti-bot blocks, 20 results per
    page, clean direct URLs, fast.
  - Bing: Works well. 10 results per page.
  - Google: Has aggressive IP-level anti-bot detection. May return
    captcha pages even with stealth mode.

Usage:
    python examples/toolkits/headless_browser_search_toolkit_example.py
"""

import asyncio
import json

from camel.toolkits.headless_browser_search_toolkit import (
    HeadlessBrowserSearchToolkit,
)


# -- Example 1: Basic search (page 1, Brave) -----------------------------
async def example_basic_search():
    """Search Brave and print page 1 results."""
    print("=" * 70)
    print("Example 1: Basic Brave search (page 1)")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave")
    try:
        result_json = await toolkit.search(
            "large language model applications"
        )
        page = json.loads(result_json)
        print(
            f"\nPage {page['page']} - "
            f"{page['total_results']} results\n"
        )
        for i, r in enumerate(page["results"], 1):
            print(f"  [{i}] {r['title']}")
            print(f"      URL:     {r['url']}")
            if r.get("snippet"):
                print(f"      Snippet: {r['snippet'][:120]}")
            print()
    finally:
        await toolkit.close()


# -- Example 2: Fetch a specific page (page 3) ---------------------------
async def example_specific_page():
    """Fetch page 3 of Brave results."""
    print("=" * 70)
    print("Example 2: Brave search page 3")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(
        engine="brave", num_pages=3
    )
    try:
        result_json = await toolkit.search("climate change 2026")
        page = json.loads(result_json)
        print(
            f"\nPage {page['page']} - "
            f"{page['total_results']} results\n"
        )
        for r in page["results"][:5]:
            print(f"  - {r['title']}")
            print(f"    {r['url']}")
        if page["total_results"] > 5:
            extra = page["total_results"] - 5
            print(f"  ... and {extra} more")
    finally:
        await toolkit.close()


# -- Example 3: Override num_pages at call time ---------------------------
async def example_override_page():
    """Default is page 1, but override to page 2 at call time."""
    print("=" * 70)
    print("Example 3: Override num_pages at call time")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave")
    try:
        result_json = await toolkit.search(
            "python asyncio tutorial", num_pages=2
        )
        page = json.loads(result_json)
        print(
            f"\nPage {page['page']} - "
            f"{page['total_results']} results\n"
        )
        for i, r in enumerate(page["results"][:5], 1):
            print(f"  [{i}] {r['title']}")
            print(f"      {r['url']}")
    finally:
        await toolkit.close()


# -- Example 4: Bing search ----------------------------------------------
async def example_bing_search():
    """Search using Bing engine."""
    print("=" * 70)
    print("Example 4: Bing search (page 1)")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="bing")
    try:
        result_json = await toolkit.search(
            "transformer architecture explained"
        )
        page = json.loads(result_json)
        print(
            f"\nPage {page['page']} - "
            f"{page['total_results']} results\n"
        )
        for i, r in enumerate(page["results"][:5], 1):
            print(f"  [{i}] {r['title']}")
            print(f"      {r['url']}")
            if r.get("snippet"):
                print(f"      {r['snippet'][:120]}")
            print()
    finally:
        await toolkit.close()


# -- Example 5: Google search (may be blocked) ----------------------------
async def example_google_search():
    """Try Google search. Falls back gracefully if captcha."""
    print("=" * 70)
    print("Example 5: Google search (stealth mode)")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="google")
    try:
        result_json = await toolkit.search("camel-ai framework")
        page = json.loads(result_json)
        if not page["results"]:
            print(
                f"\nPage {page['page']}: No results "
                f"(likely blocked by captcha)."
            )
            print(
                "  Tip: Google has aggressive IP-level "
                "anti-bot detection."
            )
            print(
                "  Consider using engine='brave' "
                "or engine='bing'."
            )
        else:
            n = page["total_results"]
            print(f"\nPage {page['page']} - {n} results\n")
            for i, r in enumerate(page["results"][:5], 1):
                print(f"  [{i}] {r['title']}")
                print(f"      {r['url']}")
                print()
    finally:
        await toolkit.close()


# -- Example 6: Reuse browser across queries ------------------------------
async def example_reuse_browser():
    """Reuse the same browser session for multiple searches."""
    print("=" * 70)
    print("Example 6: Reuse browser for multiple queries")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave")
    queries = [
        "python web scraping",
        "rust vs go performance",
        "camel-ai framework",
    ]
    try:
        for query in queries:
            result_json = await toolkit.search(query)
            page = json.loads(result_json)
            count = page["total_results"]
            top = None
            if page["results"]:
                top = page["results"][0]
            print(f"\n  Query: {query!r}")
            print(f"  Results: {count}")
            if top:
                print(f"  Top hit: {top['title']}")
                print(f"           {top['url']}")
    finally:
        await toolkit.close()


# -- Example 7: get_tools() for agent integration ------------------------
async def example_agent_tools():
    """Show how to get FunctionTool list for agent integration."""
    print("=" * 70)
    print("Example 7: get_tools() for agent integration")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(
        engine="brave", num_pages=2
    )
    tools = toolkit.get_tools()
    for t in tools:
        schema = t.get_openai_tool_schema()
        print(f"\n  Tool: {schema['function']['name']}")
        desc = schema['function']['description'][:80]
        print(f"  Desc: {desc}")
        params = schema['function']['parameters']
        print(f"  Params: {list(params['properties'])}")


async def main():
    await example_basic_search()
    # print("\n\n")
    # await example_specific_page()
    # print("\n\n")
    # await example_override_page()
    # print("\n\n")
    # await example_bing_search()
    # print("\n\n")
    # await example_google_search()
    # print("\n\n")
    # await example_reuse_browser()
    # print("\n\n")
    # await example_agent_tools()


if __name__ == "__main__":
    asyncio.run(main())
