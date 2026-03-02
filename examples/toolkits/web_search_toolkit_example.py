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
    python examples/toolkits/web_search_toolkit_example.py
"""

import asyncio
import json

from camel.toolkits.headless_browser_search_toolkit import (
    HeadlessBrowserSearchToolkit,
)


# -- Example 1: Basic single-page search (Brave) -------------------------
async def example_basic_search():
    """Search Brave for a query and print structured results."""
    print("=" * 70)
    print("Example 1: Basic Brave search (1 page)")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave", num_pages=1)
    try:
        result_json = await toolkit.search("large language model applications")
        pages = json.loads(result_json)
        for page in pages:
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


# -- Example 2: Multi-page search ----------------------------------------
async def example_multi_page():
    """Fetch the first 3 pages of Brave results."""
    print("=" * 70)
    print("Example 2: Multi-page Brave search (3 pages)")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave", num_pages=3)
    try:
        result_json = await toolkit.search("climate change 2026")
        pages = json.loads(result_json)
        total = sum(p["total_results"] for p in pages)
        print(f"\nTotal results across {len(pages)} pages: {total}\n")
        for page in pages:
            print(
                f"--- Page {page['page']} "
                f"({page['total_results']} results) ---"
            )
            for r in page["results"][:5]:
                print(f"  - {r['title']}")
                print(f"    {r['url']}")
            if page["total_results"] > 5:
                print(f"  ... and {page['total_results'] - 5} more")
            print()
    finally:
        await toolkit.close()


# -- Example 3: Export results to JSON ------------------------------------
async def example_export_json():
    """Search and save results as a JSON file."""
    print("=" * 70)
    print("Example 3: Export results to JSON")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave", num_pages=2)
    try:
        result_json = await toolkit.search("python asyncio tutorial")
        data = json.loads(result_json)
        output_path = "web_search_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_path}")
        total = sum(d["total_results"] for d in data)
        print(f"Total results: {total}")
        print("\nSample entry:")
        if data and data[0]["results"]:
            print(
                json.dumps(
                    data[0]["results"][0],
                    indent=2,
                    ensure_ascii=False,
                )
            )
    finally:
        await toolkit.close()


# -- Example 4: Bing search ----------------------------------------------
async def example_bing_search():
    """Search using Bing engine."""
    print("=" * 70)
    print("Example 4: Bing search")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="bing", num_pages=1)
    try:
        result_json = await toolkit.search(
            "transformer architecture explained"
        )
        pages = json.loads(result_json)
        for page in pages:
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

    toolkit = HeadlessBrowserSearchToolkit(engine="google", num_pages=1)
    try:
        result_json = await toolkit.search("camel-ai framework")
        pages = json.loads(result_json)
        for page in pages:
            if not page["results"]:
                print(
                    f"\nPage {page['page']}: No results "
                    f"(likely blocked by captcha)."
                )
                print(
                    "  Tip: Google has aggressive IP-level "
                    "anti-bot detection."
                )
                print("  Consider using engine='brave' " "or engine='bing'.")
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
    print("Example 6: Reuse browser for multiple queries (Brave)")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave", num_pages=1)
    queries = [
        "python web scraping",
        "rust vs go performance",
        "camel-ai framework",
    ]
    try:
        for query in queries:
            result_json = await toolkit.search(query)
            pages = json.loads(result_json)
            count = sum(p["total_results"] for p in pages)
            top = None
            if pages and pages[0]["results"]:
                top = pages[0]["results"][0]
            print(f"\n  Query: {query!r}")
            print(f"  Results: {count}")
            if top:
                print(f"  Top hit: {top['title']}")
                print(f"           {top['url']}")
    finally:
        await toolkit.close()


# -- Example 7: Use with get_tools() for agent integration ---------------
async def example_agent_tools():
    """Show how to get FunctionTool list for agent integration."""
    print("=" * 70)
    print("Example 7: get_tools() for agent integration")
    print("=" * 70)

    toolkit = HeadlessBrowserSearchToolkit(engine="brave", num_pages=2)
    tools = toolkit.get_tools()
    for t in tools:
        schema = t.get_openai_tool_schema()
        print(f"\n  Tool: {schema['function']['name']}")
        print(f"  Desc: {schema['function']['description'][:80]}")
        params = schema['function']['parameters']
        print(f"  Params: {list(params['properties'])}")


async def main():
    await example_basic_search()
    # print("\n\n")
    # await example_multi_page()
    # print("\n\n")
    # await example_export_json()
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
