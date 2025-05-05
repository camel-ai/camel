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

from camel.embeddings import TogetherEmbedding

together_embed = TogetherEmbedding()

# Embed a single text
text_embeddings = together_embed.embed_list(["What is the capital of France?"])

print("Default model embedding dimension:", len(text_embeddings[0]))
'''
===============================================================================
Default model embedding dimension: 768
===============================================================================
'''

# Example with a different model
together_embed_alt = TogetherEmbedding(
    model_type="togethercomputer/m2-bert-80M-2k-retrieval",
)

# Embed multiple texts
texts = [
    "What is the capital of France?",
    "Paris is the capital of France.",
    "The Eiffel Tower is in Paris.",
]
text_embeddings_multi = together_embed_alt.embed_list(texts)

print("Alternative model embedding dimension:", len(text_embeddings_multi[2]))
'''
===============================================================================
Alternative model embedding dimension: 768
===============================================================================
'''
