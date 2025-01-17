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

from typing import Any, Dict, List, Optional, Union

from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import BaseTokenCounter, OpenAITokenCounter


class ModelScopeModel(BaseModelBackend):
    r"""LLM API served by ModelScope in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into AutoModelForCausalLM.from_pretrained().
            (default: :obj:`None`)
        api_key (Optional[str], optional): Not used for ModelScope.
            (default: :obj:`None`)
        url (Optional[str], optional): Not used for ModelScope.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        from modelscope import AutoModelForCausalLM, AutoTokenizer

        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._client = AutoModelForCausalLM.from_pretrained(
            model_type,
            torch_dtype="auto",
            device_map="auto",
            **(model_config_dict or {}),
        )
        self._tokenizer = AutoTokenizer.from_pretrained(model_type)

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        """Runs inference using ModelScope.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion: Response in ChatCompletion format.
        """
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self._tokenizer([text], return_tensors="pt").to(
            self._client.device
        )

        generated_ids = self._client.generate(
            **model_inputs, **(self.model_config_dict)
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(
                model_inputs.input_ids, generated_ids
            )
        ]

        response = self._tokenizer.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]

        return ChatCompletion(
            id="ms-" + str(hash(response))[:8],
            object="chat.completion",
            created=None,  # ModelScope doesn't provide creation time
            model=str(self._model_type),
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response,
                    },
                    "finish_reason": "stop",
                }
            ],
            usage={
                "prompt_tokens": None,  # ModelScope doesn't provide token counts
                "completion_tokens": None,
                "total_tokens": None,
            },
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def stream(self) -> bool:
        """Returns whether the model supports streaming.
        ModelScope currently doesn't support streaming.
        """
        return False

    def check_model_config(self) -> None:
        """Check whether the model configuration contains any unexpected
        arguments to ModelScope API.
        """
        pass  # No specific checks needed for ModelScope
