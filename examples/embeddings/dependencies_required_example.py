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
This example demonstrates how the @dependencies_required decorator is applied
to embedding classes in CAMEL.

Each embedding class guards its __init__ with @dependencies_required so that
users get a clear ImportError naming the missing package instead of a
confusing AttributeError or traceback deep inside the library.

Classes covered:
  - OpenAIEmbedding          requires: openai
  - AzureEmbedding           requires: openai
  - OpenAICompatibleEmbedding requires: openai
  - TogetherEmbedding        requires: openai
  - MistralEmbedding         requires: mistralai
  - GeminiEmbedding          requires: google.genai
  - JinaEmbedding            requires: requests, PIL
  - SentenceTransformerEncoder requires: sentence_transformers
  - VisionLanguageEmbedding  requires: transformers, PIL
"""

from unittest.mock import patch

from camel.embeddings import (
    AzureEmbedding,
    GeminiEmbedding,
    JinaEmbedding,
    MistralEmbedding,
    OpenAICompatibleEmbedding,
    OpenAIEmbedding,
    SentenceTransformerEncoder,
    TogetherEmbedding,
    VisionLanguageEmbedding,
)
from camel.utils.commons import is_module_available

# ── 1. Normal usage ──────────────────────────────────────────────────────────
# When all required packages are installed the decorator is completely
# transparent — it simply calls __init__ as usual.

openai_embed = OpenAIEmbedding()
text_embeddings = openai_embed.embed_list(["What is the capital of France?"])

print("OpenAIEmbedding dimension:", len(text_embeddings[0]))
'''
===============================================================================
OpenAIEmbedding dimension: 1536
===============================================================================
'''

# ── 2. Graceful error when a dependency is missing ───────────────────────────
# Simulate an environment where `openai` is not installed.


def _mock_missing(module_name: str):
    """Patch is_module_available to report module as absent."""

    def fake(m):
        if m == module_name:
            return False
        return is_module_available(m)

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


# OpenAIEmbedding — missing `openai`
with _mock_missing('openai'):
    try:
        OpenAIEmbedding(api_key="fake-key")
    except ImportError as error:
        print("OpenAIEmbedding ImportError:", error)
'''
===============================================================================
OpenAIEmbedding ImportError: Required package(s) ['openai'] are not
installed. Please install them with: pip install openai
===============================================================================
'''

# MistralEmbedding — missing `mistralai`
with _mock_missing('mistralai'):
    try:
        MistralEmbedding(api_key="fake-key")
    except ImportError as error:
        print("MistralEmbedding ImportError:", error)
'''
===============================================================================
MistralEmbedding ImportError: Required package(s) ['mistralai'] are not
installed. Please install them with: pip install mistralai
===============================================================================
'''

# GeminiEmbedding — missing `google.genai`
with _mock_missing('google.genai'):
    try:
        GeminiEmbedding(api_key="fake-key")
    except ImportError as error:
        print("GeminiEmbedding ImportError:", error)
'''
===============================================================================
GeminiEmbedding ImportError: Required package(s) ['google.genai'] are not
installed. Please install them with: pip install google.genai
===============================================================================
'''

# JinaEmbedding — missing `requests`
with _mock_missing('requests'):
    try:
        JinaEmbedding(api_key="fake-key")
    except ImportError as error:
        print("JinaEmbedding ImportError:", error)
'''
===============================================================================
JinaEmbedding ImportError: Required package(s) ['requests'] are not
installed. Please install them with: pip install requests
===============================================================================
'''

# AzureEmbedding — missing `openai`
with _mock_missing('openai'):
    try:
        AzureEmbedding(api_key="fake-key", url="https://fake.azure.com")
    except ImportError as error:
        print("AzureEmbedding ImportError:", error)
'''
===============================================================================
AzureEmbedding ImportError: Required package(s) ['openai'] are not
installed. Please install them with: pip install openai
===============================================================================
'''

# OpenAICompatibleEmbedding — missing `openai`
with _mock_missing('openai'):
    try:
        OpenAICompatibleEmbedding(
            model_type="text-embed",
            api_key="fake-key",
            url="http://fake-url",
        )
    except ImportError as error:
        print("OpenAICompatibleEmbedding ImportError:", error)
'''
===============================================================================
OpenAICompatibleEmbedding ImportError: Required package(s) ['openai'] are
not installed. Please install them with: pip install openai
===============================================================================
'''

# TogetherEmbedding — missing `openai`
with _mock_missing('openai'):
    try:
        TogetherEmbedding(api_key="fake-key")
    except ImportError as error:
        print("TogetherEmbedding ImportError:", error)
'''
===============================================================================
TogetherEmbedding ImportError: Required package(s) ['openai'] are not
installed. Please install them with: pip install openai
===============================================================================
'''

# SentenceTransformerEncoder — missing `sentence_transformers`
with _mock_missing('sentence_transformers'):
    try:
        SentenceTransformerEncoder()
    except ImportError as error:
        print("SentenceTransformerEncoder ImportError:", error)
'''
===============================================================================
SentenceTransformerEncoder ImportError: Required package(s)
['sentence_transformers'] are not installed. Please install them with:
pip install sentence_transformers
===============================================================================
'''

# VisionLanguageEmbedding — missing `transformers`
with _mock_missing('transformers'):
    try:
        VisionLanguageEmbedding()
    except ImportError as error:
        print("VisionLanguageEmbedding ImportError:", error)
'''
===============================================================================
VisionLanguageEmbedding ImportError: Required package(s) ['transformers']
are not installed. Please install them with: pip install transformers
===============================================================================
'''
