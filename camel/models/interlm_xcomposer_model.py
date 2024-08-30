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
from typing import Any, Dict, List, Optional, Union

from openai import Stream

from camel.configs import INTERNLM_API_PARAMS

from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    Choice,
    CompletionUsage,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
)


class InternLMXComposerModel:
    r"""Class for interace with OpenAI-API-compatible servers running
    open-source InternLM-XComposer models.
    """

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
        self.model_config_dict = model_config_dict

        if self.model_config_dict["operation_mode"] not in {"chat", "write_webpage", "resume_2_webpage", "write_article"}:
            raise ValueError("Please check the operation_mode value in model_config_dict!")
            
        self.model_type = model_type

        # try:
        #     # `operation_mode` is the operation mode of the open-source model
        #     # Refer to https://github.com/InternLM/InternLM-XComposer
        #     self.operation_mode = model_config_dict.get(
        #         "operation_mode", OperationMode.CHAT
        #     )
        # except ValueError:
        #     valid_modes = [mode.value for mode in OperationMode]
        #     raise ValueError(
        #         "Invalid operation mode for open-source model "
        #         f"backend. Choose from {valid_modes}"
        #     )

        import torch

        model_kwargs = self.model_config_dict.get("model_kwargs", {})
        # model_kwargs["torch_dtype"] = torch.bfloat16
        # model_kwargs["trust_remote_code"] = True

        from transformers import AutoModel, AutoTokenizer

        self._client = (
            AutoModel.from_pretrained(
                self.model_name,
                **model_kwargs,
            )
            .to(
                # model_kwargs.get("device") or 
                "cuda"
                # if torch.cuda.is_available()
                # else "cpu"
            )  # move the model to the specified device (GPU or CPU)
            .eval()  # set the model to evaluation mode
            .half()  # convert the model parameters to half-precision floating point (FP16).  # noqa: E501
        )

        tokenizer_kwargs = self.model_config_dict.get("tokenizer_kwargs", {})
        # tokenizer_kwargs["trust_remote_code"] = True

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, **tokenizer_kwargs
        )
        self._client.tokenizer = self._tokenizer  # mypy: ignore[attr-defined]

        # Replace `model_config_dict` with only the `model_kwargs`
        self.model_config_dict = self.model_config_dict["model_kwargs"]

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
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
        last_message = messages[-1]

        if isinstance(last_message["content"], str):
            # If the message does not contain image nor video:
            message_content = last_message["content"]
        elif isinstance(last_message["content"], list):
            # If the message contains image or video:

            import base64
            import shutil

            n_image = 0  # number of images
            n_video = 0  # number of videos
            image = []  # list of images local path

            # # Check and clean the images folder
            # if self.multimodal_src_directory.exists():
            #     shutil.rmtree(self.multimodal_src_directory)
            # self.multimodal_src_directory.mkdir(parents=True, exist_ok=True)

            # Get `message_content`
            for item in last_message["content"]:
                if item["type"] == "text":
                    message_content = item["text"]
                elif item["type"] == "image_url":
                    # Get `image` list

                    n_image += 1
                    base64_string = item['image_url']['url'].split(',')[1]

                    # Convert the base64 string into images
                    # and save them as the local files.
                    image_data = base64.b64decode(base64_string)
                    # image_file_path = (
                    #     self.multimodal_src_directory / f"image_{n_image}.jpg"
                    # )

                    # with open(image_file_path, 'wb') as file:
                    #     file.write(image_data)
                    image.append(str(image_file_path))
                elif item["type"] == "video_url":
                    # Get `video` list

                    n_video += 1
                    base64_string = item['video_url']['url'].split(',')[1]

                    # Convert the base64 string into video
                    # and save them as the local files.
                    video_data = base64.b64decode(base64_string)
                    # video_file_path = (
                    #     self.multimodal_src_directory / f"video_{n_video}.mp4"
                    # )

                    # with open(video_file_path, 'wb') as file:
                    #     file.write(video_data)
                    image.append(str(video_file_path))

        else:
            message_content = ""
            image = []

        import torch

        torch.set_grad_enabled(False)

        with torch.autocast(device_type='cuda', dtype=torch.float16):
            if self.operation_mode == OperationMode.CHAT:
                response_str, _ = (  # output param `his` is ignored
                    self._client.chat(
                        self._tokenizer,
                        message_content,
                        image,
                        do_sample=False,
                        num_beams=3,
                        use_meta=True,
                    )
                )
            elif self.operation_mode == OperationMode.WRITE_WEBPAGE:
                response_str, _ = (  # output param `his` is ignored
                    self._client.write_webpage(
                        message_content,
                        image,
                        seed=202,
                        task="Instruction-aware webpage generation",
                        repetition_penalty=3.0,
                    )
                )
            elif self.operation_mode == OperationMode.RESUME_TO_WEBPAGE:
                response_str, _ = (  # output param `his` is ignored
                    self._client.resume_to_webpage(
                        message_content,
                        image,
                        seed=202,
                        repetition_penalty=3.0,
                    )
                )
            elif self.operation_mode == OperationMode.WRITE_ARTICLE:
                response_str, _ = (  # output param `his` is ignored
                    self._client.write_article(
                        message_content,
                        seed=8192,
                    )
                )

        # Adapt to OpenAI's response format.
        response = ChatCompletion.construct(
            id="interlm-xcomposer-output-id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    logprobs=None,
                    message=ChatCompletionMessage(
                        content=response_str,
                        role="assistant",
                        function_call=None,
                        tool_calls=None,
                    ),
                ),
            ],
            created=0,
            model=self.model_name,
            object="chat.completion",
            service_tier=None,
            system_fingerprint="fp_interlm_xcomposer_system_fingerprint",
            usage=CompletionUsage(
                completion_tokens=0,
                prompt_tokens=0,
                total_tokens=0,
            ),
        )

        return response

    # def check_model_config(self):
    #     r"""Check whether the model configuration is valid for open-source
    #     model backends.

    #     Raises:
    #         ValueError: If the model configuration dictionary contains any
    #             unexpected arguments to OpenAI API, or it does not contain
    #             :obj:`model_path`.
    #     """
    #     if self.model_type == "internlm-xcomposer2d5-7b":
    #         for param in self.model_config_dict:
    #             if param not in INTERNLM_API_PARAMS:
    #                 raise ValueError(
    #                     f"Unexpected argument `{param}` is "
    #                     "input into ImtermLM model backend."
    #                 )

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