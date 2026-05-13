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

"""
Perplexity Search - Real API Call Examples

Before running, set your API key:
    export PERPLEXITY_API_KEY="your_api_key_here"

Get your key at: https://www.perplexity.ai/account/api
"""

import os
from typing import Any

from camel.toolkits import SearchToolkit

if not os.getenv("PERPLEXITY_API_KEY"):
    raise EnvironmentError(
        "PERPLEXITY_API_KEY is not set.\n"
        "Run: export PERPLEXITY_API_KEY='your_key_here'\n"
        "Get your key at: https://www.perplexity.ai/account/api"
    )


def print_results(response: dict[str, Any]) -> None:
    r"""Print Perplexity search results in a readable format."""
    if error := response.get("error"):
        print(f"Error: {error}")
        return

    print(f"Search ID   : {response.get('id')}")
    print(f"Server time : {response.get('server_time')}")
    for index, item in enumerate(response.get("results", []), start=1):
        print(f"\n[{index}] {item.get('title')}")
        print(f"    URL          : {item.get('url')}")
        print(f"    Snippet      : {item.get('snippet')}")
        print(f"    Date         : {item.get('date')}")
        print(f"    Last updated : {item.get('last_updated')}")


def main() -> None:
    r"""Run Perplexity search toolkit examples."""
    toolkit = SearchToolkit()

    print("=" * 60)
    print("Example 1: Basic search")
    print("=" * 60)
    basic_result = toolkit.search_perplexity(
        query="CAMEL-AI multi-agent framework",
    )
    print_results(basic_result)

    print("\n" + "=" * 60)
    print("Example 2: Search with recency and country filters")
    print("=" * 60)
    filtered_result = toolkit.search_perplexity(
        query="latest advances in multi-agent AI systems",
        max_results=5,
        country="US",
        search_recency_filter="month",
    )
    print_results(filtered_result)


if __name__ == "__main__":
    main()
