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
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    Choice,
    ModelType,
)
from camel.utils import BaseTokenCounter, OpenAITokenCounter


class SmolLMModel:
    r"""SmolLM service interface."""

    def __init__(
        self,
        model_type: str,
        model_config_dict: Dict[str, Any],
        quantization_config: Optional[BitsAndBytesConfig] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for SmolLM backend with HuggingFace model support.

        Args:
            model_type (str): Model checkpoint for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that contains model
                parameters like `max_length` for the model generation.
            quantization_config (Optional[BitsAndBytesConfig]): Config for model
                quantization, defaults to 8-bit quantization if not provided.
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_4O_MINI)` will be used.
        """
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self.quantization_config = quantization_config or BitsAndBytesConfig(
            load_in_8bit=True
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_type)

        # Device selection based on available hardware
        self.device = (
            "mps"
            if torch.backends.mps.is_available()
            else "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        if self.device != "cuda":
            self.quantization_config = None

        # Load model and move to selected device
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_type, quantization_config=self.quantization_config
        ).to(self.device)

        self._token_counter = token_counter or OpenAITokenCounter(
            ModelType.GPT_4O_MINI
        )

        # Check if model configuration has valid parameters
        self.check_model_config()

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to the SmolLM model.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments.
        """
        valid_params = [
            'max_new_tokens',
            'temperature',
            'top_p',
            'top_k',
            'do_sample',
        ]
        for param in self.model_config_dict:
            if param not in valid_params:
                raise ValueError(
                    f"Unexpected argument `{param}` in SmolLM model configuration."
                )

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, ChatCompletionChunk]:
        """Run inference using SmolLM with given messages."""
        input_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False
        )
        inputs = self.tokenizer.encode(input_text, return_tensors="pt").to(
            self.device
        )
        attention_mask = torch.ones(inputs.shape, device=self.device)

        outputs = self.model.generate(
            inputs, attention_mask=attention_mask, **self.model_config_dict
        )

        decoded_output = self.tokenizer.decode(
            outputs[0], skip_special_tokens=True
        )

        # Prepare ChatCompletion response
        chat_message = ChatCompletionMessage(
            role="assistant",
            content=decoded_output,
        )

        return ChatCompletion(
            id=str(uuid.uuid4()),
            model=self.model_type,
            created=int(time.time()),
            object="chat.completion",
            choices=[
                Choice(
                    message=chat_message,
                    index=0,
                    logprobs=None,
                    finish_reason="stop",
                )
            ],
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        """Return the token counter for the model."""
        return self._token_counter


def main():
    from camel.types import ChatCompletionUserMessageParam

    model_type = "HuggingFaceTB/SmolLM-360M-Instruct"  # Example model type
    model_config = {
        'max_new_tokens': 50,
        'temperature': 0.7,
        'top_p': 0.9,
        'top_k': 50,
        'do_sample': True,
    }

    # Instantiate the SmolLMModel class
    smol_model = SmolLMModel(
        model_type=model_type, model_config_dict=model_config
    )

    # Create a list of OpenAIMessage inputs (example message)
    messages = [
        ChatCompletionUserMessageParam(
            role="user", content="What is the capital of France?"
        )
    ]

    # Run the model
    response = smol_model.run(messages)

    # Output the response
    print(f"Model ID: {response.model}")
    print(f"Generated Text: {response.choices[0].message.content}")


if __name__ == '__main__':
    main()
