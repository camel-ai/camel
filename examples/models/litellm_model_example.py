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
from camel.utils import print_text_animated

# Define model type and configuration
model_type = "gpt-3.5-turbo"
model_config_dict = {
    "temperature": 0.7,
    "max_tokens": 500,
    "stream": False,  # Set to True to enable stream mode
}

# Create an instance of LiteLLMModel
model = LiteLLMModel(model_type, model_config_dict)

# Define test messages
messages = [
    {"content": "You are a helpful assistant.", "role": "system"},
    {
        "content": "Can you explain what is the LiteLLMModel",
        "role": "user",
    },
]

# Run the model
response = model.run(messages)

# Print the response
print(response)

# Print the cost
cost = model.token_counter.calculate_cost_from_response(response)
print(f"The cost is ${cost}")

output_messages = ""

for choice in response.choices:
    chat_message = choice.message.content or ""
    output_messages += chat_message

print(model.token_counter.count_tokens_from_messages(messages))

messages.append({"content": output_messages, "role": "assistant"})

# Print the number of token consumed
token_consumed = model.token_counter.count_tokens_from_messages(messages)
print(f"The token consumed is {token_consumed}")

# Print the response
print_text_animated(Fore.GREEN + "AI Assistant:\n\n" f"{output_messages}\n")
"""
===============================================================================
ModelResponse(id='chatcmpl-9ZIkZBUVvRPU80osTkzoPxrLINB7S', choices=[Choices
(finish_reason='stop', index=0, message=Message(content='The `LiteLLMModel` is
a type of language model developed by OpenAI, specifically designed to be
lightweight and efficient for tasks such as text generation and natural
language processing. It is a smaller and simplified version of the larger GPT
(Generative Pre-trained Transformer) models, making it more accessible for
applications with limited computational resources. The LiteLLMModel is trained
on a large corpus of text data and can generate coherent and contextually
relevant text based on the input it receives. Its compact size makes it
suitable for deployment on devices with constraints on memory and processing
power.', role='assistant'))], created=1718200583, model='gpt-3.5-turbo-0125',
object='chat.completion', system_fingerprint=None, usage=Usage
(completion_tokens=116, prompt_tokens=27, total_tokens=143))
===============================================================================
"""

"""
===============================================================================
The cost is $0.0001875
===============================================================================
"""

"""
===============================================================================
The token consumed is 147
===============================================================================
"""

"""
===============================================================================
AI Assistant:

The `LiteLLMModel` is a type of language model developed by OpenAI,
specifically designed to be lightweight and efficient for tasks such as text
generation and natural language processing. It is a smaller and simplified
version of the larger GPT (Generative Pre-trained Transformer) models, making
it more accessible for applications with limited computational resources. The
LiteLLMModel is trained on a large corpus of text data and can generate
coherent and contextually relevant text based on the input it receives. Its
compact size makes it suitable for deployment on devices with constraints on
memory and processing power.
===============================================================================
"""
