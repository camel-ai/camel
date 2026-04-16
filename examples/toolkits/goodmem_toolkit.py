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
r"""GoodMem + CAMEL Agent Example.

Demonstrates how to use GoodMem as a semantic memory backend for a
CAMEL ChatAgent.  The agent uses GoodMem tools to store documents,
retrieve relevant passages, and answer questions grounded in stored
knowledge.

The example walks through every step:

    1. Connect to GoodMem and discover embedders
    2. Create a space and ingest sample documents as memories
    3. Ask the agent questions answered from stored memories
    4. Inspect the raw memory record
    5. Clean up (delete memories and space)

Prerequisites:
    - A running GoodMem server (see https://docs.goodmem.ai)
    - An OpenAI API key (or any CAMEL-supported LLM provider)
    - At least one embedder registered on your GoodMem server

Usage::

    # 1. Set environment variables
    export OPENAI_API_KEY="sk-..."
    export GOODMEM_API_KEY="gm_..."
    export GOODMEM_BASE_URL="https://localhost:8080"

    # 2. Run the example
    python examples/toolkits/goodmem_toolkit.py

Note:
    This example uses OpenAI via ``ModelPlatformType.DEFAULT``, but any
    CAMEL-supported provider works.  Swap the ``ModelFactory.create``
    call and set the provider's API key instead.

    For self-signed certificates (e.g. local dev), set
    ``verify_ssl=False`` in the ``GoodMemToolkit`` constructor.
"""

from __future__ import annotations

import sys
import time

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import GoodMemToolkit
from camel.types import ModelPlatformType, ModelType

# =========================================================================
# Configuration
# =========================================================================

# A small fictional knowledge base about "Acme Corp".  Each string
# becomes one GoodMem memory.  GoodMem will chunk, embed, and index
# these so they can be retrieved later via semantic search.
DOCUMENTS = [
    (
        "Acme Corp was founded in 2019 by Jane Smith and Carlos "
        "Rivera in Austin, Texas. The company started as a "
        "two-person garage project focused on making databases "
        "easier to operate at scale."
    ),
    (
        "Acme Corp's flagship product is AcmeDB, a cloud-native "
        "distributed database designed for real-time analytics. "
        "AcmeDB supports ACID transactions, horizontal sharding, "
        "and automatic failover across multiple availability zones."
    ),
    (
        "In March 2023, Acme Corp raised $50 million in Series B "
        "funding led by Benchmark Capital, with participation from "
        "Sequoia and Y Combinator Continuity. The round valued the "
        "company at $400 million."
    ),
    (
        "AcmeDB's free tier supports up to 10 GB of storage, "
        "1 million reads per month, and 100,000 writes per month. "
        "Paid plans start at $29/month for the Starter tier and "
        "$199/month for the Professional tier."
    ),
    (
        "Acme Corp is headquartered in Austin, Texas, with remote "
        "engineering offices in Berlin, Germany and Bangalore, "
        "India. The company employs approximately 120 people "
        "across all locations as of early 2024."
    ),
]

SPACE_NAME = "camel-goodmem-example"

QUESTIONS = [
    "When was Acme Corp founded and by whom?",
    "How much funding did Acme Corp raise in Series B?",
    "What are the storage limits on AcmeDB's free tier?",
]


# =========================================================================
# Helpers
# =========================================================================


def section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'- ' * 30}")
    print(f"  {title}")
    print(f"{'- ' * 30}")


# =========================================================================
# Main
# =========================================================================


def main() -> None:
    """Run the full GoodMem + CAMEL agent example end-to-end."""

    print("=" * 60)
    print("  GoodMem + CAMEL Agent Example")
    print("=" * 60)

    # --- Configuration ---
    # Set verify_ssl=False for self-signed certificates in local dev.
    goodmem_toolkit = GoodMemToolkit(verify_ssl=False)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=(
            "You are a helpful assistant with access to a semantic "
            "memory store via GoodMem tools. Use these tools to "
            "store and retrieve information. When answering "
            "questions, always search your memories first."
        ),
        model=model,
        tools=goodmem_toolkit.get_tools(),
    )

    # ---- Step 1: Discover embedders ----
    section("Step 1: Discovering embedders")
    embedders = goodmem_toolkit.goodmem_list_embedders()
    if not embedders:
        sys.exit(
            "Error: No embedders found on the GoodMem server.\n"
            "Register one first -- see https://docs.goodmem.ai"
        )
    embedder_id = embedders[0]["embedderId"]
    print(f"  Using embedder: {embedders[0].get('displayName', embedder_id)}")

    # ---- Step 2: Create a space ----
    section("Step 2: Creating space")
    space_result = goodmem_toolkit.goodmem_create_space(
        name=SPACE_NAME, embedder_id=embedder_id
    )
    space_id = space_result["spaceId"]
    reused = space_result.get("reused", False)
    print(
        f"  Space '{SPACE_NAME}' "
        f"({'reused' if reused else 'created'}): {space_id}"
    )

    # ---- Step 3: Ingest documents ----
    section("Step 3: Ingesting documents")
    memory_ids: list[str] = []
    for i, document in enumerate(DOCUMENTS):
        result = goodmem_toolkit.goodmem_create_memory(
            space_id=space_id, text_content=document
        )
        memory_ids.append(result["memoryId"])
        print(f"  [{i + 1}/{len(DOCUMENTS)}] memoryId={result['memoryId']}")

    # Wait for indexing to complete before querying.
    print("  Waiting for indexing to complete...")
    time.sleep(5)

    # ---- Step 4: Ask the agent questions ----
    section("Step 4: Asking questions (agent-driven retrieval)")
    for i, question in enumerate(QUESTIONS):
        print(f"\n  Q{i + 1}: {question}")
        response = agent.step(
            f"Search my memories in space {space_id} to answer: {question}"
        )
        print(f"  A{i + 1}: {response.msgs[0].content}")

    # ---- Step 5: Inspect a memory record ----
    section("Step 5: Inspecting a memory record")
    memory_record = goodmem_toolkit.goodmem_get_memory(
        memory_id=memory_ids[0], include_content=True
    )
    memory_metadata = memory_record["memory"]
    print(f"  Memory ID:   {memory_metadata.get('memoryId')}")
    print(f"  Status:      {memory_metadata.get('processingStatus')}")
    print(f"  Content type: {memory_metadata.get('contentType')}")
    content = memory_record.get("content", "")
    preview = content[:100] if isinstance(content, str) else ""
    print(f"  Content:     {preview}...")

    # ---- Step 6: Cleanup ----
    section("Step 6: Cleaning up")
    print(f"  Deleting {len(memory_ids)} memories...")
    for memory_id in memory_ids:
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
    goodmem_toolkit.close()

    print(f"\n{'=' * 60}")
    print("  Done!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
