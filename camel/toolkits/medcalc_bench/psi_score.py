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
- rewrite function psi_score_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.convert_temperature import (
    fahrenheit_to_celsius_explanation,
)
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def psi_score_explanation(input_variables):
    age_exp, age = age_conversion_explanation(input_variables["age"])
    gender = input_variables["sex"]
    pulse = input_variables["heart_rate"][0]
    temperature_exp, temperature = fahrenheit_to_celsius_explanation(
        input_variables["temperature"][0],
        input_variables["temperature"][1],
    )
    pH = input_variables["pH"]
    respiratory_rate = input_variables["respiratory_rate"][0]
    sys_bp = input_variables["sys_bp"][0]
    bun_exp, bun = conversion_explanation(
        input_variables["bun"][0],
        'BUN',
        28.02,
        None,
        input_variables["bun"][1],
        "mg/dL",
    )
    sodium_exp, sodium = conversion_explanation(
        input_variables["sodium"][0],
        "sodium",
        22.99,
        None,
        input_variables["sodium"][1],
        "mmol/L",
    )
    glucose_exp, glucose = conversion_explanation(
        input_variables["glucose"][0],
        "glucose",
        180.16,
        None,
        input_variables["glucose"][1],
        "mg/dL",
    )
    hemocratit = input_variables["hemocratit"][0]
    partial_pressure_oxygen = input_variables.get("partial_pressure_oxygen")

    explanation = """
    The rules for computing the Pneumonia Severity Index (PSI) are shown below:
    
       1. Age: Enter age in years (age score will be equal to age in years)
       2. Sex: Female = -10 points, Male = 0 points
       3. Nursing home resident: No = 0 points, Yes = +10 points
       4. Neoplastic disease: No = 0 points, Yes = +30 points
       5. Liver disease history: No = 0 points, Yes = +20 points
       6. Congestive heart failure (CHF) history: No = 0 points, Yes = +10 
       points
       7. Cerebrovascular disease history: No = 0 points, Yes = +10 points
       8. Renal disease history: No = 0 points, Yes = +10 points
       9. Altered mental status: No = 0 points, Yes = +20 points
       10. Respiratory rate ≥30 breaths/min: No = 0 points, Yes = +20 points
       11. Systolic blood pressure <90 mmHg: No = 0 points, Yes = +20 points
       12. Temperature <35°C (95°F) or >39.9°C (103.8°F): No = 0 points, 
       Yes = +15 points
       13. Pulse ≥125 beats/min: No = 0 points, Yes = +10 points
       14. pH <7.35: No = 0 points, Yes = +30 points
       15. BUN ≥30 mg/dL or ≥11 mmol/L: No = 0 points, Yes = +20 points
       16. Sodium <130 mmol/L: No = 0 points, Yes = +20 points
       17. Glucose ≥250 mg/dL or ≥14 mmol/L: No = 0 points, Yes = +10 points
       18. Hematocrit <30%: No = 0 points, Yes = +10 points
       19. Partial pressure of oxygen <60 mmHg or <8 kPa: No = 0 points, 
       Yes = +10 points
       20. Pleural effusion on x-ray: No = 0 points, Yes = +10 points
    
    The total score is calculated by summing the points for each criterion.\n\n
    """

    explanation += "The current PSI score is 0.\n"
    age_explanation, age = age_conversion_explanation(input_variables["age"])
    explanation += age_explanation
    explanation += (
        f"We add the the number of years of age of the "
        f"patient to the psi score, making the current "
        f"total 0 + {age} = {age}.\n"
    )

    psi_score = 0

    psi_score += age

    if gender == "Female":
        explanation += (
            f"Because the patient is female, we subtract "
            f"10 points from the current total, making the "
            f"current total {psi_score} - 10 "
            f"= {psi_score - 10}.\n"
        )
        psi_score -= 10
    else:
        explanation += (
            f"Because the patient is male, no adjustments "
            f"are made to the score, keeping the "
            f"current total at {psi_score}.\n"
        )

    parameters = {
        "nursing_home_resident": ("Nursing Home Resident", 10),
        "neoplastic_disease": ("Neoplastic disease", 30),
        "liver_disease": ("Liver disease history", 20),
        "chf": ("CHF History", 10),
        "cerebrovascular_disease": ("Cerebrovascular disease history", 10),
        "renal_disease": ("Renal Disease History", 10),
        "altered_mental_status": ("Altered Mental Status", 20),
        "pleural_effusion": ("Pleural effusion on x-ray", 10),
    }

    for parameter in parameters:
        if parameter == 'nursing_home_resident':
            if parameter not in input_variables:
                explanation += (
                    f"Whether patient is a nursing home "
                    f"resident is not reported. Hence, "
                    f"we assume this to be false and so "
                    f"not add any points to the current "
                    f"total keeping it at {psi_score}.\n"
                )
            elif not input_variables[parameter]:
                explanation += (
                    f"The patient is not a nursing home "
                    f"resident and so we do not add any "
                    f"points to the current total "
                    f"keeping it at {psi_score}.\n"
                )
            else:
                explanation += (
                    f"The patient is reported to be a "
                    f"nursing home resident and so we "
                    f"add 10 points to the score, "
                    f"making the current total "
                    f"{psi_score} + 10 = {psi_score + 10}.\n"
                )
                psi_score += 10
            continue

        if parameter not in input_variables:
            explanation += (
                f"{parameters[parameter][0]} is not reported "
                f"for the patient and so we assume it to be "
                f"false. Hence, we do not add any points "
                f"to the current total keeping it at {psi_score}.\n"
            )
        elif not input_variables[parameter]:
            explanation += (
                f"{parameters[parameter][0]} is reported "
                f"to be false for the patient and so we do "
                f"not add any points to the current total "
                f"keeping it at {psi_score}.\n"
            )
        elif input_variables[parameter]:
            points = parameters[parameter][1]
            explanation += (
                f"{parameters[parameter][0]} is reported to "
                f"be present for the patient and so we add "
                f"{points} points to the score, making "
                f"the current total {psi_score} + {points} "
                f"= {psi_score + points}.\n"
            )
            psi_score += points

    explanation += f"The patient's pulse is {pulse} beats per minute. "

    if pulse >= 125:
        explanation += (
            f"The pulse is greater or equal to than 125 beats "
            f"per minute, and so we add 10 points to the "
            f"score, making the current total {psi_score} "
            f"+ 10 = {psi_score + 10}.\n"
        )
        psi_score += 10
    else:
        explanation += (
            f"The pulse is less than 125 beats per minute "
            f"and so we do not add any points to the score, "
            f"keeping it at {psi_score}.\n"
        )

    explanation += temperature_exp
    if temperature < 35:
        explanation += (
            f"The patient's temperature is less than 35 "
            f"degrees celsius, and so we add 15 points to "
            f"the score, making the current total {psi_score} "
            f"+ 15 = {psi_score + 15}.\n"
        )
        psi_score += 15
    elif temperature > 39.9:
        explanation += (
            f"The patient's temperature is greater than "
            f"39.9 degrees celsius and so we add 15 points "
            f"to the score, making the current total "
            f"{psi_score} + 15 = {psi_score + 15}.\n"
        )
        psi_score += 15
    else:
        explanation += (
            f"The patient's temperature is greater than 35 "
            f"degrees celsius and the temperature is less "
            f"than 39.9 degrees celsius, and so we do not "
            f"add any points to the score, keeping the "
            f"total at {psi_score}.\n"
        )

    explanation += f"The patient's pH is {pH}. "

    if pH < 7.35:
        explanation += (
            f"The patient's pH is less than 7.35, and so "
            f"we add 30 points to the score, making the "
            f"current total {psi_score} + 30 = {psi_score + 30}.\n"
        )
        psi_score += 30
    else:
        explanation += (
            f"The patient's pH is greater than or equal "
            f"to 7.35, and so we do not add any points "
            f"to the score, keeping the current total "
            f"at {psi_score}.\n"
        )

    explanation += (
        f"The patient's respiratory rate is {respiratory_rate} "
        f"breaths per minute. "
    )

    if respiratory_rate >= 30:
        explanation += (
            f"The patient's respiratory rate is greater "
            f"than or equal to 30 breaths per minute and "
            f"so we add 20 points to the score, making "
            f"current total {psi_score} + 20 = {psi_score + 20}.\n"
        )
        psi_score += 20
    else:
        explanation += (
            f"The patient's respiratory rate is less than "
            f"30 breaths per minute and so we do not add "
            f"any points to the score, keeping the total "
            f"score at {psi_score}.\n"
        )

    explanation += f"The patient's systolic blood pressure is {sys_bp} mm Hg. "

    if sys_bp < 90:
        explanation += (
            f"The patient's systolic blood pressure is "
            f"less than 90 mm Hg and so we add 20 points "
            f"to the score, making current total "
            f"{psi_score} + 20 = {psi_score + 20}.\n"
        )
        psi_score += 20
    else:
        explanation += (
            f"The patient's systolic blood pressure is "
            f"greater than or equal to 90 mm Hg and so "
            f"we do not add any points to the score, "
            f"keeping the total at {psi_score}.\n"
        )

    explanation += bun_exp

    if bun >= 30:
        explanation += (
            f"The patient's BUN is greater than or equal "
            f"to 30 mg/dL, and so we add 20 points to "
            f"the score, making current total {psi_score} "
            f"+ 20 = {psi_score + 20}.\n"
        )
        psi_score += 20
    else:
        explanation += (
            f"The patient's BUN is less than 30 mg/dL, "
            f"and so we do not add any points to the "
            f"score, keeping the total at {psi_score}.\n"
        )

    explanation += sodium_exp

    if sodium < 130:
        explanation += (
            f"The patient's sodium is less than 130 "
            f"mmol/L, and so we add 20 points to the "
            f"score, making the current total "
            f"{psi_score} + 20 = {psi_score + 20}.\n"
        )
        psi_score += 20
    else:
        explanation += (
            f"The patient's sodium is greater than or "
            f"equal to 130 mmol/L, and so we do not "
            f"add any points to the score, keeping "
            f"the total at {psi_score}.\n"
        )

    explanation += glucose_exp

    if glucose >= 250:
        explanation += (
            f"The patient's glucose concentration is "
            f"greater than 250 mg/dL, and so we add 10 "
            f"points to the score, making the current "
            f"total {psi_score} + 10 = {psi_score + 10}.\n"
        )
        psi_score += 10
    else:
        explanation += (
            f"The patient's glucose concentration is "
            f"less than or equal to than 250 mg/dL, "
            f"and so we not add any points to the current "
            f"total, keeping it at {psi_score}.\n"
        )

    explanation += f"The patient's hemocratit is {hemocratit} %. "

    if hemocratit < 30:
        explanation += (
            f"The patient's hemocratit is less than 30%, "
            f"and so we add 10 points to the score, "
            f"making the current total {psi_score} + "
            f"10 = {psi_score + 10}.\n"
        )
        psi_score += 10
    else:
        explanation += (
            f"The patient's hemocratit is greater than or equal "
            f"to 30%, and so we not add any points to "
            f"the current total, keeping it at {psi_score}.\n"
        )

    if partial_pressure_oxygen[1] == "mm Hg":
        explanation += (
            f"The patient's partial pressure of oxygen "
            f"is {partial_pressure_oxygen[0]} mm Hg. "
        )

        if partial_pressure_oxygen[0] < 60:
            explanation += (
                f"The patient's partial pressure of "
                f"oxygen is less than 60 mm Hg, and so "
                f"we add {psi_score} points to the score, "
                f"making the current total {psi_score} "
                f"+ 10 = {psi_score + 10}.\n"
            )
            psi_score += 10
        else:
            explanation += (
                f"The patient's partial pressure of "
                f"oxygen is greater than or equal to "
                f"60 mm Hg, and so we not add any points "
                f"to the current total, keeping "
                f"it at {psi_score}.\n"
            )

    elif partial_pressure_oxygen[1] == "kPa":
        explanation += (
            f"The patient's partial pressure of oxygen "
            f"is {partial_pressure_oxygen[0]} kPa. "
        )

        if partial_pressure_oxygen[0] < 8:
            explanation += (
                f"The patient's partial pressure of "
                f"oxygen is less than 8 kPa, and so we "
                f"add {psi_score} points to the score, "
                f"making the current total {psi_score} "
                f"+ 10 = {psi_score + 10}.\n"
            )
            psi_score += 10
        else:
            explanation += (
                f"The patient's partial pressure of "
                f"oxygen is greater than or equal to 8 "
                f"kPa, and so we not add any points to "
                f"the current total, keeping it at {psi_score}.\n"
            )

    explanation += f"The patient's PSI score is {psi_score}.\n"

    return {"Explanation": explanation, "Answer": psi_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "sex": "Male",
            "age": (17, "years"),
            "temperature": (99.0, "degrees fahreinheit"),
            "heart_rate": (98.0, 'beats per minute'),
            "pH": 7.3,
            "respiratory_rate": (17.0, "breaths per minute"),
            "sys_bp": (70, "mm"),
            "bun": (3.5, "mmol/L"),
            "sodium": (134.0, "mmol/L"),
            "glucose": (97.3, "mg/dL"),
            "hemocratit": (20, "%"),
            "partial_pressure_oxygen": (80, "mm"),
            "nursing_home_resident": False,  # Optional
            "neoplastic_disease": False,  # Optional
            "liver_disease": False,  # Optional
            "chf": False,  # Optional
            "cerebrovascular_disease": False,  # Optional
            "renal_disease": False,  # Optional
            "altered_mental_status": False,  # Optional
            "pleural_effusion": False,  # Optional
        },
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = psi_score_explanation(input_variables)
        print(result)
        print("-" * 50)
