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
AWS Bedrock Converse prompt caching example — let the agent fetch and
analyse a blog.

AWSBedrockConverseModel supports implicit prompt caching via the Converse API.
Set ``cache_control`` in BedrockConfig to enable it.

Required environment variables:
  export AWS_REGION="us-east-1"
  export AWS_ACCESS_KEY_ID="..."
  export AWS_SECRET_ACCESS_KEY="..."
  # Or use bearer token auth:
  export BEDROCK_API_KEY="..."
"""

import httpx

from camel.agents import ChatAgent
from camel.configs import BedrockConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType

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


# ── Create model with prompt caching ──────────────────────────────────────

model = ModelFactory.create(
    model_platform=ModelPlatformType.AWS_BEDROCK_CONVERSE,
    model_type="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    model_config_dict=BedrockConfig(
        cache_control="5m",
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

# ── Follow-up questions reuse the cached context ─────────────────────────

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
