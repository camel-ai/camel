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

r"""Before using sglang to run LLM model offline,
you need to install flashinfer.
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
Hello CAMEL AI. How can I assist you today?
===============================================================================
"""

weather_tool = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city to find the weather for,\n"
                        "e.g. 'San Francisco'",
                    },
                    "state": {
                        "type": "string",
                        "description": "The two-letter abbreviation for,\n"
                        "the state (e.g., 'CA'), e.g. CA for California",
                    },
                    "unit": {
                        "type": "string",
                        "description": "Temperature unit (celsius/fahrenheit)",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["city", "state", "unit"],
            },
        },
    }
]


r"""Note that api_key defines the parser used to interpret responses.
Currently supported parsers include:
llama3: Llama 3.1 / 3.2 (e.g. meta-llama/Llama-3.1-8B-Instruct,
        meta-llama/Llama-3.2-1B-Instruct).
mistral: Mistral (e.g. mistralai/Mistral-7B-Instruct-v0.3,
         mistralai/Mistral-Nemo-Instruct-2407, 
         mistralai/ Mistral-Nemo-Instruct-2407, mistralai/Mistral-7B-v0.3).
qwen25: Qwen 2.5 (e.g. Qwen/Qwen2.5-1.5B-Instruct, Qwen/Qwen2.5-7B-Instruct).
"""
sglang_model_with_tool = ModelFactory.create(
    model_platform=ModelPlatformType.SGLANG,
    model_type="meta-llama/Llama-3.2-1B-Instruct",
    model_config_dict={"temperature": 0.0, "tools": weather_tool},
    api_key="llama3",
)

assistant_sys_msg = (
    "You are a helpful assistant.\n"
    "Use the get_current_weather tool when asked about weather."
)
agent_with_tool = ChatAgent(
    assistant_sys_msg,
    model=sglang_model_with_tool,
    token_limit=4096,
    external_tools=weather_tool,
)
user_msg = "What's the weather in Boston today?"

assistant_response = agent_with_tool.step(user_msg)
external_tool_call = assistant_response.info.get('external_tool_call_request')
if external_tool_call:
    print(f"Detected external tool call: {external_tool_call.tool_name}")
    print(f"Arguments: {external_tool_call.args}")
    print(f"Tool Call ID: {external_tool_call.tool_call_id}")
else:
    print("No external tool call detected")

"""
===============================================================================
Detected external tool call: get_current_weather
Arguments: {'city': 'Boston', 'state': 'MA', 'unit': 'celsius'}
Tool Call ID: 0
===============================================================================
"""
