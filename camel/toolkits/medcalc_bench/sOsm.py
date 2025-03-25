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
- rewrite function compute_serum_osmolality_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_serum_osmolality_explanation(input_parameters):
    r"""
    Calculates the patient's Serum Osmolality and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "bun" (array): The patient's blood urea nitrogen level in the format (value, unit).
                - Value (float): The value of blood urea nitrogen level.
                - Unit (str): The unit of blood urea nitrogen level, eg. "mg/dL", "mEq/L", and so on.
            - "glucose" (array): The patient's blood glucose level in the format (value, unit).
                - Value (float): The value of blood glucose level.
                - Unit (str): The unit of blood glucose level, eg. "mmol/L", "mEq/L", and so on.
            - "sodium" (array): The patient's bicarbonate level in the format (value, unit).
                - Value (float): The value of bicarbonate level.
                - Unit (str): The unit of bicarbonate level, eg. "mmol/L", "mEq/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's Serum Osmolality.

    Notes:
        - None

    Example:
        compute_serum_osmolality_explanation({'bun': [20.0, 'mg/dL'],'glucose': [599.0, 'mg/dL'],'sodium': [139.0, 'mEq/L']})
        output: "{'Explanation': "The formula for computing serum osmolality is 2 * Na + (BUN / 2.8) + (glucose / 18),
        where Na is the concentration of sodium in mmol/L, the concentration of BUN is in mg/dL,
        and the concentration of glucose is in mg/dL.\nThe concentration of sodium is 139.0 mEq/L.
        We need to convert the concentration to mmol/L. Let's first convert the mass of sodium from mEq to mmol.
        The mass of sodium is 139.0 mEq. To convert from 139.0 mEq to mmol, convert from mEq to mmol.
        The compound 139.0 has a valence of 1, and so divide the valence by the value of mEq to
        get, 139.0 mEq/(1 mEq/mmol) = 139.0 mmol sodium. The volume units is L so no volume conversion is needed.
        Hence, the concentration value of 139.0 mEq sodium/L converts to 139.0 mmol sodium/L.
        \nThe concentration of bun is 20.0 mg/dL. \nThe concentration of glucose is 599.0 mg/dL.
        \nPlugging these values into the equation, we get 2 * 139.0 + (20.0 / 2.8) + (20.0 / 18) = 318.421 mmol/L.
        The patient's calculated serum osmolality concentration is 318.421 mmol/L.
        This is equalivalent to 318.421 mOsm/kg.\n", 'Answer': 318.421}"
    """

    explanation = "The formula for computing serum osmolality is 2 * Na + (BUN / 2.8) + (glucose / 18), " \
                  "where Na is the concentration of sodium in mmol/L, " \
                  "the concentration of BUN is in mg/dL, and the concentration of glucose is in mg/dL.\n"

    sodium_exp, sodium = conversion_explanation(
        input_parameters["sodium"][0],
        "sodium",
        22.99,
        1,
        input_parameters["sodium"][1],
        "mmol/L",
    )
    bun_exp, bun = conversion_explanation(
        input_parameters["bun"][0],
        "bun",
        28.02,
        None,
        input_parameters["bun"][1],
        "mg/dL",
    )
    glucose_exp, glucose = conversion_explanation(
        input_parameters["glucose"][0],
        "glucose",
        180.16,
        None,
        input_parameters["glucose"][1],
        "mg/dL",
    )

    explanation += sodium_exp + "\n"
    explanation += bun_exp + "\n"
    explanation += glucose_exp + "\n"

    serum_os = round_number(2 * sodium + (bun / 2.8) + (glucose / 18))

    explanation += f"Plugging these values into the equation, " \
                   f"we get 2 * {sodium} + ({bun} / 2.8) + ({bun} / 18) = {serum_os} mmol/L."
    explanation += f"The patient's calculated serum osmolality concentration is {serum_os} mmol/L. " \
                   f"This is equalivalent to {serum_os} mOsm/kg.\n"

    return {"Explanation": explanation, "Answer": serum_os}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            'bun': [20.0, 'mg/dL'],
            'glucose': [599.0, 'mg/dL'],
            'sodium': [139.0, 'mEq/L'],
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_serum_osmolality_explanation(input_variables)
        print(result)
        print("-" * 50)
