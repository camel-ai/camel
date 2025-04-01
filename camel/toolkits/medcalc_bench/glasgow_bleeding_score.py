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
- rewrite function glasgow_bleeding_score_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def glasgow_bleeding_score_explanation(input_parameters):
    explanation = r"""
    The Glasgow-Blatchford Score (GBS) for assessing the severity of 
    gastrointestinal bleeding is shown below:

       1. Hemoglobin level (g/dL): Enter value (norm: 12-17 g/dL)
       2. BUN level (mg/dL): Enter value (norm: 8-20 mg/dL)
       3. Initial systolic blood pressure (mm Hg): Enter value (norm: 
       100-120 mm Hg)
       4. Sex: Female = +1 point, Male = 0 points
       5. Heart rate ≥100: No = 0 points, Yes = +1 point
       6. Melena present: No = 0 points, Yes = +1 point
       7. Recent syncope: No = 0 points, Yes = +2 points
       8. Hepatic disease history: No = 0 points, Yes = +2 points
       9. Cardiac failure present: No = 0 points, Yes = +2 points
    
    The total score is calculated by summing the points for each criterion (
    additional lab values may also be factored into the score).\n\n
    """

    score = 0

    hemoglobin_exp, hemoglobin = conversion_explanation(
        input_parameters["hemoglobin"][0],
        "hemoglobin",
        64500,
        None,
        input_parameters["hemoglobin"][1],
        "g/dL",
    )
    bun_exp, bun = conversion_explanation(
        input_parameters["bun"][0],
        "BUN",
        28.08,
        None,
        input_parameters["bun"][1],
        "mg/dL",
    )
    gender = input_parameters["sex"]
    systiolic_bp = input_parameters["sys_bp"][0]
    heart_rate = input_parameters["heart_rate"][0]

    explanation += (
        f"The current glasgow bleeding score is 0. The patient's "
        f"gender is {gender}.\n"
    )
    explanation += hemoglobin_exp

    if gender == "Male":
        if 12 < hemoglobin <= 13:
            explanation += (
                f"Because the patient is a male and the "
                f"hemoglobin concentration is between 12 and 13 "
                f"g/dL, we add one point, making the current "
                f"score {score} + 1 = {score + 1}.\n"
            )
            score += 1
        elif 10 <= hemoglobin < 12:
            explanation += (
                f"Because the patient is a male and the "
                f"hemoglobin concentration is between 10 and 12 "
                f"g/dL, we add three points, making the current "
                f"score {score} + 3 = {score + 3}.\n"
            )
            score += 3
        elif hemoglobin < 10:
            explanation += (
                f"Because the patient is a male and the "
                f"hemoglobin concentration is less than "
                f"10 and 12 g/dL, we add six points, "
                f"making the current score "
                f"{score} + 6 = {score + 6}.\n"
            )
            score += 6
        elif hemoglobin > 13:
            explanation += (
                f"Because the patient is a male and the "
                f"hemoglobin concentration is greater than 13 "
                f"g/dL, we do not add any points, "
                f"keeping the current score at {score}.\n"
            )

    else:
        if 10 < hemoglobin <= 12:
            explanation += (
                f"Because the patient is a female "
                f"and the hemoglobin concentration is between 10 "
                f"and 12 mg/dL, we add one point, making the "
                f"current score {score} + 1 = {score + 1}.\n"
            )
            score += 1
        elif hemoglobin < 10:
            explanation += (
                f"Because the patient is a female and the "
                f"hemoglobin concentration is less "
                f"than 10 mg/dL, we add three points, "
                f"making the current score "
                f"{score} + 3 = {score + 3}.\n"
            )
            score += 6
        elif hemoglobin > 12:
            explanation += (
                f"Because the patient is a female and the "
                f"hemoglobin concentration is greater than 12 "
                f"mg/dL, we do not add any points, keeping the "
                f"current score at {score}.\n"
            )

    explanation += bun_exp

    if 18.2 <= bun < 22.4:
        explanation += (
            f"The BUN concentration is between 18.2 and 22.4 "
            f"mg/dL, and so we add two points, "
            f"making the current score "
            f"{score} + 2 = {score + 2}.\n"
        )
        score += 2
    elif 22.4 <= bun < 28:
        explanation += (
            f"The BUN concentration is between "
            f"22.4 and 28 mg/dL, and so we add three points, "
            f"making the current score "
            f"{score} + 3 = {score + 3}.\n"
        )
        score += 3
    elif 28 <= bun < 70:
        explanation += (
            f"The BUN concentration is between 28 and 70 mg/dL, "
            f"and so we add four points, making the current score"
            f" {score} + 4 = {score + 4}.\n"
        )
        score += 4
    elif bun > 70:
        explanation += (
            f"The BUN concentration is greater than 70 mg/dL, "
            f"and so we add six points, making the current score"
            f" {score} + 6 = {score + 6}.\n"
        )
        score += 6
    elif bun < 18.2:
        explanation += (
            f"The BUN concentration is less than 18.2 mg/dL, "
            f"and so we do not make any changes to the score, "
            f"keeping the score at {score}.\n"
        )

    explanation += f"The patient's blood pressure is {systiolic_bp} mm Hg. "

    if 100 <= systiolic_bp < 110:
        explanation += (
            f"Because the patient's systolic blood pressure is "
            f"between 100 and 110 mm Hg, we increase the "
            f"score by one point, making the current score "
            f"{score} + 1 = {score + 1}.\n"
        )
        score += 1
    elif 90 <= systiolic_bp < 100:
        explanation += (
            f"Because the patient's systolic blood pressure is "
            f"between 90 and 100 mm Hg, we increase the score by "
            f"two points, making the current score "
            f"{score} + 2 = {score + 2}.\n"
        )
        score += 2
    elif systiolic_bp < 90:
        explanation += (
            f"Because the patient's systolic blood pressure is "
            f"less than 90 mm Hg, we increase the score by three "
            f"points, making the current score "
            f"{score} + 3 = {score + 3}.\n"
        )
        score += 3
    elif systiolic_bp >= 110:
        explanation += (
            f"Because the patient's systolic blood pressure is "
            f"greater than or equal to 110 mm Hg, we do not add "
            f"points to the score, keeping the current score at"
            f" {score} + 3 = {score + 3}.\n"
        )

    explanation += (
        f"The patient's heart rate is {heart_rate} beats per " f"minute. "
    )

    if heart_rate >= 100:
        explanation += (
            f"Because the heart rate is greater or equal to than "
            f"100 beats per minute, we increase the score by one "
            f"point, making the current score {score} + 1 ="
            f" {score + 1}.\n"
        )
        score += 1
    else:
        explanation += (
            f"Because the heart rate is less than 100 beats per "
            f"minute, we do not change the score, keeping the "
            f"current score at {score}.\n"
        )

    default_parameters = {
        "melena_present": "melena",
        "syncope": "recent syncope",
        "hepatic_disease_history": "hepatic disease history",
        "cardiac_failure": "cardiac failure",
    }

    for parameter in default_parameters:
        if parameter not in input_parameters:
            explanation += (
                f"The patient's status for"
                f" {default_parameters[parameter]} is missing "
                f"from the patient note and so we assume it is "
                f"absent from the patient.\n"
            )
            input_parameters[parameter] = False
            explanation += (
                f"Hence, we do not add any points to the score, "
                f"keeping it at {score}.\n"
            )

        elif (
            parameter
            in ['syncope', 'hepatic_disease_history', 'cardiac_failure']
            and input_parameters[parameter]
        ):
            explanation += (
                f"The patient has a"
                f" {default_parameters[parameter]}, and so we "
                f"add two points to the current total, "
                f"making the current total "
                f"{score} + 2 =  {score + 2}.\n"
            )
            score += 2

        elif input_parameters[parameter]:
            explanation += (
                f"The patient has "
                f"{default_parameters[parameter]} and so we add "
                f"one point to the current total, making the "
                f"current total {score} + 1 =  {score + 1}.\n"
            )
            score += 1

        else:
            explanation += (
                f"The patient's status for "
                f"{default_parameters[parameter]} is reported to "
                f"be absent for the patient, and "
                f"so we do not add any points, "
                f"keeping the current total at {score}.\n"
            )

    explanation += f"The patient's Glasgow Bleeding Score is {score}.\n"

    return {"Explanation": explanation, "Answer": score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "hemoglobin": (12, 'g/dL'),
            "bun": (10, 'mg/dL'),
            "sys_bp": (70, "mm"),
            "sex": "Male",
            "heart_rate": (92.0, "breaths per minute"),
            "platelet_count": (277000.0, 'µL'),
            "melena_present": False,
            "syncope": False,
            "hepatic_disease_history": False,
            "cardiac_failure": False,
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = glasgow_bleeding_score_explanation(input_variables)
        print(result)
        print("-" * 50)
