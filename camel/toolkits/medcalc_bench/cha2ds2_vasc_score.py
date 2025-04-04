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
- rewrite function compute_cci_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)


def generate_cha2ds2_vasc_explanation(params):
    score = 0

    output = """
    The criteria for the CHA2DS2-VASc score are listed below:

    1. Age: < 65 years = 0 points, 65-74 years = +1 point, ≥ 75 years
        = +2 points
    2. Sex: Female = +1 point, Male = 0 points
    3. Congestive Heart Failure (CHF) history: No = 0 points, Yes = +1 point
    4. Hypertension history: No = 0 points, Yes = +1 point
    5. Stroke, Transient Ischemic Attack (TIA), or Thromboembolism history:
        No = 0 points, Yes = +2 points
    6. Vascular disease history (previous myocardial infarction, peripheral
        artery disease, or aortic plaque): No = 0 points, Yes = +1 point
    7. Diabetes history: No = 0 points, Yes = +1 point

    The CHA2DS2-VASc score is calculated by summing the points for each
        criterion.\n\n
    """

    output += "The current CHA2DS2-VASc score is 0.\n"

    text, age = age_conversion_explanation(params['age'])
    output += text

    # Age
    if age >= 75:
        output += (
            f"Because the age is greater than 74, two points added to "
            f"the score, making the current total {score} + 2 = "
            f"{score + 2}.\n"
        )
        score += 2
    elif age >= 65:
        output += (
            f"Because the age is between 65 and 74, one point added "
            f"to the score, making the current total {score} + 1 = "
            f"{score + 1}.\n"
        )
        score += 1
    else:
        output += (
            f"Because the age is less than 65 years, no points are "
            f"added to the current total, keeping the total at "
            f"{score}.\n"
        )

    sex = params['sex']  # Sex of the patient (Male/Female)

    output += f"The patient's gender is {sex.lower()} "

    if sex.lower() == 'female':
        output += (
            f"and so one point is added to the score, making the "
            f"current total {score} + 1 = {score + 1}.\n"
        )
        score += 1
    else:
        output += (
            f"and so no points are added to the current total, "
            f"keeping the total at {score}.\n"
        )

    # Congestive Heart Failure
    if 'chf' in params:
        chf = params['chf']
        output += (
            f"The patient history for congestive heart failure is "
            f"{'present' if chf else 'absent'}. "
        )
    else:
        chf = False
        output += (
            "Because the congestive heart failure history is not "
            "specified in the patient note, we assume it is absent "
            "from the patient. "
        )

    # Congestive Heart Failure (CHF)
    if chf:
        output += (
            f"Because the patient has congestive heart failure, "
            f"one point is added to the score, making the current "
            f"total {score} + 1 = {score + 1}.\n"
        )
        score += 1
    else:
        output += (
            f"Because the patient does not have congestive heart "
            f"failure, no points are added to the current total, "
            f"keeping the total at {score}.\n"
        )

    # Hypertension
    if 'hypertension' in params:
        hypertension = params['hypertension']
        output += (
            f"The patient history for hypertension is "
            f"{'present' if hypertension else 'absent'}. "
        )
    else:
        hypertension = False
        output += (
            "Because hypertension history is not specified in the "
            "patient note, we assume that it is absent from the "
            "patient. "
        )

    # Congestive Heart Failure (CHF)
    if hypertension:
        output += (
            f"Because the patient has hypertension, one point is "
            f"added to the score, making the current "
            f"total {score} + 1 = {score + 1}.\n"
        )
        score += 1
    else:
        output += (
            f"Because the patient does not have hypertension, "
            f"no points are added to the current total, "
            f"keeping the total at {score}.\n"
        )

    output += (
        "One criteria of the CHA2DS2-VASc score is to check "
        "if the patient has had any history of stroke, transient "
        "ischemic attacks (TIA), or thromboembolism. "
    )

    if 'stroke' in params:
        stroke = params['stroke']
        output += (
            f"Based on the patient note, the patient history for "
            f"stroke is {'present' if stroke else 'absent'}. "
        )
    else:
        stroke = False
        output += (
            "Because stroke history is not specified in the patient "
            "note, we assume that it is absent from the patient. "
        )

    if 'tia' in params:
        tia = params['tia']
        output += (
            f"Based on the patient note, the patient history for tia "
            f"is {'present' if tia else 'absent'}. "
        )
    else:
        tia = False
        output += (
            "Because tia history is not specified in the patient "
            "note, we assume that it is absent from the patient. "
        )

    if 'thromboembolism' in params:
        thromboembolism = params['thromboembolism']
        output += (
            f"Based on the patient note, the patient history for "
            f"thromboembolism is "
            f"{'present' if thromboembolism else 'absent'}. "
        )
    else:
        thromboembolism = False
        output += (
            "Because thromboembolism history is not specified in the "
            "patient note, we assume it to be absent. "
        )

    # Stroke / TIA / Thromboembolism
    if stroke or tia or thromboembolism:
        output += (
            f"Because at least one of stroke, tia, or thromboembolism "
            f"is present, two points are added to the score, making "
            f"the current total {score} + 2 = {score + 2}.\n"
        )
        score += 2
    else:
        output += (
            f"Because all of stroke, tia, or thromboembolism are "
            f"absent, no points are added to score, keeping the score "
            f"at {score}.\n"
        )

    if 'vascular_disease' in params:
        vascular_disease = params['vascular_disease']
        output += (
            f"Based on the patient note, the patient history for "
            f"vascular disease is "
            f"{'present' if vascular_disease else 'absent'}. "
        )
    else:
        vascular_disease = False
        output += (
            "Because vascular disease history is not specified "
            "in the patient note, we assume it to be absent.\n"
        )

    if vascular_disease:
        output += (
            f"Because the patient has vascular disease, one point is "
            f"added to the score, making the current "
            f"total {score} + 1 = {score + 1}. "
        )
        score += 1
    else:
        output += (
            f"Because the patient does not have vascular disease, "
            f"no points are added to score, keeping the score at "
            f"{score}. "
        )

    if 'diabetes' in params:
        diabetes = params['diabetes']
        output += (
            f"Based on the patient note, the patient history for "
            f"diabetes is {'present' if diabetes else 'absent'}. "
        )
    else:
        diabetes = False
        output += (
            "Because diabetes history is not specified in the "
            "patient note, we assume it's value as 'absent'. "
        )

    if diabetes:
        output += (
            f"Because the patient has diabetes, one point "
            f"is added to the score, making the current total {score} "
            f"+ 1 = {score + 1}.\n"
        )
        score += 1
    else:
        output += (
            f"Because the patient does not have diabetes, "
            f"no points are added to score, keeping the score at "
            f"{score}.\n"
        )

    output += f"The patient's CHA2DS2-VASc Score is {score}.\n"

    return {"Explanation": output, "Answer": score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            'sex': 'Male',
            'thromboembolism': True,
            'tia': True,
            'hypertension': True,
            'age': (78, 'years'),
            'stroke': True,
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = generate_cha2ds2_vasc_explanation(input_variables)
        print(result)
        print("-" * 50)
