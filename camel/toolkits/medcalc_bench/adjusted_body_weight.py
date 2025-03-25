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
"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function weight_conversion_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench import ideal_body_weight
from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.weight_conversion import (
    weight_conversion_explanation,
)


def abw_explanation(input_variables):
    """
    Calculates the patient's Adjusted Body Weight (ABW) and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "weight" (tuple): The patient's weight information in the format (value, unit).
                - Value (float): The numerical weight measurement.
                - Unit (str): The unit of weight, which can be "lbs" (pounds), "g" (grams), or "kg" (kilograms).
            - "height" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters) or "in" (inches).
            - "sex" (str): The patient's gender, which can be either "Male" or "Female".

    Returns:
        dict: Contains three key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process, including IBW and ABW calculations.
            - "ABW" (str): The specific formula and result for ABW calculation.
            - "Answer" (float): The patient's adjusted body weight (in kilograms).

    Notes:
        - Uses the `weight_conversion.weight_conversion_explanation` function to convert weight to kilograms.
        - Uses the `ideal_body_weight.ibw_explanation` function to calculate Ideal Body Weight (IBW).
        - Uses the `round_number` function to round the result.

    Example:
        abw_explanation({'weight': (150, 'lbs'), 'height': (170, 'cm'), 'sex': 'Male'})
        output: "{'Explanation': "The patient's gender is Male.\nThe patient's height is 170 cm, which is 170 cm * 0.393701 in/cm = 66.929
        in. \nFor males, the ideal body weight (IBW) is calculated as follows:\nIBW = 50 kg + 2.3 kg * (height (in inches) - 60)\nPlugging
        in the values gives us 50 kg + 2.3 kg * (66.929 (in inches) - 60) = 65.937 kg.\nHence, the patient's IBW is 65.937 kg.The
        patient's weight is 150 lbs so this converts to 150 lbs * 0.453592 kg/lbs = 68.039 kg. To compute the ABW value, apply the
        following formula: ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). ABW = 65.937 kg + 0.4 * (68.039 kg  -
        65.937 kg) = 66.778 kg. The patient's adjusted body weight is 66.778 kg.\n", 'ABW': "To compute the ABW value, apply the following
        formula: ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). ABW = 65.937 kg + 0.4 * (68.039 kg  - 65.937 kg) = 66.778 kg. The
        patient's adjusted body weight is 66.778 kg.\n", 'Answer': 66.778}"
    """

    weight_explanation, weight = weight_conversion_explanation(
        input_variables["weight"]
    )
    ibw_explanation = ideal_body_weight.ibw_explanation(input_variables)

    explanation = f"{ibw_explanation['Explanation']}"
    explanation += f"{weight_explanation}"

    ibw = ibw_explanation["Answer"]

    abw = round_number(ibw + 0.4 * (weight - ibw))
    abw_explanation_string = ""
    abw_explanation_string += (
        "To compute the ABW value, apply the following formula: "
    )
    abw_explanation_string += (
        "ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). "
    )
    abw_explanation_string += (
        f"ABW = {ibw} kg + 0.4 * ({weight} kg  - {ibw} kg) = {abw} kg. "
    )
    abw_explanation_string += (
        f"The patient's adjusted body weight is {abw} kg.\n"
    )

    explanation += abw_explanation_string

    return {
        "Explanation": explanation,
        "ABW": abw_explanation_string,
        "Answer": abw,
    }


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "weight": (150, "lbs"),  # weight 150 lbs
            "height": (170, "cm"),  # height 170 cm
            "sex": "Male",  # Male
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = abw_explanation(input_variables)
        print(result)
        print("-" * 50)
