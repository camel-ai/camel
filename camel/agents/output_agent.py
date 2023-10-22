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
from io import BytesIO

import tiktoken

from camel.configs import ChatGPTConfig
from camel.functions.data_io_functions import HtmlFile
from camel.models.openai_model import OpenAIModel
from camel.typing import ModelType

with open("examples/multi_agent/multi-agent-output-Supply Chain-en.html",
          "rb") as f:
    file = BytesIO(f.read())
    file.name = "test.html"
    html_file = HtmlFile.from_bytes(file)

normal_string = html_file.docs[0]['page_content']

num_tokens = len(tiktoken.get_encoding("cl100k_base").encode(normal_string))
print(num_tokens)

# Create an instance of the OpenAI model
my_openai_model = OpenAIModel(model_type=ModelType.GPT_3_5_TURBO_16K,
                              model_config_dict=ChatGPTConfig().__dict__)

# Create a task prompt based on the content
messages_task_prompt = [
    {
        "role":
        "system",
        "content":
        '''You are a helpful assistant to re-organize information
        into a detailed instruction,
        below is the content for you:''' + '\n' + normal_string
    },
    {
        "role":
        "user",
        "content":
        '''Please extract the detailed action information
        from the provided content,
        make it useful for a human can follow the detailed
        instruction step by step to solve the task.'''
    },
]

# Get a response for the task prompt
response_task_prompt = my_openai_model.run(
    messages=messages_task_prompt)['choices'][0]
content_task_prompt = response_task_prompt['message']['content']
print(content_task_prompt)
