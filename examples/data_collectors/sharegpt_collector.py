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

import json

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.data_collectors import ShareGPTDataCollector
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

tool_list = MathToolkit().get_tools()

model_config_dict = ChatGPTConfig(
    tools=tool_list,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Set external_tools
agent = ChatAgent(
    system_message="You are a helpful assistant",
    model=model,
    tools=tool_list,
)
collector = ShareGPTDataCollector().record(agent).start()

# This will directly run the internal tool
response = agent.step("Call tools to calculate 17 * 19 = ?")


print(json.dumps(collector.convert(), indent=4, ensure_ascii=False))
print(json.dumps(collector.llm_convert(), indent=4, ensure_ascii=False))
print(collector.to_sharegpt_conversation(collector.convert()))

# ruff: noqa: E501
"""
{
    "system": "You are a helpful assistant",
    "tools": "[{\"name\": \"add\", \"description\": \"Adds two numbers.\", \"parameters\": {\"properties\": {\"a\": {\"type\": \"integer\", \"description\": \"The first number to be added.\"}, \"b\": {\"type\": \"integer\", \"description\": \"The second number to be added.\"}}, \"required\": [\"a\", \"b\"], \"type\": \"object\"}}, {\"name\": \"sub\", \"description\": \"Do subtraction between two numbers.\", \"parameters\": {\"properties\": {\"a\": {\"type\": \"integer\", \"description\": \"The minuend in subtraction.\"}, \"b\": {\"type\": \"integer\", \"description\": \"The subtrahend in subtraction.\"}}, \"required\": [\"a\", \"b\"], \"type\": \"object\"}}, {\"name\": \"mul\", \"description\": \"Multiplies two integers.\", \"parameters\": {\"properties\": {\"a\": {\"type\": \"integer\", \"description\": \"The multiplier in the multiplication.\"}, \"b\": {\"type\": \"integer\", \"description\": \"The multiplicand in the multiplication.\"}}, \"required\": [\"a\", \"b\"], \"type\": \"object\"}}]",
    "conversations": [
        {
            "from": "human",
            "value": "Call tools to calculate 17 * 19 = ?"
        },
        {
            "from": "function_call",
            "value": "{\"name\": \"mul\", \"arguments\": {\"a\": 17, \"b\": 19}}"
        },
        {
            "from": "observation",
            "value": "323"
        },
        {
            "from": "gpt",
            "value": "The result of \\( 17 \\times 19 \\) is \\( 323 \\)."
        }
    ]
}
{
    "system": "You are a helpful assistant",
    "tools": "[{\"name\": \"add\", \"description\": \"Adds two numbers.\", \"parameters\": {\"properties\": {\"a\": {\"type\": \"integer\", \"description\": \"The first number to be added.\"}, \"b\": {\"type\": \"integer\", \"description\": \"The second number to be added.\"}}, \"required\": [\"a\", \"b\"], \"type\": \"object\"}}, {\"name\": \"sub\", \"description\": \"Do subtraction between two numbers.\", \"parameters\": {\"properties\": {\"a\": {\"type\": \"integer\", \"description\": \"The minuend in subtraction.\"}, \"b\": {\"type\": \"integer\", \"description\": \"The subtrahend in subtraction.\"}}, \"required\": [\"a\", \"b\"], \"type\": \"object\"}}, {\"name\": \"mul\", \"description\": \"Multiplies two integers.\", \"parameters\": {\"properties\": {\"a\": {\"type\": \"integer\", \"description\": \"The multiplier in the multiplication.\"}, \"b\": {\"type\": \"integer\", \"description\": \"The multiplicand in the multiplication.\"}}, \"required\": [\"a\", \"b\"], \"type\": \"object\"}}]",
    "conversations": [
        {
            "from_": "human",
            "value": "Tools calling operator: Call tools to calculate 17 * 19 = ?"
        },
        {
            "from_": "function_call",
            "value": "{\"name\": \"mul\", \"arguments\": {\"a\": 17, \"b\": 19}}"
        },
        {
            "from_": "gpt",
            "value": "The result of \\( 17 \\times 19 \\) is \\( 323 \\)."
        }
    ]
}
root=[ShareGPTMessage(from_='system', value='You are a helpful assistant'), ShareGPTMessage(from_='human', value='Call tools to calculate 17 * 19 = ?'), ShareGPTMessage(from_='gpt', value='{"name": "multiply", "arguments": "{\'a\': 17, \'b\': 19}"}'), ShareGPTMessage(from_='human', value='"{\'result\': {\'323\'}}"'), ShareGPTMessage(from_='gpt', value='The result of \\( 17 \\times 19 \\) is \\( 323 \\).')]
"""
