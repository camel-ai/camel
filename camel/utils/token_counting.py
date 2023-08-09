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
import tiktoken
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from transformers import AutoTokenizer

from camel.messages import OpenAIMessage
from camel.typing import ModelType


OPENAI_MODEL_VALUES = {
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k-0613",
    "gpt-4-0314",
    "gpt-4-32k-0314",
    "gpt-4-0613",
    "gpt-4-32k-0613",
}

# register_conv_template(
#     Conversation(
#         name="llama-2",
#         system_template="[INST] <<SYS>>\n{system_message}\n<</SYS>>\n\n",
#         roles=("[INST]", "[/INST]"),
#         messages=(),
#         offset=0,
#         sep_style=SeparatorStyle.LLAMA2,
#         sep=" ",
#         sep2=" </s><s>",
#         stop_token_ids=[2],
#     )
# )
# reference: https://github.com/facebookresearch/llama/blob/cfc3fc8c1968d390eb830e65c63865e980873a06/llama/generation.py#L212
def messages_to_prompt(messages: List[OpenAIMessage], model: ModelType) -> str:
    system_message = messages[0]["content"]

    if model == ModelType.LLAMA_2:
        seps = [" ", " </s><s>"]
        ret = ""
        role_map = {"user": "[INST]", "assistant": "[/INST]"}
        system_prompt = f"[INST] <<SYS>>\n{system_message}\n<</SYS>>\n\n"
        for i, msg in enumerate(messages[1:]):
            role = role_map[msg["role"]]
            message = msg["content"]
            if message:
                if i == 0:
                    ret += system_prompt + message
                else:
                    ret += role + " " + message + seps[i % 2]
            else:
                ret += role
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
    try:
        encoding = tiktoken.encoding_for_model(value_for_tiktoken)
    except KeyError:
        print("Model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return encoding


class BaseTokenCounter(ABC):
    @abstractmethod
    def count_tokens_from_messages(
        self, 
        messages: List[OpenAIMessage]
    ) -> int:
        pass

class OpenSourceTokenCounter(BaseTokenCounter):
    def __init__(self, model: ModelType, model_path: str):
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

        self.tokenizer = tokenizer
        self.model_type = model

    def count_tokens_from_messages(
        self, 
        messages: List[OpenAIMessage]
    ) -> int:
        prompt = messages_to_prompt(messages, self.model_type)
        input_ids = self.tokenizer(prompt).input_ids

        return len(input_ids)

class OpenAITokenCounter(BaseTokenCounter):
    def __init__(self, model: ModelType):
        self.model: str = model.value_for_tiktoken

        self.tokens_per_message: int
        self.tokens_per_name: int
        if (self.model in OPENAI_MODEL_VALUES) or \
              ("gpt-3.5-turbo" in self.model) or \
              ("gpt-4" in self.model):
            self.tokens_per_message = 3
            self.tokens_per_name = 1
        elif self.model == "gpt-3.5-turbo-0301":
            # Every message follows <|start|>{role/name}\n{content}<|end|>\n
            self.tokens_per_message = 4
            # If there's a name, the role is omitted
            self.tokens_per_name = -1
        else:
            raise NotImplementedError(
                "Token counting for OpenAI Models is not presently "
                f"implemented for model {model}. "
                "See https://github.com/openai/openai-python/blob/main/chatml.md "
                "for information on how messages are converted to tokens. "
                "See https://platform.openai.com/docs/models/gpt-4"
                "or https://platform.openai.com/docs/models/gpt-3-5"
                "for information about openai chat models.")

        self.encoding = get_model_encoding(self.model)
    
    def count_tokens_from_messages(
        self, 
        messages: List[OpenAIMessage]
    ) -> int:
        num_tokens = 0
        for message in messages:
            num_tokens += self.tokens_per_message
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(str(value)))
                if key == "name":
                    num_tokens += self.tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens



class TokenCounterFactory:
    r"""Factory of backend models.

    Raises:
        ValueError: in case the provided model type is unknown.
    """

    @staticmethod
    def create(model_type: ModelType, kwargs: Dict[str, Any]) -> BaseTokenCounter:
        r"""Creates an instance of `BaseModelBackend` of the specified type.

        Args:
            model_type (ModelType): Model for which a backend is created.
            kwargs (Dict[str, Any]): a dictionary containing additional
                information, such as the path to the tokenizer

        Raises:
            ValueError: If there is not backend for the model.

        Returns:
            BaseModelBackend: The initialized backend.
        """
        if model_type in {
                ModelType.GPT_3_5_TURBO,
                ModelType.GPT_3_5_TURBO_16K,
                ModelType.GPT_4,
                ModelType.GPT_4_32k,
                ModelType.STUB,
        }:
            return OpenAITokenCounter(model_type)
        elif model_type in {
            ModelType.LLAMA_2
        }:
            return OpenSourceTokenCounter(model_type, **kwargs)
        else:
            raise ValueError("Unknown model")