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
Querit Search - Real API Call Examples

Before running, set your API key:
    export QUERIT_API_KEY="your_api_key_here"

Get your key at: https://www.querit.ai/en/dashboard/home
"""

import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType

# ── 0. Check API key ─────────────────────────────────────────────────────────
if not os.getenv("QUERIT_API_KEY"):
    raise EnvironmentError(
        "QUERIT_API_KEY is not set.\n"
        "Run: export QUERIT_API_KEY='your_key_here'\n"
        "Get your key at: https://www.querit.ai/en/dashboard/home"
    )

toolkit = SearchToolkit()

# ── 1. Basic search ───────────────────────────────────────────────────────────
print("=" * 60)
print("Example 1: Basic search")
print("=" * 60)

result = toolkit.search_querit(
    query="CAMEL-AI multi-agent framework",
    number_of_result_pages=3,
)
print(f"Search ID : {result.get('search_id')}")
print(f"Took      : {result.get('took')}")
for item in result.get("results", []):
    print(f"\n[{item['result_id']}] {item['title']}")
    print(f"    URL     : {item['url']}")
    print(f"    Snippet : {item['snippet'][:100]}...")
    print(f"    Age     : {item['page_age']}")

# ── 2. Search with filters ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Example 2: Search with filters (site / time / language)")
print("=" * 60)

result_filtered = toolkit.search_querit(
    query="multi-agent AI framework",
    number_of_result_pages=5,
    site_include=["github.com", "arxiv.org"],
    time_range="m6",  # past 6 months
    language_include=["english"],
)
print(f"Search ID : {result_filtered.get('search_id')}")
print(f"Took      : {result_filtered.get('took')}")
for item in result_filtered.get("results", []):
    print(f"\n[{item['result_id']}] {item['title']}")
    print(f"    URL : {item['url']}")

# ── 3. Search with geo filter ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Example 3: Search with geo + date range filter")
print("=" * 60)

result_geo = toolkit.search_querit(
    query="large language model benchmark",
    number_of_result_pages=5,
    time_range="2024-01-01to2024-12-31",
    country_include=["united states", "united kingdom"],
)
print(f"Search ID : {result_geo.get('search_id')}")
print(f"Took      : {result_geo.get('took')}")
for item in result_geo.get("results", []):
    print(f"\n[{item['result_id']}] {item['title']}")
    print(f"    URL : {item['url']}")

# ── 4. ChatAgent with Querit tool ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("Example 4: ChatAgent using Querit as a tool")
print("=" * 60)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

agent = ChatAgent(
    system_message=(
        "You are a helpful research assistant. "
        "Use the Querit search tool to find up-to-date information "
        "and summarize the results concisely."
    ),
    model=model,
    tools=[FunctionTool(toolkit.search_querit)],
)

response = agent.step(
    "What are the latest breakthroughs in multi-agent AI systems in 2025?"
)
print(response.msgs[0].content)
