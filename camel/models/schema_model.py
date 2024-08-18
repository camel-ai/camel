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
import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from openai import Stream
from pydantic import BaseModel, ValidationError

from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    Choice,
    ModelPlatformType,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
)

T = TypeVar('T', bound=BaseModel)


class SchemaModel(BaseModelBackend):
    r"""Shema model in a unified BaseModelBackend interface, which aims to
    generate the formatted response."""

    def __init__(
        self,
        model_platform: ModelPlatformType,
        model_type: str,
        model_config_dict: Dict[str, Any],
        url: Optional[str] = None,
    ) -> None:
        r"""Constructor for open-source backend.

        Args:
            model_platform (ModelPlatformType): Platform from which the model
                originates, including transformers, llama_cpp, and vllm.
            model_type (str): Model for which a backend is created, for
                example, "mistralai/Mistral-7B-v0.3".
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
            url (Optional[str]): The url to the OpenAI service.
        """
        from outlines import models  # type: ignore[import]

        self.model_platform = model_platform
        self.model_name = model_type
        self.model_config_dict = model_config_dict
        self._client: Union[models.Transformers, models.LlamaCpp, models.VLLM]
        self._url = url

        # Since Outlines suports multiple model types, it is necessary to
        # read the documentation to learn about the model kwargs:
        # https://outlines-dev.github.io/outlines/reference/models/transformers
        if self.model_platform == ModelPlatformType.OUTLINES_TRANSFORMERS:
            model_kwargs = self.model_config_dict.get("model_kwargs", {})
            device = self.model_config_dict.get("device", None)
            tokenizer_kwargs = self.model_config_dict.get(
                "tokenizer_kwargs", {}
            )

            self._client = models.transformers(
                model_name=self.model_name,
                device=device,
                model_kwargs=model_kwargs,
                tokenizer_kwargs=tokenizer_kwargs,
            )
        elif self.model_platform == ModelPlatformType.OUTLINES_LLAMACPP:
            repo_id = self.model_config_dict.get(
                "repo_id", "TheBloke/phi-2-GGUF"
            )
            filename = self.model_config_dict.get(
                "filename", "phi-2.Q4_K_M.gguf"
            )
            download_dir = self.model_config_dict.get("download_dir", None)
            model_kwargs = self.model_config_dict.get("model_kwargs", {})

            from llama_cpp import llama_tokenizer  # type: ignore[import]

            # Initialize the tokenizer
            tokenizer = llama_tokenizer.LlamaHFTokenizer.from_pretrained(
                repo_id
            )  # type: ignore[attr-defined]

            self._client = models.llamacpp(  # type: ignore[attr-defined]
                repo_id=repo_id,
                filename=filename,
                download_dir=download_dir,
                tokenizer=tokenizer,
                **model_kwargs,
            )
        elif self.model_platform == ModelPlatformType.OUTLINES_VLLM:
            model_kwargs = self.model_config_dict.get("model_kwargs", {})

            self._client = models.vllm(
                model_name=self.model_name,
                **model_kwargs,
            )
        else:
            raise ValueError(
                f"Unsupported model by Outlines: {self.model_name}"
            )

        self._token_counter: Optional[BaseTokenCounter] = None

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            # The default model type is GPT_3_5_TURBO, since the self-hosted
            # models are not supported in the token counter.
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
        return self._token_counter

    @overload
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]: ...

    @overload
    def run(
        self,
        messages: List[OpenAIMessage],
        output_schema: Type[T],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]: ...

    def run(
        self,
        messages: List[OpenAIMessage],
        output_schema: Optional[Type[T]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        if output_schema is None:
            raise NotImplementedError(
                "run without output_schema is not implemented"
            )

        from outlines import generate  # type: ignore[import]

        generator = generate.json(self._client, output_schema)

        if not messages:
            raise ValueError("The messages list should not be empty.")
        message = messages[-1]
        message_str = (
            f"{message.get('role', '')}: {message.get('content', '')}"
        )

        parsed_response = generator(message_str)
        json_response = json.dumps(str(parsed_response))

        # Verify the structured format
        try:
            _ = output_schema(**json.loads(json_response))
        except ValidationError as e:
            raise ValueError(
                f"Generated response does not match the output schema: {e}"
            )

        import time

        response = ChatCompletion(
            id=f"chatcmpl-{time.time()}",
            created=int(time.time()),
            model=self.model_name,
            object="chat.completion",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=json_response,
                    ),
                    finish_reason="stop",
                ),
            ],
        )

        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains the required
        arguments for the schema-based model.

        Raises:
            Warning: If the model configuration dictionary does not contain
                the required arguments for the schema-based model, the warnings
                are raised.
        """
        # Check the model_name, WarningError if not found
        if "model_name" not in self.model_config_dict:
            raise Warning("The model_name is set to the default value.")

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
