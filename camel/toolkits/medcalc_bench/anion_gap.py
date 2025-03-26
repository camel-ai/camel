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
- rewrite function compute_anion_gap_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_anion_gap_explanation(input_parameters):
    r"""
    Calculates the patient's anion gap and generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following key-value pairs:
            - "sodium" (array): The patient's blood sodium level in the format (value, unit).
                - Value (float): The blood sodium level.
                - Unit (str): The unit of blood sodium level.
            - "chloride" (array): The patient's chloride level in the format (value, unit).
                - Value (float): The value of chloride level.
                - Unit (str): The unit of chloride level, eg. "mmol/L", "mEq/L", and so on.
            - "bicarbonate" (array): The patient's bicarbonate level in the format (value, unit).
                - Value (float): The value of bicarbonate level.
                - Unit (str): The unit of bicarbonate level, eg. "mmol/L", "mEq/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's anion gap.

    Notes:
        - None

    Example:
        compute_anion_gap_explanation({'chloride': [106.0, 'mEq/L'],'bicarbonate': [20.0, 'mEq/L'],'sodium': [140.0, 'mEq/L']})
        output: "{'Explanation': "The formula for computing a patient's anion gap is:
        sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\nThe concentration of sodium is 140.0 mEq/L.
        \nThe concentration of chloride is 106.0 mEq/L. \nThe concentration of bicarbonate is 20.0 mEq/L.
        \nPlugging in these values into the anion gap formula gives us 140.0 mEq/L - (106.0 mEq/L + 20.0 mEq/L) = 14.0 mEq/L.
        Hence, The patient's anion gap is 14.0 mEq/L.\n", 'Answer': 14.0}"
    """

    explanation = ""
    explanation += "The formula for computing a patient's anion gap is: " \
                   "sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\n"

    sodium = input_parameters["sodium"]
    chloride = input_parameters["chloride"]
    bicarbonate = input_parameters["bicarbonate"]

    sodium_exp, sodium = conversion_explanation(
        sodium[0], "sodium", 22.99, 1, sodium[1], "mEq/L"
    )
    chloride_exp, chloride = conversion_explanation(
        chloride[0], "chloride", 35.45, 1, chloride[1], "mEq/L"
    )
    bicarbonate_exp, bicarbonate = conversion_explanation(
        bicarbonate[0], "bicarbonate", 61.02, 1, bicarbonate[1], "mEq/L"
    )

    explanation += sodium_exp + "\n"
    explanation += chloride_exp + "\n"
    explanation += bicarbonate_exp + "\n"

    answer = round_number(sodium - (chloride + bicarbonate))

    explanation += f"Plugging in these values into the anion gap formula gives us " \
                   f"{sodium} mEq/L - ({chloride} mEq/L + {bicarbonate} mEq/L) = {answer} mEq/L. "
    explanation += f"Hence, The patient's anion gap is {answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": answer}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "sodium": (134.0, 'mmol/L'),
            "chloride": (109.0, 'mmol/L'),
            "bicarbonate": (21.0, 'mmol/L'),
        },
        {
            'chloride': (106.0, 'mEq/L'),
            'bicarbonate': (20.0, 'mEq/L'),
            'sodium': (140.0, 'mEq/L'),
        },
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_anion_gap_explanation(input_variables)
        print(result)
        print("-" * 50)
