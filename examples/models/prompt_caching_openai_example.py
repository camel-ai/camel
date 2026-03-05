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
OpenAI prompt caching example — let the agent fetch and analyse a blog.

OpenAI caching is automatic for prompts with 1024+ tokens.  The agent uses
a ``fetch_url`` tool to retrieve a web page, then answers follow-up questions.
Cached tokens appear in usage on subsequent requests.

Required environment variable:
  export OPENAI_API_KEY="sk-..."
"""

import httpx

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

BLOG_URL = (
    "https://www.camel-ai.org/blogs/"
    "seta-scaling-environments-for-terminal-agents"
)


def fetch_url(url: str) -> str:
    """Fetch the text content of a web page.

    Args:
        url: The URL to fetch.

    Returns:
        The page content as plain text.
    """
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.text


# ── Create model ───────────────────────────────────────────────────────────

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5,
    model_config_dict=ChatGPTConfig(
        prompt_cache_key="blog_analysis_cache",  # optional
    ).as_dict(),
)

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[FunctionTool(fetch_url)],
)

# ── First question: agent fetches the article itself ──────────────────────

response = agent.step(
    f"Please read this blog post and summarise it in 2-3 sentences: {BLOG_URL}"
)
print("[Question 1] Summarise the blog post.")
print(f"  Usage: {response.info.get('usage', {})}")
print(f"  Answer: {response.msgs[0].content[:200]}...")
print()

# ── Follow-up questions — caching kicks in automatically ─────────────────

follow_ups = [
    "What success rate did Claude Sonnet 4.5 achieve on Terminal-Bench 2.0?",
    "What are the main failure categories mentioned in the article?",
]

for i, question in enumerate(follow_ups, 2):
    response = agent.step(question)
    print(f"[Question {i}] {question}")
    print(f"  Usage: {response.info.get('usage', {})}")
    print(f"  Answer: {response.msgs[0].content[:200]}...")
    print()
