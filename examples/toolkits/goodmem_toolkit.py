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
r"""GoodMem + CAMEL ChatAgent example.

Four short scenarios that drive GoodMemToolkit through ChatAgent:
    1. Persistent project context across sessions (agent.reset()).
    2. Two-agent team knowledge pipeline (Scribe + Analyst).
    3. Structured team activity log with native metadata filtering.
    4. Tool-call inspection of the Analyst's response.

Requires GOODMEM_API_KEY, GOODMEM_BASE_URL, OPENAI_API_KEY. Set
GOODMEM_VERIFY_SSL=false for local dev with self-signed certs.
"""

import os
import time

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import GoodMemToolkit
from camel.types import ModelPlatformType, ModelType

verify_ssl = os.environ.get("GOODMEM_VERIFY_SSL", "true").lower() != "false"
goodmem_toolkit = GoodMemToolkit(verify_ssl=verify_ssl)

embedder_id = goodmem_toolkit.goodmem_list_embedders()[0]["embedderId"]
space_id = goodmem_toolkit.goodmem_create_space(
    name="camel-goodmem-example", embedder_id=embedder_id
)["spaceId"]
team_space_id = goodmem_toolkit.goodmem_create_space(
    name="camel-goodmem-example-team", embedder_id=embedder_id
)["spaceId"]
tagged_space_id = goodmem_toolkit.goodmem_create_space(
    name="camel-goodmem-example-tagged",
    embedder_id=embedder_id,
)["spaceId"]

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)
tools = goodmem_toolkit.get_tools()


# ---- Scenario 1: Persistent project context across sessions ----
print("\n=== Scenario 1: Persistent project context across sessions ===")
agent = ChatAgent(
    system_message=(
        "You are an engineering team assistant whose long-term "
        "memory is stored in GoodMem. When the user shares a "
        f"project fact, store it in GoodMem space '{space_id}'. "
        "When the user asks a question, retrieve the answer from "
        "that same space. Do not answer from your conversational "
        "memory."
    ),
    model=model,
    tools=tools,
)
for turn in [
    "I'm building a customer support assistant for our SaaS product.",
    "The team uses Python 3.12 with FastAPI and Postgres.",
    "For tests we use pytest with at least 80% coverage required.",
]:
    print(f"\nUser:  {turn}")
    print(f"Agent: {agent.step(turn).msgs[0].content}")

time.sleep(5)  # let indexing settle
agent.reset()

question = "Remind me what our coverage requirement is."
print(f"\nUser:  {question}")
print(f"Agent: {agent.step(question).msgs[0].content}")


# ---- Scenario 2: Two-agent team knowledge pipeline ----
print("\n=== Scenario 2: Two-agent team knowledge pipeline ===")
scribe = ChatAgent(
    system_message=(
        "You are a team Scribe. Store each team note verbatim in "
        f"GoodMem space '{team_space_id}' using "
        "goodmem_create_memory. Confirm storage briefly."
    ),
    model=model,
    tools=tools,
)
for note in [
    "Q2 goal: reduce customer support response time to under 2 hours.",
    "Our main services are auth-service, billing-service, and "
    "notifications-service.",
    "Known issue: notifications-service drops messages during high load.",
    "Team retro: the CI pipeline is too slow; we should parallelize tests.",
]:
    scribe.step(note)

time.sleep(5)

analyst = ChatAgent(
    system_message=(
        "You are a team Analyst. Search GoodMem space "
        f"'{team_space_id}' to answer team questions."
    ),
    model=model,
    tools=tools,
)
question = "What do we know about our services and current priorities?"
print(f"\nUser:  {question}")
print(f"Agent: {analyst.step(question).msgs[0].content}")


# ---- Scenario 3: Structured team activity log ----
print("\n=== Scenario 3: Structured team activity log ===")
tagger = ChatAgent(
    system_message=(
        "You are a release tagger. For each entry the user gives "
        f"you, call goodmem_create_memory on space "
        f"'{tagged_space_id}' with metadata_json that records the "
        "entry's category (one of: 'feat', 'fix', 'chore', 'docs')."
    ),
    model=model,
    tools=tools,
)
for content, category in [
    ("Added user profile editing to the dashboard.", "feat"),
    ("Built the CSV export feature.", "feat"),
    ("Resolved slow login on the mobile app.", "fix"),
    ("Fixed crash when opening large attachments.", "fix"),
    ("Upgraded Python version across services.", "chore"),
    ("Updated the API reference for billing endpoints.", "docs"),
]:
    tagger.step(f"Store: '{content}' with category '{category}'.")

time.sleep(5)

release_manager = ChatAgent(
    system_message=(
        "You are a release manager. The team activity log lives in "
        f"GoodMem space '{tagged_space_id}'. Each memory has a "
        "'category' metadata field (one of 'feat', 'fix', 'chore', "
        "'docs'). To answer category-specific questions, call "
        "goodmem_retrieve_memories with a metadata_filter, e.g. "
        "CAST(val('$.category') AS TEXT) = 'feat'. Report each "
        "result by its chunkText."
    ),
    model=model,
    tools=tools,
)
question = "Show me the new features we've shipped."
print(f"\nUser:  {question}")
response = release_manager.step(question)
print(f"Agent: {response.msgs[0].content}")


# ---- Scenario 4: Tool-call inspection ----
print("\n=== Scenario 4: Tool-call inspection ===")
for tool_call in response.info.get("tool_calls", []):
    print(f"  {tool_call.tool_name}({tool_call.args})")
