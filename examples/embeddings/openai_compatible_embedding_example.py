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

from camel.embeddings import OpenAICompatibleEmbedding

# Set the embedding instance
nv_embed = OpenAICompatibleEmbedding(
    model_type="nvidia/nv-embed-v1",
    api_key="nvapi-xxx",
    url="https://integrate.api.nvidia.com/v1",
)

# Embed the text
text_embeddings = nv_embed.embed_list(["What is the capital of France?"])

print(len(text_embeddings[0]))
'''
===============================================================================
4096
===============================================================================
'''
