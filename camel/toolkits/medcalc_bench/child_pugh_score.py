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
- rewrite function compute_child_pugh_score_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_child_pugh_score_explanation(input_variables):
    r"""
    Calculates the patient's child pugh score and generates a detailed
    explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following
        key-value pairs:
            - "inr" (float): The patient's international normalised ratio (
            INR) in the float format.
            - "albumin" (tuple): The patient's albumin concentration in the
            format (value, unit).
                - Value (float): The numerical albumin concentration value.
                - Unit (str): The unit of albumin concentration, eg. "g/L",
                "mg/dL", "g/mL" and so on.
            - "bilirubin" (array): The patient's bilirubin level in the
            format (value, unit).
                - Value (float): The value of bilirubin level.
                - Unit (str): The unit of bilirubin level, eg. "mmol/L",
                "mEq/L", and so on.
            - "ascites" (str): The patient's ascites level.
                - Absent
                - Slight
                - Moderate
            - "encephalopathy" (str): Whether the patient has encephalopathy.
                - No Encephalopathy
                - Grade 1-2
                - Grade 3-4

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's child pugh score.

    Notes:
        - None

    Example:
        compute_child_pugh_score_explanation({'bilirubin': (2.8, 'mg/dL'),
        'albumin': (2.1, 'g/dL'),
        'inr': 1.5,
        'ascites': 'Absent',
        'encephalopathy': 'Grade 1-2'})

        output: "{'Explanation': "\n    The criteria for the Child-PughScore
        are listed below:\n\n    1. Bilirubin (Total): <2 mg/dL (<34.2
        μmol/L) = +1 point, 2-3 mg/dL (34.2-51.3μmol/L) = +2 points,
        \n    >3 mg/dL (>51.3μmol/L) = +3 points\n    2. Albumin: >3.5 g/dL
        (>35 g/L) = +1 point,2.8-3.5 g/dL (28-35 g/L) = +2 points,<2.8 g/dL
        (<28 g/L) = +3 points\n    3. INR: <1.7 = +1 point,1.7-2.3 = +2
        points, >2.3 = +3 points\n    4.Ascites: Absent = +1 point, Slight
        = +2 points, Moderate = +3points\n    5. Encephalopathy:
        NoEncephalopathy = +1 point, Grade 1-2 = +2 points, Grade 3-4 =
        +3points\n\n    The Child-Pugh Score iscalculated by summing the
        points for each criterion.\\n\\n\n    Thecurrent child pugh score is 0.
        \nThepatient's INR is 1.5. Because the INR is less than 1.7, we add
        1 tothe score, making the current total0 + 1 = 1.\nThe concentration
        of bilirubin is 2.8 mg/dL. Because the Bilirubin concentration is
        between 2mg/dL and 3 mg/dL, we add 2 to the score, making the
        current total 1 + 2 = 3.\nThe concentration of albuminis 2.1 g/dL.
        Because the Albumin concentration is less than 2.8 g/dL, we add 3 to
        the score, making thecurrent total 3 + 3 = 6.\nAscites is reported
        to be 'absent' and so we add 1 point to the score, making thecurrent
        total 6 + 1 = 7.\nEncephalopathy state is 'Grade 1-2 encephalopathy'
        and so we add two points to thescore, making the current total 7 + 2 =
        9.\nThe patient's child pugh score is 9.\n", 'Answer': 9}"
    """

    cp_score = 0

    explanation = r"""
    The criteria for the Child-Pugh Score are listed below:

    1. Bilirubin (Total): <2 mg/dL (<34.2 μmol/L) = +1 point, 2-3 mg/dL
        (34.2-51.3 μmol/L) = +2 points, >3 mg/dL (>51.3 μmol/L) = +3 points
    2. Albumin: >3.5 g/dL (>35 g/L) = +1 point, 2.8-3.5 g/dL (28-35 g/L)
        = +2 points, <2.8 g/dL (<28 g/L) = +3 points
    3. INR: <1.7 = +1 point, 1.7-2.3 = +2 points, >2.3 = +3 points
    4. Ascites: Absent = +1 point, Slight = +2 points, Moderate = +3 points
    5. Encephalopathy: No Encephalopathy = +1 point, Grade 1-2 = +2 points,
        Grade 3-4 = +3 points

    The Child-Pugh Score is calculated by summing
    the points for each criterion.\n\n
    """

    explanation += "The current child pugh score is 0.\n"

    inr = input_variables['inr']

    ascites_state = input_variables.get('ascites', 'Absent')
    encephalopathy_state = input_variables.get(
        'encephalopathy', 'No Encephalopathy'
    )

    explanation += f"The patient's INR is {inr}. "
    bilirubin_exp, bilirubin = conversion_explanation(
        input_variables['bilirubin'][0],
        'bilirubin',
        548.66,
        None,
        input_variables['bilirubin'][1],
        "mg/dL",
    )

    albumin_exp, albumin = conversion_explanation(
        input_variables['albumin'][0],
        'albumin',
        66500,
        None,
        input_variables['albumin'][1],
        "g/dL",
    )

    # INR score calculation
    if inr < 1.7:
        explanation += (
            f"Because the INR is less than 1.7, we add 1 to the score, "
            f"making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        )
        cp_score += 1
    elif 1.7 <= inr <= 2.3:
        explanation += (
            f"Because the INR is between 1.7 and 2.3, "
            f"we add two to the score, making the current "
            f"total {cp_score} + 2 = {cp_score + 2}.\n"
        )
        cp_score += 2
    elif inr > 2.3:
        explanation += (
            f"Because the INR is greater than 2.3, we add three to the "
            f"score, making the current total"
            f" {cp_score} + 3 = {cp_score + 3}.\n"
        )
        cp_score += 3

    explanation += bilirubin_exp

    # Bilirubin score calculation
    if bilirubin < 2:
        explanation += (
            f"Because the Bilirubin concentration is less than 2 mg/dL, "
            f"we add 1 to the score, making the "
            f"current total {cp_score} + 1 = {cp_score + 1}.\n"
        )
        cp_score += 1
    elif 2 < bilirubin < 3:
        explanation += (
            f"Because the Bilirubin concentration is between 2 mg/dL and 3 "
            f"mg/dL, we add 2 to the score, "
            f"making the current total {cp_score} + 2 = {cp_score + 2}.\n"
        )
        cp_score += 2
    elif bilirubin >= 3:
        explanation += (
            f"Because the Bilirubin concentration is greater than 3 mg/dL, "
            f"we add 3 to the score, "
            f"making the current total {cp_score} + 3 = {cp_score + 3}.\n"
        )
        cp_score += 3

    explanation += albumin_exp

    # Albumin score calculation
    if albumin > 3.5:
        explanation += (
            f"Because the Albumin concentration is greater than 3.5 g/dL, "
            f"we add 1 to the score, "
            f"making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        )
        cp_score += 1
    elif 2.8 < albumin <= 3.5:
        explanation += (
            f"Because the Albumin concentration is between 2.8 g/dL and 3.5 "
            f"g/dL, we add 2 to the score, "
            f"making the current total {cp_score} + 2 = {cp_score + 2}.\n"
        )
        cp_score += 2
    elif albumin <= 2.8:
        explanation += (
            f"Because the Albumin concentration is less than 2.8 g/dL, "
            f"we add 3 to the score, making the "
            f"current total {cp_score} + 3 = {cp_score + 3}.\n"
        )
        cp_score += 3

    # Ascites score calculation
    if 'ascites' in input_variables:
        if input_variables['ascites'] == 'Absent':
            explanation += (
                f"Ascites is reported to be 'absent' and so we add 1 point "
                f"to the score, making the "
                f"current total {cp_score} + 1 = {cp_score + 1}.\n"
            )
            cp_score += 1
        elif ascites_state == 'Slight':
            explanation += (
                f"Ascites is reported to be 'slight' and so we add 2 points "
                f"to the score, making the "
                f"current total {cp_score} + 2 = {cp_score + 2}.\n"
            )
            cp_score += 2
        elif ascites_state == 'Moderate':
            explanation += (
                f"Ascites is reported to be 'moderate' and so we add 3 "
                f"points to the score, making the "
                f"current total {cp_score} + 3 = {cp_score + 3}.\n"
            )
            cp_score += 3
    else:
        explanation += (
            f"The Ascites state not specified, assuming and so we will "
            f"assume it to be absent. This means "
            f"we add 1 point to the score, making the current total"
            f" {cp_score} + 1 = {cp_score + 1}.\n"
        )
        cp_score += 1

    if 'encephalopathy' in input_variables:
        # Encephalopathy score calculation
        if encephalopathy_state == 'No Encephalopathy':
            explanation += (
                f"Encephalopathy state is reported to be "
                f"'no encephalopathy' and so we add one point to "
                f"the score, making the current total {cp_score} + 1 = "
                f"{cp_score + 1}.\n"
            )
            cp_score += 1
        elif encephalopathy_state == 'Grade 1-2':
            explanation += (
                f"Encephalopathy state is 'Grade 1-2 encephalopathy' and so "
                f"we add two points to the score, making the current total"
                f" {cp_score} + 2 = {cp_score + 2}.\n"
            )
            cp_score += 2
        elif encephalopathy_state == 'Grade 3-4':
            explanation += (
                f"Encephalopathy state is 'Grade 3-4 encephalopathy' and so "
                f"we add three points to the score, making the current total"
                f" {cp_score} + 3 = {cp_score + 3}.\n"
            )
            cp_score += 3
    else:
        explanation += (
            f"Encephalopathy state is not specified, and so we assume it's "
            f"value to be 'no encephalopathy.' We add one point to the "
            f"score, making the current total {cp_score} + 1 = "
            f"{cp_score + 1}.\n"
        )
        cp_score += 1

    explanation += f"The patient's child pugh score is {cp_score}.\n"

    return {"Explanation": explanation, "Answer": cp_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "bilirubin": (2.8, "mg/dL"),
            "albumin": (2.1, "g/dL"),
            "inr": 1.5,
            "ascites": "Absent",
            "encephalopathy": "Grade 1-2",
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_child_pugh_score_explanation(input_variables)
        print(result)
        print("-" * 50)
