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
import base64
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from vllm.outputs import RequestOutput

from camel.configs import PHI_API_PARAMS, PHIConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType, UnifiedModelType
from camel.utils import OpenAITokenCounter


class PHIModel(BaseModelBackend):
    r"""PHI API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]):
        Model for which a backend is created.
        model_config_dict (Optional[Dict[str, Any]], optional):
        A dictionary that will be fed into the PHI model.
            If None, PHIConfig().as_dict() will be used. (default: None)
        api_key (Optional[str], optional):
        The API key for authenticating with the PHI service. (default: None)
        url (Optional[str], optional):
        The url to the PHI service. (default: None)
        token_counter (Optional[Any], optional):
        Token counter to use for the model. If not provided,
            OpenAITokenCounter will be used. (default: None)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[Any] = None,
    ) -> None:
        from vllm import LLM

        if model_config_dict is None:
            model_config_dict = PHIConfig().as_dict()
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
        )
        model_type_str = UnifiedModelType.__str__(model_type)
        self._client = LLM(
            model=model_type_str,
            device=model_config_dict["device"],
            trust_remote_code=model_config_dict["trust_remote_code"],
            max_model_len=model_config_dict["max_model_len"],
            limit_mm_per_prompt=model_config_dict["limit_mm_per_prompt"],
        )

    def _to_phi_format_chatmessage(
        self, messages: List[OpenAIMessage]
    ) -> Dict[str, Any]:
        r"""Preprocess messages to extract text and images.

        Args:
            messages (List[OpenAIMessage]): List of messages to preprocess.

        Returns:
            Dict[str, Any]: Preprocessed messages in PHI format.
        """
        new_messages = []
        image_urls = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                if isinstance(content, dict) and "image_url" in content:
                    image_urls.append(content["image_url"]["url"])
                else:
                    new_messages.append({"role": role, "content": content})
            elif role in ["system", "assistant"]:
                new_messages.append({"role": role, "content": content})
            else:
                raise ValueError(f"Unsupported message role: {role}")
        return new_messages  # type: ignore[return-value]

    def run(self, messages: List[OpenAIMessage]) -> ChatCompletion:
        r"""Run the PHI model with the given messages.

        Args:
            messages (List[OpenAIMessage]): List of messages to process.

        Returns:
            ChatCompletion: The response from the PHI model.
        """
        import io

        from vllm import SamplingParams

        sampling_params = SamplingParams(
            temperature=self.model_config_dict["temperature"],
            max_tokens=self.model_config_dict["max_tokens"],
            stop_token_ids=self.model_config_dict["stop_token_ids"],
        )
        preprocessed = self._to_phi_format_chatmessage(messages)

        question = "\n".join(
            msg["content"]  # type: ignore[index]
            if isinstance(msg["content"], str)  # type: ignore[index]
            else "\n".join(
                content["text"]  # type: ignore[index]
                for content in msg["content"]  # type: ignore[index]
                if content["type"] == "text"  # type: ignore[index]
            )
            for msg in preprocessed
            if msg["role"] == "user"  # type: ignore[index]
        )
        image_urls = [
            content["image_url"]["url"]  # type: ignore[index]
            for msg in preprocessed
            if isinstance(msg["content"], list)  # type: ignore[index]
            for content in msg["content"]  # type: ignore[index]
            if content["type"] == "image_url"  # type: ignore[index]
        ]

        if image_urls:
            image_data = []
            for img_base64 in image_urls:
                base64_data = img_base64.split(',')[1]
                image_bytes = base64.b64decode(base64_data)
                image_elem = Image.open(io.BytesIO(image_bytes))
                image_data.append(image_elem)
            if not image_data:
                raise ValueError("No valid images were downloaded.")
            placeholders = "\n".join(
                f"<|image_{i}|>" for i, _ in enumerate(image_urls, start=1)
            )
            prompt = (
                f"<|user|>\n"
                f"{question}\n"
                f"{placeholders}\n"
                f"<|end|>\n"
                f"<|assistant|>\n"
            )
            outputs = self._client.generate(
                {"prompt": prompt, "multi_modal_data": {"image": image_data}},
                sampling_params=sampling_params,
            )
        else:
            outputs = self._client.chat(
                messages=preprocessed,  # type: ignore[arg-type]
                sampling_params=sampling_params,
                use_tqdm=False,
            )
        return self._to_openai_format_response(outputs)

    def _to_openai_format_response(
        self, outputs: List[RequestOutput]
    ) -> ChatCompletion:
        r"""Convert vLLM outputs to OpenAI format.

        Args:
            outputs (List[RequestOutput]): List of vLLM outputs.

        Returns:
            ChatCompletion: The response in OpenAI format.
        """
        choices = []
        created_time = 0
        for output in outputs:
            created_time = output.metrics.arrival_time  # type: ignore[union-attr,assignment]
            message_content = output.outputs[0].text
            choice = {
                "index": 0,
                "message": {"role": "assistant", "content": message_content},
                "finish_reason": "stop",
            }
            choices.append(choice)

        return ChatCompletion(
            id="chat-completion-id",
            object="chat.completion",
            created=int(created_time),
            model=self.model_type,
            choices=choices,  # type: ignore[arg-type]
            usage={  # type: ignore[arg-type]
                "prompt_tokens": sum(
                    len(msg.outputs[0].text) for msg in outputs
                ),
                "completion_tokens": sum(
                    len(choice["message"]["content"].split())  # type: ignore[misc,index]
                    for choice in choices
                ),
                "total_tokens": sum(
                    len(msg.outputs[0].text) for msg in outputs
                )
                + sum(
                    len(choice["message"]["content"].split())  # type: ignore[misc,index]
                    for choice in choices
                ),
            },
        )

    @property
    def token_counter(self) -> OpenAITokenCounter:
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter  # type: ignore[return-value]

    def check_model_config(self):
        r"""Check whether the model configuration
        contains any unexpected arguments.
        """
        for param in self.model_config_dict:
            if param not in PHI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Phi model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False
