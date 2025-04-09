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
from .azure_embedding import AzureEmbedding
from .base import BaseEmbedding
from .jina_embedding import JinaEmbedding
from .mistral_embedding import MistralEmbedding
from .openai_compatible_embedding import OpenAICompatibleEmbedding
from .openai_embedding import OpenAIEmbedding
from .sentence_transformers_embeddings import SentenceTransformerEncoder
from .together_embedding import TogetherEmbedding
from .vlm_embedding import VisionLanguageEmbedding

__all__ = [
    "BaseEmbedding",
    "OpenAIEmbedding",
    "AzureEmbedding",
    "SentenceTransformerEncoder",
    "VisionLanguageEmbedding",
    "MistralEmbedding",
    "OpenAICompatibleEmbedding",
    "JinaEmbedding",
    "TogetherEmbedding",
]
