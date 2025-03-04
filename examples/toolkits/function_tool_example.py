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
from typing import Dict, Any

from camel.agents import ChatAgent
from camel.toolkits import tool


@tool()
def calculate_bmi(
    weight: float,
    height: float,
) -> Dict[str, Any]:
    r"""Calculate BMI (Body Mass Index) and provide health status.

    Args:
        weight (float): Weight in kilograms.
        height (float): Height in meters.

    Returns:
        Dict[str, Any]: Dictionary containing BMI value and health status.
    """
    bmi = weight / (height * height)
    
    if bmi < 18.5:
        status = "Underweight"
    elif 18.5 <= bmi < 24.9:
        status = "Normal weight"
    elif 24.9 <= bmi < 29.9:
        status = "Overweight"
    else:
        status = "Obese"
    
    return {
        "bmi": round(bmi, 2),
        "status": status
    }


def main():
    system_message = """You are a health assistant that helps calculate BMI.
    When users mention their height and weight, use the calculate_bmi tool to:
    1. Calculate their BMI
    2. Determine their health status
    3. Provide the results in a clear format
    
    Do NOT perform the calculation yourself. Always use the tool."""

    agent = ChatAgent(
        system_message,
        tools=[calculate_bmi],
    )

    messages = [
        "I am 70 kg and 1.75 meters tall. What's my BMI?",
        "If someone is 80 kg and 1.8 meters, are they overweight?",
        "My friend weighs 65 kg with height 1.7 meters, check their BMI.",
    ]

    for msg in messages:
        print("\nUser:", msg)
        response = agent.step(msg)
        print("Assistant:", response.msgs[0].content)
        if "tool_calls" in response.info:
            print("\nTool Calls:")
            for call in response.info["tool_calls"]:
                print(call)

if __name__ == "__main__":
    main()

'''
===============================================================================
User: I am 70 kg and 1.75 meters tall. What's my BMI?
Assistant: Your BMI is 22.86, which falls within the "Normal weight" category.

Tool Calls:
Tool Execution: calculate_bmi
        Args: {'weight': 70, 'height': 1.75}
        Result: {'bmi': 22.86, 'status': 'Normal weight'}


User: If someone is 80 kg and 1.8 meters, are they overweight?
Assistant: For someone who is 80 kg and 1.8 meters tall, their BMI is 24.69, 
    which is classified as "Normal weight." Therefore, they are not 
    considered overweight.

Tool Calls:
Tool Execution: calculate_bmi
        Args: {'weight': 80, 'height': 1.8}
        Result: {'bmi': 24.69, 'status': 'Normal weight'}


User: My friend weighs 65 kg with height 1.7 meters, check their BMI.
Assistant: Your friend's BMI is 22.49, which is categorized as "Normal weight."

Tool Calls:
Tool Execution: calculate_bmi
        Args: {'weight': 65, 'height': 1.7}
        Result: {'bmi': 22.49, 'status': 'Normal weight'}
===============================================================================
'''