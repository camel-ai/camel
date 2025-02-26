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
from camel.data_collector import ShareGPTDataCollector
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

tool_list = MathToolkit().get_tools()

model_config_dict = ChatGPTConfig(
    tools=tool_list,
    temperature=0.0,
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


print(json.dumps(collector.convert(), indent=4))
print(json.dumps(collector.llm_convert(), indent=4))
print(collector.to_ShareGPTData(collector.convert()))


# ruff: noqa: E501
"""
{
    "system": "You are a helpful assistant",
    "tools": [
        {
            "name": "add",
            "description": "Adds two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The first number to be added."
                    },
                    "b": {
                        "type": "number",
                        "description": "The second number to be added."
                    }
                },
                "required": ["a", "b"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "sub",
            "description": "Do subtraction between two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The minuend in subtraction."
                    },
                    "b": {
                        "type": "number",
                        "description": "The subtrahend in subtraction."
                    }
                },
                "required": ["a", "b"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "multiply",
            "description": "Multiplies two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The multiplier in multiplication."
                    },
                    "b": {
                        "type": "number",
                        "description": "The multiplicand in multiplication."
                    },
                    "decimal_places": {
                        "type": "integer",
                        "description": "The number of decimal places to "
                                       "round to. Defaults to 2."
                    }
                },
                "required": ["a", "b", "decimal_places"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "divide",
            "description": "Divides two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The dividend in division."
                    },
                    "b": {
                        "type": "number",
                        "description": "The divisor in division."
                    },
                    "decimal_places": {
                        "type": "integer",
                        "description": "The number of decimal places to "
                                       "round to. Defaults to 2."
                    }
                },
                "required": ["a", "b", "decimal_places"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "round",
            "description": "Rounds a number to a specified number of decimal "
                           "places.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The number to be rounded."
                    },
                    "decimal_places": {
                        "type": "integer",
                        "description": "The number of decimal places to "
                                       "round to. Defaults to 0."
                    }
                },
                "required": ["a", "decimal_places"],
                "type": "object",
                "additionalProperties": false
            }
        }
    ],
    "conversations": [
        {
            "from": "human",
            "value": "Call tools to calculate 17 * 19 = ?"
        },
        {
            "from": "function_call",
            "value": {
                "name": "multiply",
                "arguments": {
                    "a": 17,
                    "b": 19,
                    "decimal_places": 0
                }
            }
        },
        {
            "from": "observation",
            "value": "323"
        },
        {
            "from": "gpt",
            "value": "The result of 17 times 19 is 323."
        }
    ]
}

{
    "system": "You are a helpful assistant",
    "tools": [
        {
            "name": "add",
            "description": "Adds two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The first number to be added."
                    },
                    "b": {
                        "type": "number",
                        "description": "The second number to be added."
                    }
                },
                "required": ["a", "b"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "sub",
            "description": "Do subtraction between two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The minuend in subtraction."
                    },
                    "b": {
                        "type": "number",
                        "description": "The subtrahend in subtraction."
                    }
                },
                "required": ["a", "b"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "multiply",
            "description": "Multiplies two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The multiplier in multiplication."
                    },
                    "b": {
                        "type": "number",
                        "description": "The multiplicand in multiplication."
                    },
                    "decimal_places": {
                        "type": "integer",
                        "description": "The number of decimal places to "
                                       "round to. Defaults to 2."
                    }
                },
                "required": ["a", "b", "decimal_places"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "divide",
            "description": "Divides two numbers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The dividend in division."
                    },
                    "b": {
                        "type": "number",
                        "description": "The divisor in division."
                    },
                    "decimal_places": {
                        "type": "integer",
                        "description": "The number of decimal places to "
                                       "round to. Defaults to 2."
                    }
                },
                "required": ["a", "b", "decimal_places"],
                "type": "object",
                "additionalProperties": false
            }
        },
        {
            "name": "round",
            "description": "Rounds a number to a specified number of decimal "
                           "places.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The number to be rounded."
                    },
                    "decimal_places": {
                        "type": "integer",
                        "description": "The number of decimal places to "
                                       "round to. Defaults to 0."
                    }
                },
                "required": ["a", "decimal_places"],
                "type": "object",
                "additionalProperties": false
            }
        }
    ],
    "conversations": [
        {
            "from": "human",
            "value": "Call tools to calculate 17 * 19 = ?"
        },
        {
            "from": "function_call",
            "value": {
                "name": "multiply",
                "arguments": {
                    "a": 17,
                    "b": 19,
                    "decimal_places": 0
                }
            }
        },
        {
            "from": "observation",
            "value": "323"
        },
        {
            "from": "gpt",
            "value": "The result of 17 times 19 is 323."
        }
    ]
}

system='You are a helpful assistant' tools='[{"name": "add", "description": "Adds two numbers.", "parameters": {"properties": {"a": {"type": "number", "description": "The first number to be added."}, "b": {"type": "number", "description": "The second number to be added."}}, "required": ["a", "b"], "type": "object", "additionalProperties": false}}, {"name": "sub", "description": "Do subtraction between two numbers.", "parameters": {"properties": {"a": {"type": "number", "description": "The minuend in subtraction."}, "b": {"type": "number", "description": "The subtrahend in subtraction."}}, "required": ["a", "b"], "type": "object", "additionalProperties": false}}, {"name": "multiply", "description": "Multiplies two numbers.", "parameters": {"properties": {"a": {"type": "number", "description": "The multiplier in the multiplication."}, "b": {"type": "number", "description": "The multiplicand in the multiplication."}, "decimal_places": {"type": "integer", "description": "The number of decimal\\nplaces to round to. Defaults to 2."}}, "required": ["a", "b", "decimal_places"], "type": "object", "additionalProperties": false}}, {"name": "divide", "description": "Divides two numbers.", "parameters": {"properties": {"a": {"type": "number", "description": "The dividend in the division."}, "b": {"type": "number", "description": "The divisor in the division."}, "decimal_places": {"type": "integer", "description": "The number of\\ndecimal places to round to. Defaults to 2."}}, "required": ["a", "b", "decimal_places"], "type": "object", "additionalProperties": false}}, {"name": "round", "description": "Rounds a number to a specified number of decimal places.", "parameters": {"properties": {"a": {"type": "number", "description": "The number to be rounded."}, "decimal_places": {"type": "integer", "description": "The number of decimal places\\nto round to. Defaults to 0."}}, "required": ["a", "decimal_places"], "type": "object", "additionalProperties": false}}]' conversations=[ShareGPTMessage(from_='human', value='Call tools to calculate 17 * 19 = ?'), ShareGPTMessage(from_='function_call', value='[{"id": "call_4ciQdzdrxytVQFhBQ3qtz3ch", "type": "function", "function": {"name": "multiply", "arguments": "{\\"a\\": 17, \\"b\\": 19, \\"decimal_places\\": 0}"}}]'), ShareGPTMessage(from_='observation', value='"323"'), ShareGPTMessage(from_='gpt', value='The result of \\( 17 \\times 19 \\) is \\( 323 \\).')]

"""
