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
- rewrite function compute_sodium_correction_hyperglycemia_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_sodium_correction_hyperglycemia_explanation(input_variables):
    r"""
    Calculates the patient's corrected sodium concentration in terms of
    mEq/L and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following
        key-value pairs:
            - "glucose" (tuple): The patient's blood glucose level in the
            format (value, unit).
                - Value (float): The value of blood glucose level.
                - Unit (str): The unit of blood glucose level,
                eg. "mmol/L", "mEq/L", and so on.
            - "sodium" (array): The patient's blood sodium level in the
            format (value, unit).
                - Value (float): The blood sodium level.
                - Unit (str): The unit of blood sodium level.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's corrected sodium concentration.

    Notes:
        - None

    Example:
        free_water_deficit_explanation({
        'glucose': (90.0, 'mg/dL'),
        'sodium': (134.0, 'mEq/L')})

        output: "{'Explanation': "The formula for Sodium Correction for
        Hyperglycemia is Measured sodium + 0.024 * (Serum glucose - 100),
        where Measured Sodium is the sodium concentration in mEq/L and the
        Serum glucose is the concentration of glucose in mg/dL.\nThe
        concentration of sodium is 134.0 mEq/L. \nThe concentration of
        glucose is 90.0 mg/dL. \nPlugging in these values into the formula
        gives us 134.0 mEq/L + 0.024 * (90.0 - 100) = 133.76 mEq/L.\nHence,
        the patient's corrected concentration of sodium is 133.76 mEq/L.\n",
        'Answer': 133.76}"
    """

    sodium = input_variables["sodium"]
    glucose = input_variables["glucose"]

    sodium_explanation, sodium = conversion_explanation(
        sodium[0], "sodium", 22.99, 1, sodium[1], "mEq/L"
    )
    glucose_explanation, glucose = conversion_explanation(
        glucose[0], "glucose", 180.16, None, glucose[1], "mg/dL"
    )

    corrected_sodium = round_number(sodium + 0.024 * (glucose - 100))

    explanation = (
        "The formula for Sodium Correction for Hyperglycemia is "
        "Measured sodium + 0.024 * (Serum glucose - 100), "
        "where Measured Sodium is the sodium concentration in "
        "mEq/L and the Serum glucose is the concentration of "
        "glucose in mg/dL.\n"
    )

    explanation += sodium_explanation + "\n"
    explanation += glucose_explanation + "\n"

    explanation += (
        f"Plugging in these values into the formula gives us "
        f"{sodium} mEq/L + 0.024 * ({glucose} - 100) = "
        f"{corrected_sodium} mEq/L.\n"
    )

    explanation += (
        f"Hence, the patient's corrected concentration of sodium "
        f"is {corrected_sodium} mEq/L.\n"
    )

    return {"Explanation": explanation, "Answer": corrected_sodium}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {'glucose': (90.0, 'mg/dL'), 'sodium': (134.0, 'mEq/L')},
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_sodium_correction_hyperglycemia_explanation(
            input_variables
        )
        print(result)
        print("-" * 50)
