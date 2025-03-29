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
This code is borrowed and modified based on the source code from the
'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function maintenance_fluid_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.weight_conversion import (
    weight_conversion_explanation,
)


def maintenance_fluid_explanation(input_parameters):
    r"""
    Calculates the patient's maintenance fluid in mL/hr and
    generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following
        key-value pairs:
            - "weight" (tuple): The patient's weight information in the
            format (value, unit).
                - Value (float): The numerical weight measurement.
                - Unit (str): The unit of weight, which can be "lbs"
                (pounds), "g" (grams), or "kg" (kilograms).

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's maintenance fluid in mL/hr.

    Notes:
        - Uses the `weight_conversion_explanation` function to convert
        weight to kilogram.

    Example:
        maintenance_fluid_explanation(
        {
            "weight": (12.0, "kg"),  # weight 150 lbs
        })

        output: "{'Explanation': "The patient's weight is 12.0 kg. For
        patient's whose weight is in between 10 kg and 20 kg, the formula
        for computing maintenance fluid is 40 mL/hr + 2 mL/kg/hr * (weight (
        in kilograms) - 10 kilograms). Hence, plugging into this formula,
        we get 40 mL/hr + 2 mL/kg/hr * (12.0 kg - 10 kg) = 44.0
        mL/hr.\nHence, the patient's fluid maintenance is 44.0 mL/hr.\n",
        'Answer': 44.0}"
    """

    weight_exp, weight = weight_conversion_explanation(
        input_parameters["weight"]
    )

    explanation = ""

    explanation += weight_exp

    if weight < 10:
        answer = round_number(weight * 4)
        explanation += (
            f"For patient's with weight less than 10 kg, "
            f"the rule for computing maintenance fluid is "
            f"to multiply their weight by 4 mL/kg/hr to "
            f"get the maintenance fluids per hour. Hence, "
            f"the patient's maintenance fluid is {weight} "
            f"kg * 4 mL/kg/hr = {answer} mL/hr.\n"
        )
    elif 10 <= weight <= 20:
        answer = round_number(40 + 2 * (weight - 10))
        explanation += (
            f"For patient's whose weight is in between 10 kg and "
            f"20 kg, the formula for computing maintenance fluid "
            f"is 40 mL/hr + 2 mL/kg/hr * (weight (in kilograms) "
            f"- 10 kilograms). Hence, plugging into this "
            f"formula, we get 40 mL/hr + 2 mL/kg/hr * "
            f"({weight} kg - 10 kg) = {answer} mL/hr.\n"
        )
    elif weight > 20:
        answer = round_number(60 + (weight - 20))
        explanation += (
            f"For patient's whose weight is greater than 20 kg, "
            f"the formula for computing the maintenance fluid is "
            f"60 mL/hr + 1 mL/kg/hr * (weight (in kilograms) "
            f"- 20 kilograms). Hence, plugging into "
            f"this formula, we get 60 mL/hr + 2 mL/kg/hr "
            f"* ({weight} kg - 20 kg) = {answer} mL/hr.\n"
        )

    explanation += (
        f"Hence, the patient's fluid maintenance is {answer} " f"mL/hr.\n"
    )

    return {"Explanation": explanation, "Answer": answer}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "weight": (12.0, "kg"),  # weight 150 lbs
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = maintenance_fluid_explanation(input_variables)
        print(result)
        print("-" * 50)
