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
- rewrite function compute_albumin_corrected_anion_explanation
- translation

Date: March 2025
"""

import anion_gap
from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_albumin_corrected_anion_explanation(input_parameters):
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
            - "albumin" (array): The patient's albumin concentration in the format (value, unit).
                - Value (float): The numerical albumin concentration value.
                - Unit (str): The unit of albumin concentration, eg. "g/L", "mg/dL", "g/mL" and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's anion gap.

    Notes:
        - None

    Example:
        compute_albumin_corrected_anion_explanation({'chloride': [100.0, 'mmol/L'], 'bicarbonate': (19.0, 'mmol/L'),
        'albumin': [4.4, 'g/dL'], 'sodium': [134.0, 'mmol/L']})

        output: "{'Explanation': "The formula for computing a patient's albumin corrected anion gap is:
        anion_gap (in mEq/L) + 2.5 * (4 - albumin (in g/dL)).\nThe formula for computing a patient's anion gap is:
        sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\nThe concentration of sodium is 134.0 mmol/L. We
        need to convert the concentration to mEq/L. Let's first convert the mass of sodium from mmol to mEq.
        The mass of sodium is 134.0 mmol. The compound, sodium, has a valence of 1, and so multiply the valence by
        the value of mmol to get, 134.0 mmol * 1 mEq/mmol = 134.0 mEq sodium. The volume units is L so no volume
        conversion is needed. Hence, the concentration value of 134.0 mmol sodium/L converts to 134.0 mEq sodium/L.
        \nThe concentration of chloride is 100.0 mmol/L. We need to convert the concentration to mEq/L. Let's first
        convert the mass of chloride from mmol to mEq. The mass of chloride is 100.0 mmol. The compound, chloride,
        has a valence of 1, and so multiply the valence by the value of mmol to get, 100.0 mmol * 1 mEq/mmol = 100.0
        mEq chloride. The volume units is L so no volume conversion is needed. Hence, the concentration value of
        100.0 mmol chloride/L converts to 100.0 mEq chloride/L. \nThe concentration of bicarbonate is 19.0 mmol/L.
        We need to convert the concentration to mEq/L. Let's first convert the mass of bicarbonate from mmol to mEq.
        The mass of bicarbonate is 19.0 mmol. The compound, bicarbonate, has a valence of 1, and so multiply the
        valence by the value of mmol to get, 19.0 mmol * 1 mEq/mmol = 19.0 mEq bicarbonate. The volume units is L so
        no volume conversion is needed. Hence, the concentration value of 19.0 mmol bicarbonate/L converts to 19.0
        mEq bicarbonate/L. \nPlugging in these values into the anion gap formula gives us 134.0 mEq/L - (100.0 mEq/L
        + 19.0 mEq/L) = 15.0 mEq/L. Hence, The patient's anion gap is 15.0 mEq/L.\nThe concentration of albumin is
        4.4 g/dL. Plugging in these values into the albumin corrected anion gap formula, we get 15.0 (mEq/L) + 2.5 *
        (4 - 4.4 (in g/dL)) = 14.0 mEq/L. Hence, the patient's albumin corrected anion gap is 14.0 mEq/L.\n",
        'Answer': 14.0}"
    """

    explanation = "The formula for computing a patient's albumin corrected anion gap is: " \
                  "anion_gap (in mEq/L) + 2.5 * (4 - albumin (in g/dL)).\n"

    anion_gap_data = anion_gap.compute_anion_gap_explanation(input_parameters)

    explanation += anion_gap_data["Explanation"]

    albumin_exp, albumin = conversion_explanation(input_parameters["albumin"][0], "albumin", None, None,
                                                  input_parameters["albumin"][1], "g/dL")

    explanation += albumin_exp

    anion_gap_val = anion_gap_data["Answer"]
    answer = anion_gap_val + 2.5 * (4 - albumin) 
    final_answer = round_number(answer)

    explanation += f"Plugging in these values into the albumin corrected anion gap formula, we get {anion_gap_val} (" \
                   f"mEq/L) + 2.5 * (4 - {albumin} (in g/dL)) = {final_answer} mEq/L. "

    explanation += f"Hence, the patient's albumin corrected anion gap is {final_answer} mEq/L.\n"

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
            "chloride": (89.0, "mmol/L"),
            "bicarbonate": (23.7, "mEq/L"),
            "albumin": (2.1, "g/dL"),
            "sodium": (133.0, "mmol/L"),
        },
    ]

    # {'Chloride': [100.0, 'mmol/L'], 'Albumin': [4.4, 'g/dL'], 'Bicarbonate': [19.0, 'mmol/L'], 'Sodium': [134.0, 'mmol/L']}
    # {'Chloride': [89.0, 'mmol/L'], 'Albumin': [2.1, 'g/dL'], 'Bicarbonate': [23.7, 'mEq/L'], 'Sodium': [133.0, 'mmol/L']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_albumin_corrected_anion_explanation(input_variables)
        print(result)
        print("-" * 50)
