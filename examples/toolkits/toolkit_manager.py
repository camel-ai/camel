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
from camel.agents import ChatAgent
from camel.toolkits import (
    MathToolkit,
    SearchToolkit,
    SemanticScholarToolkit,
    ToolkitManager,
    WeatherToolkit,
)

# Aggregate several toolkits. Together these expose dozens of tools; exposing
# all of them to a model at once would bloat the context and hurt tool
# selection. The default "bm25" backend is keyword based and needs no API key;
# pass search_backend="embedding" for semantic matching instead.
manager = ToolkitManager(
    [
        MathToolkit(),
        SearchToolkit(),
        WeatherToolkit(),
        SemanticScholarToolkit(),
    ]
)

print(f"{manager}\nRegistered {len(manager)} tools:")
print("  " + ", ".join(manager.tool_names))

# ---------------------------------------------------------------------------
# Pattern 1: static pre-filtering
# ---------------------------------------------------------------------------
# Retrieve only the tools relevant to the task and hand them to the agent.
query = "find an academic paper by its title"
relevant_tools = manager.search_tools(query, top_k=3, with_scores=True)

print(f"\nTop tools for: {query!r}")
for function_tool, score in relevant_tools:
    print(f"  {function_tool.get_function_name():28s} score={score:.3f}")

focused_agent = ChatAgent(
    "You are a helpful research assistant.",
    tools=[tool for tool, _ in relevant_tools],
)
# focused_agent only sees the 3 relevant tools instead of all of them.

# ---------------------------------------------------------------------------
# Pattern 2: agentic discovery
# ---------------------------------------------------------------------------
# Give the agent just two meta-tools (`search_tools` and `execute_tool`). It
# searches the full registry at runtime and calls tools on demand, keeping its
# context small no matter how many toolkits are registered.
discovery_agent = ChatAgent(
    "You can discover tools with `search_tools` and run them with "
    "`execute_tool`. Always search before executing.",
    tools=manager.get_search_tools(),
)

response = discovery_agent.step(
    "What is 2024 divided by 8? Find and use the right tool."
)
print(f"\nAgentic discovery answer:\n{response.msgs[0].content}")

"""
===============================================================================
ToolkitManager(num_tools=27, search_backend='bm25')
Registered 27 tools:
  math_add, math_subtract, ..., get_weather_data, fetch_paper_data_title, ...

Top tools for: 'find an academic paper by its title'
  fetch_paper_data_title       score=6.016
  fetch_paper_data_id          score=4.678
  fetch_bulk_paper_data        score=4.417

Agentic discovery answer:
2024 divided by 8 is 253.
===============================================================================
"""
