# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Real-model example for ChatAgent tool-output caching.

This demo uses a true LLM backend (configured via the default ``ModelFactory``)
and a mock browser snapshot tool. The workflow is:

1. Ask the agent to capture a very long snapshot (which will later be cached).
2. Capture a concise update, triggering the caching of the earlier verbose
   output.
3. Ask the agent to retrieve the cached payload using the automatically
   registered ``retrieve_cached_tool_output`` tool.

Prerequisites:
    - Set up the API credentials required by the default model backend
      (for example, ``OPENAI_API_KEY`` if you're using OpenAI models).
    - Optionally customize ``MODEL_PLATFORM`` / ``MODEL_TYPE`` via
      environment variables to point to a different provider.
"""

from __future__ import annotations

from pathlib import Path

from camel.agents import ChatAgent
from camel.messages import FunctionCallingMessage
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import (
    ModelPlatformType,
    ModelType,
)

# Mock payloads -------------------------------------------------------------
SMARTPHONE_PAGE = """
<html>
  <body>
    <header>
      <h1>NovaPhone X Ultra Launch Event</h1>
      <p>The flagship with HDR+ Pro display, titanium frame, and satellite SOS.</p>
      <a class="cta-button" href="/buy">Pre-order now</a>
    </header>
    <section id="hero-carousel">
      <article>
        <h2>New Horizon Display</h2>
        <p>6.9" adaptive 1-144Hz, peak brightness 4000 nits, Dolby Vision certified.</p>
      </article>
      <article>
        <h2>Pro Camera Array</h2>
        <p>Quad 50MP sensors, 200x adaptive zoom, neural night portrait, macro mode.</p>
      </article>
      <article>
        <h2>Performance</h2>
        <p>NovaCore G3 chip, 12GB LPDDR6, 1TB UFS 5.1 storage, Wi-Fi 7 ready.</p>
      </article>
    </section>
    <section id="comparisons">
      <table>
        <tr><th>Model</th><th>Battery</th><th>Charging</th><th>Starting Price</th></tr>
        <tr><td>NovaPhone X Ultra</td><td>5,500 mAh</td><td>120W wired / 80W wireless</td><td>$1099</td></tr>
        <tr><td>NovaPhone X</td><td>5,000 mAh</td><td>80W wired / 50W wireless</td><td>$899</td></tr>
        <tr><td>NovaPhone Air</td><td>4,700 mAh</td><td>45W wired / 25W wireless</td><td>$749</td></tr>
      </table>
    </section>
    <section id="availability">
      <p>Pre-orders open March 14, shipping starts March 28 in US, EU, and APAC.</p>
      <ul>
        <li>Colorways: Graphite Black, Aurora Blue, Sunset Copper, Alpine Ice.</li>
        <li>Accessories: Smart Folio, 65W travel adapter, satellite communicator.</li>
        <li>Trade-in bonus up to $450 for eligible devices.</li>
      </ul>
    </section>
    <footer>
      <p>Visit our Experience Labs for hands-on demos. Terms apply.</p>
    </footer>
  </body>
</html>
"""  # noqa: E501

WEATHER_DASHBOARD = """
<div class="weather-widget">
  <h1>City Weather</h1>
  <p>Currently 68°F, partly cloudy.</p>
  <p>Next hour: breezy with scattered clouds, no precipitation expected.</p>
  <p>Sunset at 7:42 PM, UV index moderate.</p>
</div>
"""


# Tool implementation -------------------------------------------------------
def cache_browser_snapshot(snapshot: str) -> str:
    """Return the provided snapshot verbatim so the cache can persist it."""
    header = (
        f"[browser_snapshot length={len(snapshot)} characters]\n"
        "BEGIN_SNAPSHOT\n"
    )
    return header + snapshot + "\nEND_SNAPSHOT"


# Utility functions ---------------------------------------------------------
def _print_memory(agent: ChatAgent) -> None:
    print("\n=== Memory after second step ===")
    for idx, ctx_record in enumerate(agent.memory.retrieve(), start=1):
        record = ctx_record.memory_record
        message = record.message
        role = record.role_at_backend.value
        if isinstance(message, FunctionCallingMessage):
            meta = message.meta_dict or {}
            cache_id = meta.get("cache_id")
            result = (
                message.result
                if isinstance(message.result, str)
                else str(message.result)
            )
            preview = result.replace("\n", " ")[:140]
            if cache_id:
                print(
                    f"{idx:02d}. role={role} tool_call_id={message.tool_call_id} "  # noqa:E501
                    f"(cached reference) cache_id={cache_id}"
                )
                print(f"      preview: {preview}")
            else:
                print(
                    f"{idx:02d}. role={role} tool_call_id={message.tool_call_id} "  # noqa:E501
                    f"(inline) preview={preview}"
                )
        else:
            content = getattr(message, "content", "") or ""
            print(f"{idx:02d}. role={role} content={content[:140]}")


def _find_cached_entry(agent: ChatAgent):
    for entry in agent._tool_output_history:
        if entry.cached:
            return entry
    return None


# Demo flow -----------------------------------------------------------------
def main() -> None:
    cache_dir = Path(__file__).resolve().parent / "tool_cache"
    backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
    )
    agent = ChatAgent(
        system_message=("You are a browsing assistant."),
        model=backend,
        tools=[FunctionTool(cache_browser_snapshot)],
        enable_tool_output_cache=True,
        tool_output_cache_threshold=600,
        tool_output_cache_dir=cache_dir,
        prune_tool_calls_from_memory=False,
        max_iteration=3,
    )

    print("\n>>> Step 1: Capture verbose snapshot")
    prompt1 = (
        "You just browsed the NovaPhone store."
        "Store the current smartphone page exactly as-is "
        "so we can reference it later. Here is the full markup:\n\n"
        f"{SMARTPHONE_PAGE}"
    )
    response1 = agent.step(prompt1)
    print(f"Assistant response: {response1.msg.content}")

    print(
        "\n>>> Step 2: Capture weather snapshot (triggers caching of step 1)"
    )
    prompt2 = (
        "Now you are looking at a weather dashboard."
        "Save the widget below as a new snapshot "
        "without paraphrasing it:\n\n"
        f"{WEATHER_DASHBOARD}"
    )
    response2 = agent.step(prompt2)
    print(f"Assistant response: {response2.msg.content}")

    _print_memory(agent)

    cached_entry = _find_cached_entry(agent)
    if not cached_entry or not cached_entry.cache_id:
        print(
            "\nNo cached entry detected. Ensure the tool was executed and the threshold is high enough."  # noqa:E501
        )
        return

    print("\n>>> Step 3: Ask about the smartphone page (trigger retrieval)")
    prompt3 = (
        "I need the details from the hero banner on the smartphone store "
        "page—especially what it says about the display and core specs."
        "Check whichever snapshots you recorded earlier before you answer."
    )
    response3 = agent.step(prompt3)
    print(f"Assistant response:\n{response3.msg.content}")


if __name__ == "__main__":
    main()


'''
>>> Step 1: Capture verbose snapshot
Assistant response: I have saved the current smartphone page from the NovaPhone store exactly as provided. You can reference it later as needed.

>>> Step 2: Capture weather snapshot (triggers caching of step 1)
Assistant response: The weather widget has been saved exactly as provided without any paraphrasing. Let me know if you'd like to do anything else with it.

=== Memory after second step ===
01. role=system content=You are a browsing assistant. Whenever you need to capture or recall a page, use the available tools to record or retrieve the exact text be
02. role=user content=You just browsed the NovaPhone store. Store the current smartphone page exactly as-is so we can reference it later. Here is the full markup:
03. role=assistant tool_call_id=call_iIILkyZtQvrfXHuLCMB2KWnM (inline) preview=None
04. role=function tool_call_id=call_iIILkyZtQvrfXHuLCMB2KWnM (cached reference) cache_id=bd07770e0c0f461fbe31b4237f90ce2c
      preview: [cached tool output] tool: cache_browser_snapshot cache_id: bd07770e0c0f461fbe31b4237f90ce2c preview: [browser_snapshot length=1724 character
05. role=assistant content=I have saved the current smartphone page from the NovaPhone store exactly as provided. You can reference it later as needed.
06. role=user content=Now you are looking at a weather dashboard. Save the widget below as a new snapshot without paraphrasing it:


<div class="weather-widget">

07. role=assistant tool_call_id=call_wfl2szFZLV58kRhhRPsJPMnx (inline) preview=None
08. role=function tool_call_id=call_wfl2szFZLV58kRhhRPsJPMnx (inline) preview=[browser_snapshot length=224 characters] BEGIN_SNAPSHOT <div class="weather-widget">   <h1>City Weather</h1>   <p>Currently 686F, partly cl
09. role=assistant content=The weather widget has been saved exactly as provided without any paraphrasing. Let me know if you'd like to do anything else with it.

>>> Step 3: Ask about the smartphone page (should trigger retrieval)
Assistant response:
From the hero banner section of the smartphone store page the details about the display and core specs are:

- Display (under "New Horizon Display"):
  6.9" adaptive 1-144Hz, peak brightness 4000 nits, Dolby Vision certified.

- Performance (under "Performance"):
  NovaCore G3 chip, 12GB LPDDR6, 1TB UFS 5.1 storage, Wi-Fi 7 ready.

Let me know if you want more details from the page.
'''  # noqa: E501
