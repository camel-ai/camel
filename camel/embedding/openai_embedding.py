# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from enum import Enum
from typing import List

import openai

from camel.embedding.base import BaseEmbedding
from camel.utils import openai_api_key_required


class OpenAiEmbedding(BaseEmbedding):
    """
    """

    class ModelType(str, Enum):
        ADA2 = "text-embedding-ada-002"
        ADA1 = "text-embedding-ada-001"
        BABBAGE1 = "text-embedding-babbage-001"
        CURIE1 = "text-embedding-curie-001"
        DAVINCI1 = "text-embedding-davinci-001"

    def __init__(self, model: ModelType = ModelType.ADA2) -> None:
        self.model = model
        if self.model == self.ModelType.ADA2:
            self.output_dim = 1536
        elif self.model == self.ModelType.ADA1:
            self.output_dim = 1024
        elif self.model == self.ModelType.BABBAGE1:
            self.output_dim = 2048
        elif self.model == self.ModelType.CURIE1:
            self.output_dim = 4096
        elif self.model == self.ModelType.DAVINCI1:
            self.output_dim = 12288
        else:
            raise RuntimeError(f"Model type {model} not support")

    @openai_api_key_required
    def embed(self, text: str) -> List[float]:
        # TODO: count tokens
        response = openai.Embedding.create(input=text, model=self.model)
        return response['data'][0]['embedding']

    def get_output_dim(self) -> int:
        return self.output_dim
