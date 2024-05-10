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

from camel.models.anthropic_model import AnthropicModel
from camel.models.base_model import BaseModelBackend
from camel.models.open_source_model import OpenSourceModel
from camel.models.openai_model import OpenAIModel
from camel.models.stub_model import StubModel
from camel.types import ModelType


class ModelFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    @staticmethod
    def create(
        model_type: ModelType,
        model_config_dict: Dict,
        api_key: Optional[str] = None,
    ) -> BaseModelBackend:
        r"""Creates an instance of `BaseModelBackend` of the specified type.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict): A dictionary that will be fed into
                the backend constructor.
            api_key (Optional[str]): The API key for authenticating with the
                LLM service.

        Raises:
            ValueError: If there is not backend for the model.

        Returns:
            BaseModelBackend: The initialized backend.
        """
        model_class: Any
        if model_type.is_openai:
            model_class = OpenAIModel
        elif model_type == ModelType.STUB:
            model_class = StubModel
        elif model_type.is_open_source:
            model_class = OpenSourceModel
        elif model_type.is_anthropic:
            model_class = AnthropicModel
        else:
            raise ValueError(f"Unknown model type `{model_type}` is input")

        inst = model_class(model_type, model_config_dict, api_key)
        return inst
