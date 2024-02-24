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
from typing import Any, List, Union

from PIL import Image

from camel.embeddings import BaseEmbedding


class CLIPEmbedding(BaseEmbedding):
    r"""Provides image embedding functionalities using CLIP model.

    Args:
        model_name : The model type to be used for
            generating embeddings.
            Default value is :obj:`openai/clip-vit-base-patch32`

    Raises:
        RuntimeError: If an unsupported model type is specified.
    """

    def __init__(self,
                 model_name: str = "openai/clip-vit-base-patch32") -> None:
        r"""Initializes the: obj: `CLIPEmbedding` class with a specified model

        Args:
            model_name (str, optional): The version name of the model to use.
                                        Default value is
                                        "openai/clip-vit-base-patch32"
        """

        from transformers import CLIPModel, CLIPProcessor
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def embed_list(
        self,
        objs: List[Union[Image.Image, str]],  # to do
        **kwargs: Any,
    ) -> List[List[float]]:
        r"""Generates embeddings for the given images or texts.

        Args:
            objs (List[Image.Image|str]): The list of images or texts
                                          for which to generate the embeddings.
            **kwargs (Any): Extra kwargs passed to the embedding API.

        Returns:
            List[List[float]]: A list that represents the generated embedding
                as a list of floating-point numbers.
        """
        if not objs:
            raise ValueError("Input text list is empty")
        if isinstance(objs[0], Image.Image):
            inputs = self.processor(images=objs, return_tensors="pt",
                                    padding=True)
            image_features = self.model.get_image_features(**inputs).tolist()
            return image_features
        elif isinstance(objs[0], str):
            inputs = self.processor(text=objs, return_tensors="pt",
                                    padding=True)
            text_features = self.model.get_text_features(**inputs).tolist()
            return text_features
        else:
            raise ValueError("Input type is not image nor text")

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """

        text = 'dimension'
        inputs = self.processor(text=[text])
        dim = self.model.get_text_features(**inputs).shape[1]
        return dim
