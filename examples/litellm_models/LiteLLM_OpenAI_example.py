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
from colorama import Fore

from camel.models.litellm_model import LiteLLMModel
from camel.types import ModelType
from camel.utils import print_text_animated


def main(model_type=None) -> None:
    # Define model type and configuration
    model_type = ModelType.GPT_3_5_TURBO
    model_config_dict = {
        "temperature": 0.7,
        "max_tokens": 150,
        "stream": False  # Set to True to enable stream mode
    }

    # Create an instance of LiteLLMModel
    model = LiteLLMModel(model_type, model_config_dict)

    # Define test messages
    messages = [{
        "content": "You are a helpful assistant.",
        "role": "system"
    }, {
        "content": "Can you explain how the LiteLLMModel works?",
        "role": "user"
    }]

    # Run the model
    response = model.run(messages)

    # Print the response
    print(response)
    print(model.token_counter.calculate_cost_from_response(response))

    output_messages = ""

    for choice in response.choices:
        chat_message = choice.message.content or ""
        output_messages += chat_message

    print(model.token_counter.count_tokens_from_messages(messages))

    messages.append({"content": output_messages, "role": "assistant"})

    print(model.token_counter.count_tokens_from_messages(messages))

    print_text_animated(Fore.GREEN + "AI Assistant:\n\n"
                        f"{output_messages}\n")


if __name__ == "__main__":
    main(model_type=ModelType.GPT_3_5_TURBO)
