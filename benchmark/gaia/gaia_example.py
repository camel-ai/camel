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
from functools import wraps
from os import environ as env
from typing import Any

from huggingface_hub import login

from benchmark.gaia import GAIABenchmark
from benchmark.gaia.cache_wrapper import create_function_cacher
from benchmark.gaia.ChatCollector import ChatCollector
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import OpenAIModel
from camel.toolkits import (
    MATH_FUNCS,
    SEARCH_FUNCS,
    OpenAIFunction,
    SearchToolkit,
)
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelType

# Create the cacher
cacher = create_function_cacher('function_cache.json')
calls_per_task_dict = {}


def add_explanation(
    func: OpenAIFunction, just_too_many_calls=False
) -> OpenAIFunction:
    @wraps(func.func)
    def wrapper_no_explanation(*args, **kwargs) -> Any:
        if gaia.current_task is not None:
            task = gaia.current_task['Question']
            if task not in calls_per_task_dict:
                calls_per_task_dict[task] = 0
            calls_per_task_dict[task] += 1
            if calls_per_task_dict[task] > 12:
                raise Exception("Too many calls")
        return cacher([func.func])[0](*args, **kwargs)

    @wraps(func.func)
    def wrapper(*args, explanation: str = "", **kwargs) -> Any:
        if gaia.current_task is not None:
            task = gaia.current_task['Question']
            if task not in calls_per_task_dict:
                calls_per_task_dict[task] = 0
            calls_per_task_dict[task] += 1
            if calls_per_task_dict[task] > 25:
                raise Exception("Too many calls")
            print(
                f"[{calls_per_task_dict[task]}] Calling {func.openai_tool_schema['function']['name']} with explanation: {explanation}"
            )
        else:
            print(
                f"Calling {func.openai_tool_schema['function']['name']} with explanation: {explanation}"
            )
        print(f"Arguments: {args}, {kwargs}")
        result = cacher([func.func])[0](*args, **kwargs)
        print(f"Result: {result}")

        return result

    new_schema = {
        'type': 'function',
        'function': {
            'name': func.openai_tool_schema['function']['name'],
            'description': func.openai_tool_schema['function']['description'],
            'parameters': {
                'properties': {
                    'explanation': {
                        'type': 'string',
                        'description': 'Explanation, reasoning, and thinking out loud for the function call',
                    },
                    **func.openai_tool_schema['function']['parameters'][
                        'properties'
                    ],
                },
                'required': ['explanation']
                + func.openai_tool_schema['function']['parameters'].get(
                    'required', []
                ),
                'type': 'object',
            },
        },
    }
    if just_too_many_calls:
        return OpenAIFunction(
            wrapper_no_explanation, openai_tool_schema=func.openai_tool_schema
        )
    return OpenAIFunction(wrapper, openai_tool_schema=new_schema)


# Login to the Hugging Face Hub with environment variable HF_HOME

login(token=env["HF_HOME"])

task_prompt = """
        You are a general AI assistant. I will ask you a question. Report your 
        thoughts, and finish your answer with the following template: 
        FINAL ANSWER: [YOUR FINAL ANSWER].
        YOUR FINAL ANSWER should be a number OR as few words as possible OR a 
        comma separated list of numbers and/or strings.
        If you are asked for a number, don't use comma to write your number 
        neither use units such as $ or percent sign unless specified otherwise.
        If you are asked for a string, don't use articles, neither 
        abbreviations (e.g. for cities), and write the digits in plain text 
        unless specified otherwise.
        If you are asked for a comma separated list, apply the above rules 
        depending of whether the element to be put in the list is a number or 
        a string.
        """.strip()
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content=task_prompt,
)
gaia = GAIABenchmark()

gaia.download()
# Wrap the functions
# TODO: More nicely select specific functions and wrap them
wrapped_math_funcs = [add_explanation(func) for func in MATH_FUNCS]
wrapped_code_execution_funcs = [
    add_explanation(func) for func in CodeExecutionToolkit().get_tools()
]
wrapped_search_funcs = [
    add_explanation(func) for func in SearchToolkit().get_tools()
]

# Update the function_list
function_list = [
    add_explanation(SEARCH_FUNCS[6], just_too_many_calls=True),
    *wrapped_math_funcs,
    wrapped_search_funcs[1],
    wrapped_search_funcs[4],
    wrapped_search_funcs[5],
]

config = ChatGPTConfig(
    tools=function_list,
    temperature=0.0,
    frequency_penalty=0.0,
    max_tokens=2000,
    top_p=1.00,
)

import json

functions = [
    {
        "type": "function",
        "function": {
            "name": func.openai_tool_schema['function']['name'],
            "strict": True,
            "description": func.openai_tool_schema['function']['description'],
            "parameters": func.openai_tool_schema['function']['parameters'],
        },
    }
    for func in function_list
]
function_list_json = json.dumps(functions, indent=2)

print(function_list_json)

collector = ChatCollector()
collector.inject()

agent = ChatAgent(
    system_message=sys_msg,
    tools=function_list,
    token_limit=4000,
    model=OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=config.__dict__,
    ),
)

# scores = gaia.eval(agent, [1], "validation")
scores = gaia.eval(agent, ['all'], "validation")
all_conversations = collector.get_all_conversations()
all_json_output = collector.to_json()  # for all conversations
# Save all_json_output to a file
with open("all_conversations.json", "w") as f:
    f.write(all_json_output)

print(scores)
