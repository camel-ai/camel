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
from typing import Any, Dict, List, Tuple, Union

from openai import Stream

from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    Choice,
)
from camel.utils import BaseTokenCounter, HuggingFaceMultimodalTokenCounter


class HuggingFaceModel:
    r"""Class for interfacing with Hugging Face servers running open-source
    models."""

    def __init__(
        self,
        model_type: str,
        model_config_dict: Dict[str, Any],
    ) -> None:
        r"""Constructor for model backends of Open-source models.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into :obj:`openai.ChatCompletion.create()`.
        """
        from transformers import AutoModel, AutoTokenizer

        self.model_type = model_type
        self.model_config_dict = model_config_dict

        # Check the model type and operation mode for InternLM-XComposer
        if not model_type.lower().startswith("internlm-xcomposer"):
            # `operation_mode` is the operation mode of the open-source model
            # Refer to https://github.com/InternLM/InternLM-XComposer
            if self.model_config_dict["operation_mode"] not in {
                "chat",
                "write_webpage",
                "resume_2_webpage",
                "write_article",
            }:
                raise ValueError(
                    "Invalid operation mode of InternLM-XComposer, please "
                    "check the operation_mode value in model_config_dict."
                )

        self.model_kwargs = self.model_config_dict.get("model_kwargs", {})
        self._client = AutoModel.from_pretrained(
            self.model_type,
            **self.model_kwargs,
        )

        self.tokenizer_kwargs = self.model_config_dict.get(
            "tokenizer_kwargs", {}
        )
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_type, **self.tokenizer_kwargs
        )

        self._client.tokenizer = self._tokenizer  # mypy: ignore[attr-defined]
        self._token_counter = HuggingFaceMultimodalTokenCounter(
            model_type=model_type
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        return self._token_counter

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI-API-style chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """

        # Extract the text content from List[OpenAIMessage].
        historical_message = ""
        for message in messages[:-1]:
            if message["role"] == "system":
                historical_message += f"System: {message['content']}\n"
            elif message["role"] == "user":
                historical_message += f"Human: {message['content']}\n"
            elif message["role"] == "assistant":
                historical_message += f"Assistant: {message['content']}\n"
        historical_message += "Assistant: "

        last_message = messages[-1]
        image = []

        if isinstance(last_message["content"], str):
            # If the message does not contain image nor video:
            message_content = last_message["content"]
        elif isinstance(last_message["content"], list):
            # If the message contains image or video:

            # Convert OpenAI message to InternLM-XComposer message.
            message_content, image_paths, video_paths = (
                self._to_multi_modal_message(messages)
            )
            for image_path in image_paths:
                image.append(image_path)
            for video_path in video_paths:
                image.append(video_path)

        if self.model_type.lower().startswith("internlm-xcomposer"):
            import torch

            torch.set_grad_enabled(False)

            operation_mode = self.model_config_dict.get(
                "operation_mode", "chat"
            )
            with torch.autocast(device_type='cuda', dtype=torch.float16):
                if operation_mode == "chat":
                    response_str, _ = (  # output param `his` is ignored
                        self._client.chat(
                            self._tokenizer,
                            historical_message + message_content,
                            image,
                            **self.model_kwargs,
                        )
                    )
                elif operation_mode == "write_webpage":
                    response_str, _ = (  # output param `his` is ignored
                        self._client.write_webpage(
                            historical_message + message_content,
                            image,
                            task="Instruction-aware webpage generation",
                            **self.model_kwargs,
                        )
                    )
                elif operation_mode == "resume_2_webpage":
                    response_str, _ = (  # output param `his` is ignored
                        self._client.resume_to_webpage(
                            historical_message + message_content,
                            image,
                            **self.model_kwargs,
                        )
                    )
                elif operation_mode == "write_article":
                    response_str, _ = (  # output param `his` is ignored
                        self._client.write_article(
                            message_content,
                            image,
                            **self.model_kwargs,
                        )
                    )
        else:
            # Other huggingface models
            response_str = self._client.generate(
                historical_message + message_content,
                **self.model_kwargs,
            )

        # Adapt to OpenAI's response format.
        response = self._to_openai_message(response_str)

        return response

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)

    @property
    def token_limit(self) -> int:
        """Returns the maximum token limit for the given model.

        Returns:
            int: The maximum token limit for the given model.
        """
        max_tokens = self.model_config_dict.get("max_tokens")
        if isinstance(max_tokens, int):
            return max_tokens
        print(
            "Must set `max_tokens` as an integer in `model_config_dict` when"
            " setting up the model. Using 4096 as default value."
        )
        return 4096

    def _to_openai_message(self, message_str: str) -> ChatCompletion:
        r"""Converts InternLM-XComposer message to OpenAI message.

        Args:
            message_str (str): The content of the message.

        Returns:
            ChatCompletion: The message in OpenAI format.
        """
        obj = ChatCompletion.construct(
            id="interlm-xcomposer-output-id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    logprobs=None,
                    message=ChatCompletionMessage(
                        content=message_str,
                        role="assistant",
                        function_call=None,
                        tool_calls=None,
                    ),
                ),
            ],
            created=0,
            model=self.model_type,
            object="chat.completion",
            service_tier=None,
            system_fingerprint="fp_interlm_xcomposer_system_fingerprint",
            usage=None,
        )

        return obj

    def _to_multi_modal_message(
        self,
        messages: List[OpenAIMessage],
    ) -> Tuple[str, List[str], List[str]]:
        r"""Converts OpenAI message to InternLM-XComposer message.

        Args:
            messages (List[OpenAIMessage]): List of OpenAI messages.

        Returns:
            Tuple[str, List[str], List[str]]:
                - message_content (str): The content of the message.
                - image_paths (List[str]): The paths of the images.
                - video_paths (List[str]): The paths of the videos.
        """
        import base64
        import tempfile

        historical_message = ""

        # Extract the text content from the last message with image or video.
        last_message = messages[-1]
        message_content = ""
        image_paths = []
        video_paths = []

        if isinstance(last_message["content"], str):
            message_content = last_message["content"]
        elif isinstance(last_message["content"], list):
            n_image = 0  # number of images
            n_video = 0  # number of videos

            for item in last_message["content"]:
                if item["type"] == "text":
                    message_content = item["text"]
                elif item["type"] == "image_url":
                    n_image += 1
                    base64_string = item['image_url']['url'].split(',')[1]

                    # Create a temporary file for the image
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".jpg", mode='wb'
                    ) as tmpfile:
                        image_data = base64.b64decode(base64_string)
                        tmpfile.write(image_data)
                        image_paths.append(tmpfile.name)
                elif item["type"] == "video_url":
                    n_video += 1
                    base64_string = item['video_url']['url'].split(',')[1]

                    # Create a temporary file for the video
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".mp4", mode='wb'
                    ) as tmpfile:
                        video_data = base64.b64decode(base64_string)
                        tmpfile.write(video_data)
                        video_paths.append(tmpfile.name)

        return message_content, image_paths, video_paths
