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

1. Configure caching in ChatAgent initialization with threshold and cache_dir
2. Ask the agent to capture two snapshots: a long smartphone page and a short
   weather widget
3. Use tool_call_history_cache=True in a step() call to cache tool outputs
   exceeding the threshold
4. Ask the agent a question requiring BOTH cached snapshots - it will use the
   automatically registered ``retrieve_cached_tool_output`` tool to access them
5. Verify the agent can also retrieve a single snapshot when needed

The example demonstrates:
- Automatic caching of large tool outputs (>600 chars)
- Memory efficiency (cached references vs full content)
- Agent's ability to retrieve single or multiple cached outputs
- Seamless access to cached data without manual intervention

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
            result_length = len(result)
            preview = result.replace("\n", " ")[:140]
            if cache_id:
                print(
                    f"{idx:02d}. role={role} tool_call_id={message.tool_call_id} "  # noqa:E501
                    f"(cached reference) cache_id={cache_id} "
                    f"result_length={result_length}"
                )
                print(f"      preview: {preview}")
            else:
                print(
                    f"{idx:02d}. role={role} tool_call_id={message.tool_call_id} "  # noqa:E501
                    f"(inline) result_length={result_length}"
                )
                print(f"      preview: {preview}")
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
        model_platform=ModelPlatformType.AZURE,
        model_type=ModelType.GPT_4_1_MINI,
    )
    agent = ChatAgent(
        system_message=("You are a browsing assistant."),
        model=backend,
        tools=[FunctionTool(cache_browser_snapshot)],
        prune_tool_calls_from_memory=False,
        max_iteration=3,
        tool_call_cache_threshold=600,
        tool_call_cache_dir=cache_dir,
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

    print("\n>>> Step 2: Capture weather snapshot")
    prompt2 = (
        "Now you are looking at a weather dashboard."
        "Save the widget below as a new snapshot "
        "without paraphrasing it:\n\n"
        f"{WEATHER_DASHBOARD}"
    )
    # Print memory before caching
    print("\n=== Memory BEFORE tool_call_history_cache ===")
    response2 = agent.step(prompt2)
    print(f"Assistant response: {response2.msg.content}")
    _print_memory(agent)

    # Print memory after caching (using tool_call_history_cache=True)
    print("\n=== Memory AFTER tool_call_history_cache ===")
    response2_cached = agent.step(
        "Confirm that both snapshots have been saved.",
        tool_call_history_cache=True,
    )
    print(f"Assistant response: {response2_cached.msg.content}")
    _print_memory(agent)

    cached_entry = _find_cached_entry(agent)
    if not cached_entry or not cached_entry.cache_id:
        print(
            "\nNo cached entry detected. Ensure the tool was executed and the threshold is high enough."  # noqa:E501
        )
        return

    print("\n>>> Step 3: Ask question requiring BOTH cached snapshots")
    prompt3 = (
        "Compare the information from both snapshots you saved earlier:\n"
        "1. From the NovaPhone store page, tell me the battery capacity "
        "of the NovaPhone X Ultra\n"
        "2. From the weather dashboard, tell me the current temperature\n"
        "3. Make a comparison between these two pieces of information.\n\n"
        "You'll need to retrieve BOTH snapshots to answer this question."
    )
    response3 = agent.step(prompt3)
    print(f"Assistant response:\n{response3.msg.content}")

    print("\n>>> Step 4: Verify agent can access single snapshot")
    prompt4 = "Just tell me the sunset time from the weather widget."
    response4 = agent.step(prompt4)
    print(f"Assistant response:\n{response4.msg.content}")


if __name__ == "__main__":
    main()


'''
>>> Step 1: Capture verbose snapshot
Assistant response: The current NovaPhone X Ultra smartphone page has been stored exactly as-is. You can reference this full markup or request details from it at any time. Let me know if you need to retrieve, compare, or analyze any part of this page!

>>> Step 2: Capture weather snapshot

=== Memory BEFORE tool_call_history_cache ===
Assistant response: The weather dashboard widget has been stored exactly as you provided it. You can reference or retrieve this snapshot any time. Let me know if you need to review, compare, or analyze the widget's contents!
01. role=system content=You are a browsing assistant.
02. role=user content=You just browsed the NovaPhone store.Store the current smartphone page exactly as-is so we can reference it later. Here is the full markup:

03. role=assistant tool_call_id=call_AajvjXwUeugfncrhwEY9fiqy (inline) result_length=4
      preview: None
04. role=function tool_call_id=call_AajvjXwUeugfncrhwEY9fiqy (inline) result_length=1796
      preview: [browser_snapshot length=1726 characters] BEGIN_SNAPSHOT  <html>   <body>     <header>       <h1>NovaPhone X Ultra Launch Event</h1>       <
05. role=assistant content=The current NovaPhone X Ultra smartphone page has been stored exactly as-is. You can reference this full markup or request details from it a
06. role=user content=Now you are looking at a weather dashboard.Save the widget below as a new snapshot without paraphrasing it:


<div class="weather-widget">
 
07. role=assistant tool_call_id=call_BVR80Veg57rrDVsaxSwronfh (inline) result_length=4
      preview: None
08. role=function tool_call_id=call_BVR80Veg57rrDVsaxSwronfh (inline) result_length=294
      preview: [browser_snapshot length=225 characters] BEGIN_SNAPSHOT  <div class="weather-widget">   <h1>City Weather</h1>   <p>Currently 68°F, partly cl
09. role=assistant content=The weather dashboard widget has been stored exactly as you provided it. You can reference or retrieve this snapshot any time. Let me know i

=== Memory AFTER tool_call_history_cache ===
Assistant response: Confirmation: Both snapshots have been successfully saved.

1. NovaPhone smartphone page — contains the launch event details, specs, comparisons, and availability.
2. Weather dashboard widget — contains the city weather update, next hour forecast, sunset time, and UV index.

You can request contents or analysis from either snapshot at any time.
01. role=system content=You are a browsing assistant.
02. role=user content=You just browsed the NovaPhone store.Store the current smartphone page exactly as-is so we can reference it later. Here is the full markup:

03. role=assistant tool_call_id=call_AajvjXwUeugfncrhwEY9fiqy (inline) result_length=4
      preview: None
04. role=function tool_call_id=call_AajvjXwUeugfncrhwEY9fiqy (cached reference) cache_id=4d277c664504420eaa8ae2e5360873e7 result_length=345
      preview: [cached tool output] tool: cache_browser_snapshot cache_id: 4d277c664504420eaa8ae2e5360873e7 preview: [browser_snapshot length=1726 characte
05. role=assistant content=The current NovaPhone X Ultra smartphone page has been stored exactly as-is. You can reference this full markup or request details from it a
06. role=user content=Now you are looking at a weather dashboard.Save the widget below as a new snapshot without paraphrasing it:


<div class="weather-widget">
 
07. role=assistant tool_call_id=call_BVR80Veg57rrDVsaxSwronfh (inline) result_length=4
      preview: None
08. role=function tool_call_id=call_BVR80Veg57rrDVsaxSwronfh (inline) result_length=294
      preview: [browser_snapshot length=225 characters] BEGIN_SNAPSHOT  <div class="weather-widget">   <h1>City Weather</h1>   <p>Currently 68°F, partly cl
09. role=assistant content=The weather dashboard widget has been stored exactly as you provided it. You can reference or retrieve this snapshot any time. Let me know i
10. role=user content=Confirm that both snapshots have been saved.
11. role=assistant content=Confirmation: Both snapshots have been successfully saved.

1. NovaPhone smartphone page — contains the launch event details, specs, compari

>>> Step 3: Ask question requiring BOTH cached snapshots
Assistant response:
Based on the two snapshots I retrieved:

1. **NovaPhone X Ultra battery capacity:** 5,500 mAh

2. **Current temperature:** 68°F (partly cloudy)

3. **Creative comparison:**
   Interestingly, the NovaPhone X Ultra's battery capacity (5,500 mAh) is about
   80 times larger than the current temperature in degrees Fahrenheit (68°F)!

   While the phone can power through your day with its massive 5,500 mAh battery
   and 120W wired charging, the weather outside is a pleasant 68°F — perfect
   conditions for testing that new phone outdoors without worrying about
   overheating or cold-induced battery drain. The phone's battery is built for
   performance in any weather!

>>> Step 4: Verify agent can access single snapshot
Assistant response:
According to the weather widget snapshot, the sunset time is **7:42 PM**.
'''  # noqa: E501
