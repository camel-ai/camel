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
from camel.agents._utils import convert_to_schema, generate_tool_prompt
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
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
the base model may fail to recognize huggingface default
chat template, switching to the Instruct model resolves the issue.
"""
load_dotenv()


def get_current_weather(city: str, state: str, unit: str):
    """Get the current weather in a given location.

    Args:
        city: The city to get the weather for (e.g., 'New York')
        state: The two-letter abbreviation for the state (e.g., 'NY')
        unit: The unit to fetch the temperature in ('celsius' or 'fahrenheit')

    Returns:
        Information about the current weather
    """
    # This is a mock function for demonstration purposes
    return {
        "location": f"{city}, {state}",
        "temperature": 72 if unit == "fahrenheit" else 22,
        "unit": unit,
        "forecast": "Sunny with occasional clouds",
    }


def get_current_date(timezone: str):
    """Get the current date and time for a given timezone.

    Args:
        timezone: The timezone to fetch the current date and time for
                 (e.g., 'America/New_York')

    Returns:
        Information about the current date and time
    """
    # This is a mock function for demonstration purposes
    return {
        "timezone": timezone,
        "date": "2024-04-21",
        "time": "10:30:00",
    }


def main():
    # Define the tools using FunctionTool
    weather_tool = FunctionTool(get_current_weather)
    date_tool = FunctionTool(get_current_date)

    # Convert function tools to schema format
    weather_schema = convert_to_schema(weather_tool)
    date_schema = convert_to_schema(date_tool)

    # List of tools to use
    tools = [weather_schema, date_schema]

    # Get parameter schemas for structural tag format
    weather_params_schema = weather_schema["function"]["parameters"]
    date_params_schema = date_schema["function"]["parameters"]

    # Create SglLang model with tools
    sglang_model = ModelFactory.create(
        model_platform=ModelPlatformType.SGLANG,
        model_type="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        model_config_dict={
            "temperature": 0.0,
            "response_format": {
                "type": "structural_tag",
                "structures": [
                    {
                        "begin": "<function=get_current_weather>",
                        "schema": weather_params_schema,
                        "end": "</function>",
                    },
                    {
                        "begin": "<function=get_current_date>",
                        "schema": date_params_schema,
                        "end": "</function>",
                    },
                ],
                "triggers": ["<function="],
            },
        },
    )

    # Generate tool prompt using CAMEL's native method
    tool_prompt = generate_tool_prompt(tools)

    # Create chat agent with the model and tool prompt
    agent = ChatAgent(
        system_message=tool_prompt,
        model=sglang_model,
        token_limit=4096,
    )

    # User message
    user_msg = (
        "You are in New York. Please get the current date and time,"
        "and the weather."
    )

    # Get assistant response
    assistant_response = agent.step(user_msg)
    content = assistant_response.msgs[0].content

    # Split thought process and function calls if present
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


if __name__ == "__main__":
    main()
