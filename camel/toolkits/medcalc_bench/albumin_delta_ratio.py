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
- rewrite function compute_albumin_delta_ratio_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)
from albumin_corrected_delta_gap import (
    compute_albumin_corrected_delta_gap_explanation,
)


def compute_albumin_delta_ratio_explanation(input_parameters):
    r"""
    Calculates the patient's albumin delta ratio and generates a detailed explanatory text.

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
            - "Answer" (float): The patient's albumin delta ratio.

    Notes:
        - None

    Example:
        compute_albumin_delta_ratio_explanation({'chloride': (105.0, 'mEq/L'), 'bicarbonate': (28.0, 'mEq/L'),
        'albumin': (3.9, 'g/dL'), 'sodium': (140.0, 'mEq/L')})

        output: "{'Explanation': "The formula for computing the albumin corrected delta ratio is albumin corrected
        delta gap (mEq/L)/(24 - bicarbonate mEq/L).\nTo compute the formula of albumin corrected delta gap,
        the formula is albumin corrected anion gap (in mEq/L) - 12.\nThe formula for computing a patient's albumin
        corrected anion gap is: anion_gap (in mEq/L) + 2.5 * (4 - albumin (in g/dL)).\nThe formula for computing a
        patient's anion gap is: sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\nThe concentration of
        sodium is 140.0 mEq/L. \nThe concentration of chloride is 105.0 mEq/L. \nThe concentration of bicarbonate is
        28.0 mEq/L. \nPlugging in these values into the anion gap formula gives us 140.0 mEq/L - (105.0 mEq/L + 28.0
        mEq/L) = 7.0 mEq/L. Hence, The patient's anion gap is 7.0 mEq/L.\nThe concentration of albumin is 3.9 g/dL.
        Plugging in these values into the albumin corrected anion gap formula, we get 7.0 (mEq/L) + 2.5 * (4 - 3.9 (
        in g/dL)) = 7.25 mEq/L. Hence, the patient's albumin corrected anion gap is 7.25 mEq/L.\nPlugging in 7.25
        mEq/L for the anion gap into the albumin corrected delta gap formula, we get 7.25 - 12 = -4.75 mEq/L. Hence,
        the patient's albumin corrected delta gap is -4.75 mEq/L.\nPlugging in the albumin corrected delta gap and
        the bicarbonate concentration into the albumin corrected delta ratio formula, we get -4.75 mEq/L / -4.0 mEq/L =
        1.188. The patient's albumin corrected delta ratio is 1.188.\n", 'Answer': 1.188}"
    """

    albumin_delta_gap_resp = compute_albumin_corrected_delta_gap_explanation(input_parameters)

    bicarbonate_exp, bicarbonate_val = conversion_explanation(input_parameters["bicarbonate"][0], "bicarbonate",
                                                              61.02, 1, input_parameters["bicarbonate"][1], "mEq/L")

    explanation = f"The formula for computing the albumin corrected delta ratio is albumin corrected delta gap (" \
                  f"mEq/L)/(24 - bicarbonate mEq/L).\n"

    albmin_corrected_delta_gap_val = albumin_delta_gap_resp["Answer"]

    explanation += f"{albumin_delta_gap_resp['Explanation']}"

    final_answer = round_number(albumin_delta_gap_resp['Answer']/(24 - bicarbonate_val))

    explanation += f"Plugging in the albumin corrected delta gap and the bicarbonate concentration into the albumin " \
                   f"corrected delta ratio formula, we get {albmin_corrected_delta_gap_val} mEq/L / " \
                   f"{24 - bicarbonate_val} mEq/L = {final_answer}. "
    explanation += f"The patient's albumin corrected delta ratio is {final_answer}.\n"

    return {"Explanation": explanation, "Answer": final_answer}
 

if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "chloride": (100.0, "mmol/L"),
            "bicarbonate": (19.0, "mmol/L"),
            "albumin": (4.4, "g/dL"),
            "sodium": (134.0, "mmol/L"),
        },
        {
            "chloride": (105.0, "mEq/L"),
            "bicarbonate": (28.0, "mEq/L"),
            "albumin": (3.9, "g/dL"),
            "sodium": (140.0, "mEq/L"),
        },
    ]

    # {'Chloride': [100.0, 'mmol/L'], 'Albumin': [4.4, 'g/dL'], 'Bicarbonate': [19.0, 'mmol/L'], 'Sodium': [134.0, 'mmol/L']}
    # {'Chloride': [105.0, 'mEq/L'], 'Albumin': [3.9, 'g/dL'], 'Bicarbonate': [28.0, 'mEq/L'], 'Sodium': [140.0, 'mEq/L']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_albumin_delta_ratio_explanation(input_variables)
        print(result)
        print("-" * 50)
