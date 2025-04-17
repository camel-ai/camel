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

tool_get_current_weather = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The two-letter abbreviation for,\n"
                    "the state (e.g., 'CA'), e.g. CA for California",
                },
                "state": {
                    "type": "string",
                    "description": "the two-letter abbreviation for the"
                    "state that the city is in, e.g. 'CA' which would mean\n"
                    "'California'",
                },
                "unit": {
                    "type": "string",
                    "description": "The unit to fetch the temperature in",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["city", "state", "unit"],
        },
    },
}

tool_get_current_date = {
    "type": "function",
    "function": {
        "name": "get_current_date",
        "description": "Get the current date and time for a given timezone",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The timezone to fetch the current date\n"
                    "and time for, e.g. 'America/New_York'",
                }
            },
            "required": ["timezone"],
        },
    },
}

schema_get_current_weather = tool_get_current_weather["function"]["parameters"]
schema_get_current_date = tool_get_current_date["function"]["parameters"]


def get_messages():
    return [
        {
            "role": "system",
            "content": f"""
# Tool Instructions
- Always execute python code in messages that you share.
- When looking for real time information use relevant functions if available
  else fallback to brave_search
You have access to the following functions:
Use the function 'get_current_weather' to: Get the current weather in a given
location
{tool_get_current_weather["function"]}
Use the function 'get_current_date' to: Get the current date and time for a
given timezone
{tool_get_current_date["function"]}
If a you choose to call a function ONLY reply in the following format:
<{{start_tag}}={{function_name}}>{{parameters}}{{end_tag}}
where
start_tag => `<function`
parameters => a JSON dict with the function argument name as key and function
              argument value as value.
end_tag => `</function>`
Here is an example,
<function=example_function_name>{{"example_name": "example_value"}}</function>
Reminder:
- Function calls MUST follow the specified format
- Required parameters MUST be specified
- Only call one function at a time
- Put the entire function call reply on one line
- Always add your sources when using search results to answer the user query
You are a helpful assistant.""",
        },
        {
            "role": "user",
            "content": "You are in New York. Please get the current date and "
            "time, and the weather.",
        },
    ]


messages = get_messages()

sglang_model_with_tool = ModelFactory.create(
    model_platform=ModelPlatformType.SGLANG,
    model_type="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    model_config_dict={
        "temperature": 0.0,
        "response_format": {
            "type": "structural_tag",
            "structures": [
                {
                    "begin": "<function=get_current_weather>",
                    "schema": schema_get_current_weather,
                    "end": "</function>",
                },
                {
                    "begin": "<function=get_current_date>",
                    "schema": schema_get_current_date,
                    "end": "</function>",
                },
            ],
            "triggers": ["<function="],
        },
    },
)

agent_with_tool = ChatAgent(
    system_message=messages[0]["content"],
    model=sglang_model_with_tool,
    token_limit=4096,
)
user_msg = messages[1]["content"]

assistant_response = agent_with_tool.step(user_msg)
content = assistant_response.msgs[0].content

# Split thought process and function calls
if "</think>" in content:
    think_part, function_part = content.split("</think>", 1)
else:
    think_part = content
    function_part = ""

print("\n")
# Print thought process
print("【Assistant Thought Process】")
print(think_part.strip())

print("\n")
# Print function calls if they exist
if function_part:
    print("【Tool Calls】")
    print(function_part.strip())

print("\n")
print(f"ID: {assistant_response.info['id']}")
print("Usage:")

usage_info = assistant_response.info["usage"]
print(f"  Completion Tokens: {usage_info['completion_tokens']}")
print(f"  Prompt Tokens: {usage_info['prompt_tokens']}")
print(f"  Total Tokens: {usage_info['total_tokens']}")

termination_reasons = assistant_response.info["termination_reasons"]
print("Termination Reasons: " + ", ".join(termination_reasons))

print(f"Num Tokens: {assistant_response.info['num_tokens']}")


"""
===============================================================================
【Assistant Thought Process】
Okay, so the user is asking for the current date and time in New York and
theweather there. I need to figure out how to get this information using
the functions provided.
First, I should use the get_current_date function. The parameters required
are the timezone. Since the user is in New York, I'll set the timezone
parameter to 'America/New_York'. That should give me the current date
and time in that location.
Next, for the weather, I should use get_current_weather. The parameters needed
are city, state, and unit. The city is New York, but I need the state 
abbreviation. New York's state is NY, so the state parameter will be 'NY'. 
The unit should be in Fahrenheit since that's what the user might prefer,
but I'm not sure. Wait, the function allows any unit, but the user didn't
specify, so maybe I should default to Fahrenheit or check if Celsius is more
common. Hmm, but the example response used Fahrenheit, so I'll go with that.
Putting it all together, I'll call get_current_date with the timezone and
get_current_weather with the city, state, and unit. I'll make sure to format
the function calls correctly, each on a separate line as per the instructions.


【Tool Calls】
<function=get_current_date>{"timezone": "America/New_York"}</function>  
<function=get_current_weather>{"city": "New York", "state": "NY", "unit":
"fahrenheit"}</function>


ID: 3b49116d8dc84e18b6a9c935b7a4dd2c
Usage:
  Completion Tokens: 305
  Prompt Tokens: 487
  Total Tokens: 792
Termination Reasons: stop
Num Tokens: 496
===============================================================================
"""
