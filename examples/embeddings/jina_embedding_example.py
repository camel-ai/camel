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

import requests
from PIL import Image

from camel.embeddings import JinaEmbedding
from camel.types import EmbeddingModelType

# Set the text embedding instance
jina_text_embed = JinaEmbedding(
    model_type=EmbeddingModelType.JINA_EMBEDDINGS_V3,
)

# Embed the text
text_embeddings = jina_text_embed.embed_list(
    ["What is the capital of France?"]
)

print(len(text_embeddings[0]))
'''
===============================================================================
1024
===============================================================================
'''


# Set the code embedding instance
jina_code_embed = JinaEmbedding(
    model_type=EmbeddingModelType.JINA_EMBEDDINGS_V2_BASE_CODE,
    normalized=True,
)

# Embed the code
code_embeddings = jina_code_embed.embed_list(
    [
        "Calculates the square of a number. Parameters: number (int or float)"
        " - The number to square. Returns: int or float - The square of the"
        " number.",
        "This function calculates the square of a number you give it.",
        "def square(number): return number ** 2",
        "print(square(5))",
        "Output: 25",
        "Each text can be up to 8192 tokens long",
    ]
)

print(len(code_embeddings[0]))
'''
===============================================================================
768
===============================================================================
'''

# Set the clip embedding instance
jina_clip_embed = JinaEmbedding(
    model_type=EmbeddingModelType.JINA_CLIP_V2,
)

# Embed the text
text_embeddings = jina_clip_embed.embed_list(
    ["What is the capital of France?"]
)

# Set example image to embed
url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image_example = Image.open(requests.get(url, stream=True).raw)

# Embed the image
image_embeddings = jina_clip_embed.embed_list([image_example])

print(len(text_embeddings[0]))
'''
===============================================================================
1024
===============================================================================
'''

print(len(image_embeddings[0]))

'''
===============================================================================
1024
===============================================================================
'''
