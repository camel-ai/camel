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
Gemini explicit context caching example — let the agent browse and analyse
a blog.

Unlike Anthropic/OpenAI's implicit caching, Gemini requires you to explicitly
create a cache, then reference it in requests via `cached_content`.

ModelFactory.create() returns a GeminiModel, so you can call cache management
methods (create_cache, list_caches, get_cache, update_cache, delete_cache)
directly on the model instance.

Required environment variable:
  export GEMINI_API_KEY="..."
"""

import httpx

from camel.agents import ChatAgent
from camel.configs import GeminiConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

BLOG_URL = (
    "https://www.camel-ai.org/blogs/"
    "seta-scaling-environments-for-terminal-agents"
)

# ── Fetch the blog content for explicit caching ───────────────────────────
# Gemini explicit caching requires creating a cache object upfront with the
# content in Gemini's native format, so we fetch the page first.

print(f"Fetching blog post from {BLOG_URL} ...")
resp = httpx.get(BLOG_URL, follow_redirects=True, timeout=30)
resp.raise_for_status()
blog_text = resp.text
print(f"Fetched {len(blog_text)} characters.\n")

# ── Create model via ModelFactory ──────────────────────────────────────────

model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_3_FLASH,
    model_config_dict=GeminiConfig(
        temperature=0.2,
    ).as_dict(),
)

# ── Create a cache with the blog content ───────────────────────────────────

cache_name = model.create_cache(
    contents=[{"role": "user", "parts": [{"text": blog_text}]}],
    ttl="300s",
    display_name="seta-blog-cache",
    system_instruction="You are a helpful assistant. Answer on the article.",
)
print(f"Cache created: {cache_name}\n")

# ── Ask multiple questions using the cache ─────────────────────────────────
# When cached_content is set, Gemini rejects requests that also send
# system_instruction, so pass system_message=None.

model.cached_content = cache_name
agent = ChatAgent(system_message=None, model=model)

questions = [
    "Summarise the SETA blog post in 2-3 sentences.",
    "What success rate did Claude Sonnet 4.5 achieve on Terminal-Bench 2.0?",
    "What are the main failure categories mentioned in the article?",
]

for i, question in enumerate(questions, 1):
    agent.reset()
    response = agent.step(question)
    usage = response.info.get("usage", {})
    print(f"[Question {i}] {question}")
    print(f"  Usage: {usage}")
    print(f"  Answer: {response.msgs[0].content[:200]}...")
    print()

# ── Clean up ───────────────────────────────────────────────────────────────

model.delete_cache(cache_name)
model.cached_content = None
print(f"Cache deleted: {cache_name}")
