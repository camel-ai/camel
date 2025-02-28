# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========


from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

r"""
Before using sglang to run LLM model offline,
you need to install flashinfer which cannot 
be installed by poetry.
Consider your machine's configuration and 
install flashinfer in a appropriate version.
For more details, please refer to:
https://sgl-project.github.io/start/install.html
https://docs.flashinfer.ai/installation.html

Please load HF_token in your environment variable.
export HF_TOKEN=""
When using the OpenAI interface to run SGLang model server, 
the base model may fail to recognize  huggingface default
chat template, switching to the Instruct model resolves the issue.
"""
load_dotenv()
sglang_model = ModelFactory.create(
    model_platform=ModelPlatformType.SGLANG,
    model_type="meta-llama/Llama-3.2-1B-Instruct",
    model_config_dict={"temperature": 0.0},
    api_key="sglang",
)
assistant_sys_msg = "You are a helpful assistant."

agent = ChatAgent(assistant_sys_msg, model=sglang_model, token_limit=4096)

user_msg = "Say hi to CAMEL AI"

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
CAMEL AI ReferentialAction
===============================================================================
"""

weather_tool = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["city"],
            },
        },
    }
]

sglang_model_with_tool = ModelFactory.create(
    model_platform=ModelPlatformType.SGLANG,
    model_type="meta-llama/Llama-3.2-1B-Instruct",
    model_config_dict={"temperature": 0.0, "tools": weather_tool},
    api_key="sglang",
)

agent = ChatAgent(
    assistant_sys_msg, model=sglang_model_with_tool, token_limit=4096
)

user_msg = "What's the weather in Boston today?"

assistant_response = agent.step(user_msg)
if assistant_response.msg.tool_calls:
    tool_call = assistant_response.msg.tool_calls[0]
    print(f"Detected tool call: {tool_call['name']}")
    print(f"Arguments: {tool_call['arguments']}")
