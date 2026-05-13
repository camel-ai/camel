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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType

# ── 0. Check API key ─────────────────────────────────────────────────────────
if not os.getenv("PERPLEXITY_API_KEY"):
    raise EnvironmentError(
        "PERPLEXITY_API_KEY is not set.\n"
        "Run: export PERPLEXITY_API_KEY='your_key_here'\n"
        "Get your key at: https://www.perplexity.ai/account/api"
    )

toolkit = SearchToolkit()

# ── 1. Basic search ──────────────────────────────────────────────────────────
print("=" * 60)
print("Example 1: Basic search")
print("=" * 60)

result = toolkit.search_perplexity(
    query="CAMEL-AI multi-agent framework",
    max_results=3,
)
print(f"Search ID   : {result.get('id')}")
print(f"Server time : {result.get('server_time')}")
for index, item in enumerate(result.get("results", []), start=1):
    print(f"\n[{index}] {item.get('title')}")
    print(f"    URL     : {item.get('url')}")
    print(f"    Snippet : {item.get('snippet')}")
    print(f"    Date    : {item.get('date')}")

# ── 2. Search with recency / country filters ────────────────────────────────
print("\n" + "=" * 60)
print("Example 2: Search with recency and country filters")
print("=" * 60)

result_filtered = toolkit.search_perplexity(
    query="latest advances in multi-agent AI systems",
    max_results=5,
    country="US",
    search_recency_filter="month",
)
print(f"Search ID   : {result_filtered.get('id')}")
for index, item in enumerate(result_filtered.get("results", []), start=1):
    print(f"\n[{index}] {item.get('title')}")
    print(f"    URL : {item.get('url')}")

# ── 3. Search with domain + language filters ────────────────────────────────
print("\n" + "=" * 60)
print("Example 3: Search with domain and language filters")
print("=" * 60)

result_domain = toolkit.search_perplexity(
    query="large language model benchmark",
    max_results=5,
    search_domain_filter=["github.com", "arxiv.org"],
    search_language_filter=["en"],
)
print(f"Search ID   : {result_domain.get('id')}")
for index, item in enumerate(result_domain.get("results", []), start=1):
    print(f"\n[{index}] {item.get('title')}")
    print(f"    URL : {item.get('url')}")

# ── 4. ChatAgent with Perplexity tool ───────────────────────────────────────
print("\n" + "=" * 60)
print("Example 4: ChatAgent using Perplexity as a tool")
print("=" * 60)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

agent = ChatAgent(
    system_message=(
        "You are a helpful research assistant. "
        "Use the Perplexity search tool to find up-to-date information "
        "and summarize the results concisely."
    ),
    model=model,
    tools=[FunctionTool(toolkit.search_perplexity)],
)

response = agent.step(
    "What are the latest breakthroughs in multi-agent AI systems in 2025?"
)
print(response.msgs[0].content)
