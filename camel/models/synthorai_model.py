# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
from typing import Any

from camel.configs import SynthoraiConfig
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ModelType
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)


class SynthoraiModel(OpenAICompatibleModel):
    r"""LLM API served by Synthorai in a unified OpenAICompatibleModel
    interface.

    Synthorai is an OpenAI-compatible LLM gateway that routes requests to
    models from several upstream providers behind a single base URL and key.

    Model ids carry no vendor prefix — they are flat names such as
    ``claude-opus-5`` or ``glm-5.2``. Pass one of the predefined
    ``ModelType.SYNTHORAI_*`` enums, or any id from the catalog at
    https://synthorai.io/models/ as a free-form string.

    Note that ``/v1/models`` returns the models a given key is permitted to
    use, which is narrower than the full catalog, so what a key can reach
    depends on the key rather than on the catalog alone.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`.
            If:obj:`None`, :obj:`SynthoraiConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the Synthorai service. (default: :obj:`None`).
        url (Optional[str], optional): The url to the Synthorai service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required([("api_key", "SYNTHORAI_API_KEY")])
    def __init__(
        self,
        model_type: ModelType | str,
        model_config_dict: dict[str, Any] | None = None,
        api_key: str | None = None,
        url: str | None = None,
        token_counter: BaseTokenCounter | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = SynthoraiConfig().as_dict()
        api_key = api_key or os.environ.get("SYNTHORAI_API_KEY")
        url = url or os.environ.get(
            "SYNTHORAI_API_BASE_URL", "https://synthorai.io/v1"
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", "180"))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
