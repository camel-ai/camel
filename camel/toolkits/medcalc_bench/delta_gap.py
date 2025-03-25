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
- rewrite function compute_delta_gap_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.anion_gap import (
    compute_anion_gap_explanation,
)
from camel.toolkits.medcalc_bench.utils.rounding import round_number


def compute_delta_gap_explanation(input_parameters):
    """
    Calculates the patient's delta gap and generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following key-value pairs:
            - "sodium" (tuple): The patient's blood sodium level in the format (value, unit).
                - Value (float): The blood sodium level.
                - Unit (str): The unit of blood sodium level.
            - "chloride" (tuple): The patient's chloride level in the format (value, unit).
                - Value (float): The value of chloride level.
                - Unit (str): The unit of chloride level, eg. "mmol/L", "mEq/L", and so on.
            - "bicarbonate" (tuple): The patient's bicarbonate level in the format (value, unit).
                - Value (float): The value of bicarbonate level.
                - Unit (str): The unit of bicarbonate level, eg. "mmol/L", "mEq/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's delta gap.

    Notes:
        - Uses the `compute_anion_gap_explanation` function to compute anion gap.

    Example:
        compute_delta_gap_explanation({"chloride": (100.0, "mEq/L"),"bicarbonate": (19.0, "mEq/L"),"sodium": (135.0, "mEq/L")})
        output: "{'Explanation': "To compute the formula of the delta gap, the formula is anion gap (in mEq/L) - 12. The first step is to compute the patient's anion gap.\nThe formula for computing a patient's anion gap is: sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\nThe concentration of sodium is 135.0 mEq/L. \nThe concentration of chloride is 100.0 mEq/L. \nThe concentration of bicarbonate is 19.0 mEq/L. \nPlugging in these values into the anion gap formula gives us 135.0 mEq/L - (100.0 mEq/L + 19.0 mEq/L) = 16.0 mEq/L. Hence, The patient's anion gap is 16.0 mEq/L.\nPlugging in 16.0 mEq/L for the delta gap formula, we get 16.0 - 12 = 4.0 mEq/L. Hence, the patient's delta gap is 4.0 mEq/L.\n", 'Answer': 4.0}"
    """

    explanation = "To compute the formula of the delta gap, the formula is anion gap (in mEq/L) - 12. The first step is to compute the patient's anion gap.\n"

    anion_gap_resp = compute_anion_gap_explanation(input_parameters)

    explanation += anion_gap_resp["Explanation"]

    anion_gap_val = anion_gap_resp["Answer"]

    answer = round_number(anion_gap_val - 12.0)

    explanation += f"Plugging in {anion_gap_val} mEq/L for the delta gap formula, we get {anion_gap_val} - 12 = {answer} mEq/L. "
    explanation += f"Hence, the patient's delta gap is {answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": answer}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "chloride": (100.0, "mEq/L"),
            "bicarbonate": (19.0, "mEq/L"),
            "sodium": (135.0, "mEq/L"),
        },
        {
            "chloride": (102.0, "mEq/L"),
            "bicarbonate": (22.0, "mEq/L"),
            "sodium": (137.0, "mEq/L"),
        },
    ]

    # {'Chloride': [100.0, 'mEq/L'], 'Bicarbonate': [19.0, 'mEq/L'], 'Sodium': [135.0, 'mEq/L']}
    # {'Chloride': [102.0, 'mEq/L'], 'Bicarbonate': [22.0, 'mEq/L'], 'Sodium': [137.0, 'mEq/L']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_delta_gap_explanation(input_variables)
        print(result)
        print("-" * 50)
