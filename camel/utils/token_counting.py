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
from abc import ABC, abstractmethod
from typing import List

from camel.messages import OpenAIMessage
from camel.types import ModelType


def messages_to_prompt(messages: List[OpenAIMessage], model: ModelType) -> str:
    r"""Parse the message list into a single prompt following model-specifc
    formats.

    Args:
        messages (List[OpenAIMessage]): Message list with the chat history
            in OpenAI API format.
        model (ModelType): Model type for which messages will be parsed.

    Returns:
        str: A single prompt summarizing all the messages.
    """
    system_message = messages[0]["content"]

    ret: str
    if model == ModelType.LLAMA_2:
        # reference: https://github.com/facebookresearch/llama/blob/cfc3fc8c1968d390eb830e65c63865e980873a06/llama/generation.py#L212
        seps = [" ", " </s><s>"]
        role_map = {"user": "[INST]", "assistant": "[/INST]"}

        system_prompt = f"[INST] <<SYS>>\n{system_message}\n<</SYS>>\n\n"
        ret = ""
        for i, msg in enumerate(messages[1:]):
            role = role_map[msg["role"]]
            content = msg["content"]
            if content:
                if not isinstance(content, str):
                    raise ValueError("Currently multimodal context is not "
                                     "supported by the token counter.")
                if i == 0:
                    ret += system_prompt + content
                else:
                    ret += role + " " + content + seps[i % 2]
            else:
                ret += role
        return ret
    elif model == ModelType.VICUNA or model == ModelType.VICUNA_16K:
        seps = [" ", "</s>"]
        role_map = {"user": "USER", "assistant": "ASSISTANT"}

        system_prompt = f"{system_message}"
        ret = system_prompt + seps[0]
        for i, msg in enumerate(messages[1:]):
            role = role_map[msg["role"]]
            content = msg["content"]
            if not isinstance(content, str):
                raise ValueError("Currently multimodal context is not "
                                 "supported by the token counter.")
            if content:
                ret += role + ": " + content + seps[i % 2]
            else:
                ret += role + ":"
        return ret
    else:
        raise ValueError(f"Invalid model type: {model}")


def get_model_encoding(value_for_tiktoken: str):
    r"""Get model encoding from tiktoken.

    Args:
        value_for_tiktoken: Model value for tiktoken.

    Returns:
        tiktoken.Encoding: Model encoding.
    """
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(value_for_tiktoken)
    except KeyError:
        print("Model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return encoding


class BaseTokenCounter(ABC):
    r"""Base class for token counters of different kinds of models."""

    @abstractmethod
    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        pass


class OpenSourceTokenCounter(BaseTokenCounter):

    def __init__(self, model_type: ModelType, model_path: str):
        r"""Constructor for the token counter for open-source models.

        Args:
            model_type (ModelType): Model type for which tokens will be
                counted.
            model_path (str): The path to the model files, where the tokenizer
                model should be located.
        """

        # Use a fast Rust-based tokenizer if it is supported for a given model.
        # If a fast tokenizer is not available for a given model,
        # a normal Python-based tokenizer is returned instead.
        from transformers import AutoTokenizer
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                use_fast=True,
            )
        except TypeError:
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                use_fast=False,
            )
        except:
            raise ValueError(
                f"Invalid `model_path` ({model_path}) is provided. "
                "Tokenizer loading failed.")

        self.tokenizer = tokenizer
        self.model_type = model_type

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list using
        loaded tokenizer specific for this type of model.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        prompt = messages_to_prompt(messages, self.model_type)
        input_ids = self.tokenizer(prompt).input_ids

        return len(input_ids)


class OpenAITokenCounter(BaseTokenCounter):

    def __init__(self, model: ModelType):
        r"""Constructor for the token counter for OpenAI models.

        Args:
            model_type (ModelType): Model type for which tokens will be
                counted.
        """
        self.model: str = model.value_for_tiktoken

        self.tokens_per_message: int
        self.tokens_per_name: int

        if self.model == "gpt-3.5-turbo-0301":
            # Every message follows <|start|>{role/name}\n{content}<|end|>\n
            self.tokens_per_message = 4
            # If there's a name, the role is omitted
            self.tokens_per_name = -1
        elif ("gpt-3.5-turbo" in self.model) or ("gpt-4" in self.model):
            self.tokens_per_message = 3
            self.tokens_per_name = 1
        else:
            # flake8: noqa :E501
            raise NotImplementedError(
                "Token counting for OpenAI Models is not presently "
                f"implemented for model {model}. "
                "See https://github.com/openai/openai-python/blob/main/chatml.md "
                "for information on how messages are converted to tokens. "
                "See https://platform.openai.com/docs/models/gpt-4"
                "or https://platform.openai.com/docs/models/gpt-3-5"
                "for information about openai chat models.")

        self.encoding = get_model_encoding(self.model)

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        r"""Count number of tokens in the provided message list with the
        help of package tiktoken.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            int: Number of tokens in the messages.
        """
        num_tokens = 0
        for message in messages:
            num_tokens += self.tokens_per_message
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(str(value)))
                if key == "name":
                    num_tokens += self.tokens_per_name

        # every reply is primed with <|start|>assistant<|message|>
        num_tokens += 3
        return num_tokens
