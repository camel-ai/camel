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
r"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function targetweight_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.height_conversion import (
    height_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.rounding import round_number


def targetweight_explanation(input_variables):
    r"""
    Calculates the patient's delta gap and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "body_mass_index" (tuple): The patient's BMI in the format (value, unit).
                - Value (float): The patient's BMI value.
                - Unit (str): The unit of BMI.
            - "height" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters) or "in" (inches).

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's target weight.

    Notes:
        - Uses the `height_conversion_explanation` function to convert height to meters.

    Example:
        targetweight_explanation({"body_mass_index": (20.1, "kg/m^2"),"height": (72, "in"),})
        output: "{'Explanation': "The patient's target bmi is 20.1 kg/m^2. The patient's height is 72 in,
        which is 72 in * 0.0254 m / in = 1.829 m. From this,
        the patient's target weight is 20.1 kg/m^2 * 1.829 m * 1.829 m = 67.239 kg. ", 'Answer': 67.239}"
    """

    bmi = input_variables["body_mass_index"][0]
    height_exp, height = height_conversion_explanation(
        input_variables["height"]
    )
    target_weight_val = round_number(bmi * (height * height))

    explanation = ""

    explanation += f"The patient's target bmi is {bmi} kg/m^2. "

    explanation += f"{height_exp}"

    explanation += f"From this, the patient's target weight is {bmi} kg/m^2 * {height} m * {height} m = {target_weight_val} kg. "

    return {"Explanation": explanation, "Answer": target_weight_val}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "body_mass_index": (20.1, "kg/m^2"),
            "height": (72, "in"),
        },
        {
            "body_mass_index": (22.0, "kg/m^2"),
            "height": (75, "in"),
        },
    ]
    # {'Body Mass Index (BMI)': [20.1, 'kg/m^2'], 'height': [72, 'in']}
    # {'Body Mass Index (BMI)': [22.0, 'kg/m^2'], 'height': [75, 'in']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = targetweight_explanation(input_variables)
        print(result)
        print("-" * 50)
