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
- rewrite function compute_albumin_corrected_delta_gap_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from albumin_corrected_anion import (
    compute_albumin_corrected_anion_explanation,
)


def compute_albumin_corrected_delta_gap_explanation(input_parameters):
    r"""
    Calculates the patient's albumin corrected delta gap and generates a detailed explanatory text.

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
            - "albumin" (array): The patient's albumin concentration in the format (value, unit).
                - Value (float): The numerical albumin concentration value.
                - Unit (str): The unit of albumin concentration, eg. "g/L", "mg/dL", "g/mL" and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's albumin corrected delta gap.

    Notes:
        - None

    Example:
        compute_albumin_corrected_delta_gap_explanation()

        output: "{'Explanation': "To compute the formula of albumin corrected delta gap, the formula is albumin
        corrected anion gap (in mEq/L) - 12.\nThe formula for computing a patient's albumin corrected anion gap is:
        anion_gap (in mEq/L) + 2.5 * (4 - albumin (in g/dL)).\nThe formula for computing a patient's anion gap is:
        sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\nThe concentration of sodium is 141.0 mEq/L. \nThe
        concentration of chloride is 104.0 mEq/L. \nThe concentration of bicarbonate is 29.0 mEq/L. \nPlugging in
        these values into the anion gap formula gives us 141.0 mEq/L - (104.0 mEq/L + 29.0 mEq/L) = 8.0 mEq/L.
        Hence, The patient's anion gap is 8.0 mEq/L.\nThe concentration of albumin is 43.0 g/L. We need to convert
        the concentration to g/dL. The mass units of the source and target are the same so no conversion is needed.
        The current volume unit is L and the target volume unit is dL. The conversion factor is 10.0 dL for every
        unit of L. Our next step will be to divide the mass by the volume conversion factor of 10.0 to get the final
        concentration in terms of g/dL. This will result to 43.0 g albumin/10.0 dL = 4.3 g albumin/dL. The
        concentration value of 43.0 g albumin/L converts to 4.3 g albumin/dL. Plugging in these values into the
        albumin corrected anion gap formula, we get 8.0 (mEq/L) + 2.5 * (4 - 4.3 (in g/dL)) = 7.25 mEq/L. Hence,
        the patient's albumin corrected anion gap is 7.25 mEq/L.\nPlugging in 7.25 mEq/L for the anion gap into the
        albumin corrected delta gap formula, we get 7.25 - 12 = -4.75 mEq/L. Hence, the patient's albumin corrected
        delta gap is -4.75 mEq/L.\n", 'Answer': -4.75}"
    """

    explanation = f"To compute the formula of albumin corrected delta gap, " \
                  f"the formula is albumin corrected anion gap (in mEq/L) - 12.\n"

    albumin_corrected_resp = compute_albumin_corrected_anion_explanation(input_parameters)

    explanation += albumin_corrected_resp["Explanation"]

    albumin_corrected_val = albumin_corrected_resp["Answer"]

    answer = round_number(albumin_corrected_val - 12.0)

    explanation += f"Plugging in {albumin_corrected_val} mEq/L for the anion gap into " \
                   f"the albumin corrected delta gap formula, we get {albumin_corrected_val} - 12 = {answer} mEq/L. "
    explanation += f"Hence, the patient's albumin corrected delta gap is {answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": answer}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "chloride": (104.0, "mEq/L"),
            "bicarbonate": (29.0, "mEq/L"),
            "albumin": (43.0, "g/L"),
            "sodium": (141.0, "mEq/L"),
        },
        {
            "chloride": (89.0, "mmol/L"),
            "bicarbonate": (23.7, "mEq/L"),
            "albumin": (2.1, "g/dL"),
            "sodium": (133.0, "mmol/L"),
        },
    ]

    # {'Chloride': [104.0, 'mEq/L'], 'Albumin': [43.0, 'g/L'], 'Bicarbonate': [29.0, 'mEq/L'], 'Sodium': [141.0, 'mEq/L']}
    # {'Chloride': [89.0, 'mmol/L'], 'Albumin': [2.1, 'g/dL'], 'Bicarbonate': [23.7, 'mEq/L'], 'Sodium': [133.0, 'mmol/L']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_albumin_corrected_delta_gap_explanation(input_variables)
        print(result)
        print("-" * 50)
