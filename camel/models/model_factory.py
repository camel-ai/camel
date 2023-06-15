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
from typing import Any, Dict, Optional

from camel.typing import ModelType

from .base_model import BaseModel
from .openai_model import OpenAIModel
from .stub_model import StubModel


class ModelFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    @staticmethod
    def create(model_type: Optional[ModelType],
               model_config_dict: Dict) -> BaseModel:
        r"""Creates an instance of `BaseModel` of the specified type.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict): a dictionary that will be fed into
                the backend constructor.

        Raises:
            ValueError: If there is not backend for the model.

        Returns:
            BaseModel: The initialized backend.
        """
        default_model_type = ModelType.GPT_3_5_TURBO

        model_class: Any
        if model_type in {
                ModelType.GPT_3_5_TURBO, ModelType.GPT_4, ModelType.GPT_4_32k,
                None
        }:
            model_class = OpenAIModel
        elif model_type == ModelType.STUB:
            model_class = StubModel
        else:
            raise ValueError("Unknown model")

        if model_type is None:
            model_type = default_model_type

        inst = model_class(model_type, model_config_dict)
        return inst
