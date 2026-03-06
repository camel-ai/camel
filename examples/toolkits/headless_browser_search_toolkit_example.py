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
"""HeadlessBrowserSearchToolkit Example."""

import asyncio
import json

from camel.toolkits.headless_browser_search_toolkit import (
    HeadlessBrowserSearchToolkit,
)


async def example_basic_search():
    """Search with all args: query, engine, page."""
    toolkit = HeadlessBrowserSearchToolkit()
    result_json = await toolkit.search(
        query="large language model",
        engine="brave",
        page=1,
    )
    page = json.loads(result_json)
    print(f"Results: {page['total_results']}")
    for r in page["results"][:3]:
        print(f"  {r['title']}")
        print(f"    {r['url']}")


async def example_agent_tools():
    """Show FunctionTool schema for agent integration.

    Expected output::

        Tool: search
        Params: ['query', 'engine', 'page']
        Schema:
        {
          "type": "function",
          "function": {
            "name": "search",
            "parameters": {
              "properties": {
                "query":  {"type": "string", ...},
                "engine": {"type": ["string", "null"], ...},
                "page":   {"type": ["integer", "null"], ...}
              },
              "required": ["query", "engine", "page"]
            }
          }
        }
    """
    toolkit = HeadlessBrowserSearchToolkit()
    tools = toolkit.get_tools()
    for t in tools:
        schema = t.get_openai_tool_schema()
        func = schema["function"]
        params = func["parameters"]
        print(f"Tool: {func['name']}")
        print(f"Params: {list(params['properties'])}")
        print("Schema:")
        print(json.dumps(schema, indent=2))


async def main():
    await example_basic_search()
    # await example_agent_tools()


if __name__ == "__main__":
    asyncio.run(main())
