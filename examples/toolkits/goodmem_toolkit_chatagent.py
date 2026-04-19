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
r"""GoodMem + CAMEL ChatAgent Example.

Demonstrates how the GoodMem toolkit integrates with CAMEL's ChatAgent
across four scenarios that highlight different ChatAgent capabilities:

    Scenario 1 -- Conversational memory agent
        A single ChatAgent runs a multi-turn conversation. The agent
        uses GoodMem tools autonomously to store facts the user shares
        and retrieve them when asked follow-up questions. Shows that
        ChatAgent's own conversation history coexists cleanly with an
        external semantic memory backend.

    Scenario 2 -- Cross-agent memory persistence
        A brand-new ChatAgent (with zero conversation history) answers
        questions about the user by querying GoodMem. This demonstrates
        the core value of an external memory store: memory outlives
        the agent instance.

    Scenario 3 -- Metadata-tagged memories
        Stores memories tagged with a 'category' field via metadata_json,
        then has an agent list the memories and filter by category.
        Shows that structured metadata round-trips through GoodMem and
        is available to agents for downstream reasoning.

    Scenario 4 -- Tool-call inspection
        Prints the tool calls the agent made via response.info.
        Useful for debugging agent behavior and proving that a
        tool-using agent actually reached for the toolkit rather
        than answering from its own weights.

Prerequisites:
    - A running GoodMem server (see https://docs.goodmem.ai)
    - An OpenAI API key (or any CAMEL-supported LLM provider)
    - At least one embedder registered on your GoodMem server

Usage::

    # 1. Set environment variables. Either export them directly, or
    #    store them in a .env file at the repository root.
    export OPENAI_API_KEY="sk-..."
    export GOODMEM_API_KEY="gm_..."
    export GOODMEM_BASE_URL="https://localhost:8080"

    # 2. Run the example
    python examples/toolkits/goodmem_toolkit_chatagent.py

Note:
    This example uses OpenAI via ModelPlatformType.DEFAULT, but any
    CAMEL-supported provider works. Swap the ModelFactory.create call
    and set the provider's API key instead.

    Optional environment variable:

        GOODMEM_VERIFY_SSL
            Whether to verify the GoodMem server's TLS certificate.
            Defaults to "true". Set it to "false" only when
            connecting to a server that uses a self-signed
            certificate (e.g. a local dev instance on
            https://localhost). Keep it "true" in production or
            anywhere the server uses a CA-signed certificate.
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests
import urllib3

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import GoodMemToolkit
from camel.types import ModelPlatformType, ModelType

REQUIRED_ENV_VARS = [
    (
        "GOODMEM_API_KEY",
        "GoodMem API key (sent as X-API-Key).",
    ),
    (
        "GOODMEM_BASE_URL",
        "Base URL of your GoodMem server, e.g. https://localhost:8080.",
    ),
    (
        "OPENAI_API_KEY",
        "OpenAI API key used by the CAMEL default model. "
        "Swap the ModelFactory.create call to use a different "
        "provider.",
    ),
]


def check_env_vars() -> None:
    """Exit with a helpful message if required env vars are missing."""
    missing = [
        (name, desc)
        for name, desc in REQUIRED_ENV_VARS
        if not os.environ.get(name)
    ]
    if not missing:
        return

    lines = [
        "Error: missing required environment variables:",
        "",
    ]
    for name, desc in missing:
        lines.append(f"  - {name}: {desc}")
    lines.extend(
        [
            "",
            "Set them before running, e.g.:",
            "",
            "  bash:",
            "    export GOODMEM_API_KEY='gm_...'",
            "    export GOODMEM_BASE_URL='https://localhost:8080'",
            "    export OPENAI_API_KEY='sk-...'",
            "",
            "  PowerShell:",
            "    $env:GOODMEM_API_KEY='gm_...'",
            "    $env:GOODMEM_BASE_URL='https://localhost:8080'",
            "    $env:OPENAI_API_KEY='sk-...'",
        ]
    )
    sys.exit("\n".join(lines))


# =========================================================================
# Configuration
# =========================================================================

SPACE_NAME = "camel-goodmem-chatagent-example"

SCENARIO_1_TURNS = [
    "I live in Austin, Texas.",
    "My favorite database is AcmeDB.",
    "What's my favorite database?",
    "And where do I live?",
]

SCENARIO_2_QUESTION = "Tell me everything you know about the user."

# Scenario 3 fixtures -- (content, category) pairs written directly
# via the toolkit so the metadata is deterministic. An agent then
# queries these and filters by the 'category' metadata field.
TAGGED_FACTS = [
    ("I work as a senior engineer at Acme Corp.", "work"),
    ("My manager is named Sarah.", "work"),
    ("I play guitar every Saturday morning.", "hobby"),
    ("I run 5 miles every Sunday.", "hobby"),
    ("I have a black cat named Luna.", "personal"),
]

SCENARIO_3_QUESTION = "Show me only the facts whose category is 'hobby'."


# =========================================================================
# Helpers
# =========================================================================


def section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def subsection(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{'- ' * 30}")
    print(f"  {title}")
    print(f"{'- ' * 30}")


def setup_space(goodmem_toolkit: GoodMemToolkit) -> str:
    """Discover an embedder and create (or reuse) the demo space."""
    try:
        embedders = goodmem_toolkit.goodmem_list_embedders()
    except requests.HTTPError as http_error:
        status = (
            http_error.response.status_code
            if (http_error.response is not None)
            else None
        )
        if status == 401:
            sys.exit(
                "Error: GoodMem rejected the request with 401 "
                "Unauthorized.\n"
                "Your GOODMEM_API_KEY is set but invalid or expired. "
                "Double-check the value in your environment or .env "
                "file."
            )
        if status == 403:
            sys.exit(
                "Error: GoodMem rejected the request with 403 "
                "Forbidden.\n"
                "Your GOODMEM_API_KEY is valid but does not have "
                "permission for this operation."
            )
        raise
    except requests.exceptions.SSLError:
        sys.exit(
            "Error: TLS certificate verification failed for "
            f"{goodmem_toolkit.base_url}.\n"
            "If the server uses a self-signed certificate (e.g. a "
            "local dev instance), set GOODMEM_VERIFY_SSL=false."
        )
    except requests.ConnectionError:
        sys.exit(
            "Error: could not connect to the GoodMem server at "
            f"{goodmem_toolkit.base_url}.\n"
            "Verify GOODMEM_BASE_URL is correct and the server is "
            "running."
        )

    if not embedders:
        sys.exit(
            "Error: No embedders found on the GoodMem server.\n"
            "Register one first -- see https://docs.goodmem.ai"
        )
    embedder_id = embedders[0]["embedderId"]
    print(f"  Using embedder: {embedders[0].get('displayName', embedder_id)}")

    space_result = goodmem_toolkit.goodmem_create_space(
        name=SPACE_NAME, embedder_id=embedder_id
    )
    space_id = space_result["spaceId"]
    reused = space_result.get("reused", False)
    print(
        f"  Space '{SPACE_NAME}' "
        f"({'reused' if reused else 'created'}): {space_id}"
    )
    return space_id


def cleanup(goodmem_toolkit: GoodMemToolkit, space_ids: list[str]) -> None:
    """Best-effort cleanup: delete every memory in each space, then
    each space itself."""
    for space_id in space_ids:
        if not space_id:
            continue
        try:
            memories = goodmem_toolkit.goodmem_list_memories(space_id=space_id)
        except Exception:
            memories = []

        print(f"  Space {space_id}: deleting {len(memories)} memories...")
        for memory in memories:
            memory_id = memory.get("memoryId") or memory.get("id")
            if not memory_id:
                continue
            try:
                goodmem_toolkit.goodmem_delete_memory(memory_id=memory_id)
            except Exception:
                pass  # Best-effort cleanup

        print(f"  Deleting space {space_id}...")
        try:
            goodmem_toolkit.goodmem_delete_space(space_id=space_id)
        except Exception:
            pass  # Best-effort cleanup

    print("  Cleanup complete.")


# =========================================================================
# Scenarios
# =========================================================================


def scenario_1_conversational_agent(
    goodmem_toolkit: GoodMemToolkit, space_id: str
) -> ChatAgent:
    """Run a multi-turn conversation on a single ChatAgent.

    The agent has all 11 GoodMem tools. Over 4 turns it stores two
    facts and then retrieves them in response to follow-up questions.
    """
    section("Scenario 1: Conversational memory agent (multi-turn)")

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=(
            "You are a personal assistant with access to a semantic "
            "memory store via GoodMem tools. When the user shares a "
            "fact about themselves, store it as a memory in the "
            f"GoodMem space with ID '{space_id}'. When the user asks "
            "a question about themselves, search that same space "
            "before answering. Always call a GoodMem tool rather "
            "than relying on your own memory."
        ),
        model=model,
        tools=goodmem_toolkit.get_tools(),
    )

    for turn_index, user_message in enumerate(SCENARIO_1_TURNS, start=1):
        print(f"\n  Turn {turn_index}")
        print(f"  User:  {user_message}")
        response = agent.step(user_message)
        print(f"  Agent: {response.msgs[0].content}")

        # Wait briefly after write turns so indexing catches up before
        # the next read turn.
        if turn_index in (1, 2):
            time.sleep(3)

    return agent


def scenario_2_cross_agent_memory(
    goodmem_toolkit: GoodMemToolkit, space_id: str
):
    """Prove GoodMem outlives the agent instance.

    Spins up a brand-new ChatAgent with an empty ChatHistoryMemory and
    asks it what it knows about the user. The only way it can answer
    is by calling goodmem_retrieve_memories against the shared space.
    """
    section("Scenario 2: Cross-agent memory persistence")
    print("  (Building a fresh ChatAgent with no prior conversation history.)")

    # A short wait lets any late-arriving indexing from Scenario 1
    # finish before the reader agent queries.
    time.sleep(3)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    reader_agent = ChatAgent(
        system_message=(
            "You are a knowledge assistant. Use the GoodMem tools "
            f"to search space '{space_id}' and answer questions "
            "based on what you find there."
        ),
        model=model,
        tools=goodmem_toolkit.get_tools(),
    )

    print(f"\n  User:  {SCENARIO_2_QUESTION}")
    response = reader_agent.step(SCENARIO_2_QUESTION)
    print(f"  Agent: {response.msgs[0].content}")

    return response


def scenario_3_metadata_filtering(
    goodmem_toolkit: GoodMemToolkit,
) -> tuple[str, object]:
    """Demonstrate metadata-tagged memories.

    Writes five memories with a 'category' metadata field directly via
    the toolkit (deterministic), then has a ChatAgent list them and
    filter by category. Returns the tagged space ID (for cleanup) and
    the agent's response (so Scenario 4 can inspect it).
    """
    section("Scenario 3: Metadata-tagged memories and filtering")

    # Use a dedicated space so the tagged memories don't mix with
    # Scenario 1's untagged ones.
    embedders = goodmem_toolkit.goodmem_list_embedders()
    embedder_id = embedders[0]["embedderId"]
    tagged_space_name = f"{SPACE_NAME}-tagged"
    space_result = goodmem_toolkit.goodmem_create_space(
        name=tagged_space_name, embedder_id=embedder_id
    )
    tagged_space_id = space_result["spaceId"]
    print(f"  Using space '{tagged_space_name}': {tagged_space_id}")

    # Write tagged memories directly. Doing this via the toolkit
    # (rather than through the agent) keeps the metadata payload
    # deterministic for the demo.
    print(f"\n  Ingesting {len(TAGGED_FACTS)} tagged memories...")
    for content, category in TAGGED_FACTS:
        goodmem_toolkit.goodmem_create_memory(
            space_id=tagged_space_id,
            text_content=content,
            metadata_json=json.dumps({"category": category}),
        )
        print(f"    [{category:>8}] {content}")

    # Let indexing catch up before the agent reads.
    print("  Waiting for indexing to complete...")
    time.sleep(5)

    # Now let a ChatAgent reason about the metadata.
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )
    analyst_agent = ChatAgent(
        system_message=(
            "You are a knowledge analyst with access to GoodMem tools. "
            f"The memories live in space '{tagged_space_id}'. Each "
            "memory has a 'category' field in its metadata (one of: "
            "'work', 'hobby', 'personal'). When the user asks about a "
            "specific category, use goodmem_list_memories to fetch "
            "every memory in the space and filter by the "
            "metadata.category field yourself. Do not rely on "
            "semantic search alone."
        ),
        model=model,
        tools=goodmem_toolkit.get_tools(),
    )

    print(f"\n  User:  {SCENARIO_3_QUESTION}")
    response = analyst_agent.step(SCENARIO_3_QUESTION)
    print(f"  Agent: {response.msgs[0].content}")

    return tagged_space_id, response


def scenario_4_inspect_response(response) -> None:
    """Print the tool calls the agent made.

    ChatAgent exposes rich metadata in response.info -- tool_calls,
    usage (token counts), finish_reasons, etc. Listing tool_calls
    is the most useful slice for proving the agent actually used
    GoodMem end-to-end.
    """
    section("Scenario 4: Tool-call inspection")

    tool_calls = response.info.get("tool_calls", [])
    print(f"\n  Tool calls made: {len(tool_calls)}")
    for i, tool_call in enumerate(tool_calls, start=1):
        result_preview = str(tool_call.result)
        if len(result_preview) > 120:
            result_preview = result_preview[:120] + "..."
        print(f"    {i}. {tool_call.tool_name}({tool_call.args})")
        print(f"       -> {result_preview}")


# =========================================================================
# Main
# =========================================================================


def main() -> None:
    """Run all four scenarios end-to-end."""
    check_env_vars()

    print("=" * 60)
    print("  GoodMem + CAMEL ChatAgent Example")
    print("=" * 60)

    # verify_ssl comes from GOODMEM_VERIFY_SSL env var; defaults to
    # True so the safe behaviour is the default in production.
    verify_ssl = (
        os.environ.get("GOODMEM_VERIFY_SSL", "true").lower() != "false"
    )
    if not verify_ssl:
        # Suppress the matching urllib3 warning so the output stays clean.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    goodmem_toolkit = GoodMemToolkit(verify_ssl=verify_ssl)

    subsection("Setup: Discovering embedder and creating space")
    space_id = setup_space(goodmem_toolkit)
    tagged_space_id: str | None = None

    try:
        scenario_1_conversational_agent(goodmem_toolkit, space_id)
        scenario_2_cross_agent_memory(goodmem_toolkit, space_id)
        tagged_space_id, analyst_response = scenario_3_metadata_filtering(
            goodmem_toolkit
        )
        scenario_4_inspect_response(analyst_response)
    finally:
        subsection("Cleanup")
        spaces_to_clean = [space_id]
        if tagged_space_id:
            spaces_to_clean.append(tagged_space_id)
        cleanup(goodmem_toolkit, spaces_to_clean)
        goodmem_toolkit.close()

    print(f"\n{'=' * 60}")
    print("  Done!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
