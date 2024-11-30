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

from camel.embeddings import VisionLanguageEmbedding

# Set the VLM instance
VLM_instance = VisionLanguageEmbedding(
    model_name="openai/clip-vit-base-patch32"
)

# Set example image to embed
url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image_example = Image.open(requests.get(url, stream=True).raw)

# Embed the image
image_embeddings = VLM_instance.embed_list([image_example])

# Set example text to embed
text_example = 'two cats laying on the sofa'

# Embed the text
text_embeddings = VLM_instance.embed_list([text_example])

# Get the length of 2 embeedings
print(len(image_embeddings[0]))
print(len(text_embeddings[0]))

'''
===============================================================================
512
512
===============================================================================
'''
