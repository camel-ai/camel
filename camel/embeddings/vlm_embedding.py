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


class VisionLanguageEmbedding(BaseEmbedding[Union[str, Image.Image]]):
    r"""Provides image embedding functionalities using multimodal model.

    Args:
        model_name : The model type to be used for generating embeddings.
            And the default value is: obj:`openai/clip-vit-base-patch32`.

    Raises:
        RuntimeError: If an unsupported model type is specified.
    """

    def __init__(self,
                 model_name: str = "openai/clip-vit-base-patch32") -> None:
        r"""Initializes the: obj: `VisionLanguageEmbedding` class
                                    with a specified model
                                    and return the dimension of embeddings.

        Args:
            model_name (str, optional): The version name of the model to use.
            (default: :obj:`openai/clip-vit-base-patch32`)
        """
        from transformers import AutoModel, AutoProcessor
        self.model = AutoModel.from_pretrained(model_name)
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.dim = None

    def embed_list(
        self,
        objs: List[Union[Image.Image, str]],
        **kwargs: Any,
    ) -> List[List[float]]:
        r"""Generates embeddings for the given images or texts.

        Args:
            objs (List[Image.Image|str]): The list of images or texts for
                which to generate the embeddings.
            **kwargs (Any): Extra kwargs passed to the embedding API.

        Returns:
            List[List[float]]: A list that represents the generated embedding
                as a list of floating-point numbers.
        """
        if not objs:
            raise ValueError("Input objs list is empty.")
        result_list = []
        for obj in objs:
            if isinstance(obj, Image.Image):
                input = self.processor(images=obj, return_tensors="pt",
                                       padding=True, **kwargs)
                image_feature = self.model.get_image_features(
                    **input, **kwargs).tolist()
                result_list.extend(image_feature)
            elif isinstance(obj, str):
                input = self.processor(text=obj, return_tensors="pt",
                                       padding=True)
                text_feature = self.model.get_text_features(**input).tolist()
                result_list.extend(text_feature)

            else:
                raise ValueError("Input type is not image nor text.")
        self.dim = result_list[0].shape[1]
        return result_list

    def get_output_dim(self):
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        text = 'dimension'
        inputs = self.processor(text=[text], return_tensors="pt")
        self.dim = self.model.get_text_features(**inputs).shape[1]
        return self.dim
