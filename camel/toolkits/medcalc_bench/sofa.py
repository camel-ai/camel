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
- rewrite function compute_sofa_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
    convert_to_units_per_liter_explanation,
)


def compute_sofa_explanation(input_parameters):
    explanation = """
    The criteria for the SOFA Score are shown below:

       1. PaO₂/FiO₂ ratio (mm Hg): ≥400 = 0 points, 300-399 = +1 point,
        200-299 = +2 points, 100-199 (with respiratory support) = +3 points,
        <100 (with respiratory support) = +4 points
       2. Platelets (10^3/µL): ≥150 = 0 points, 100-149 = +1 point, 50-99 = +2
        points, 20-49 = +3 points, <20 = +4 points
       3. Glasgow Coma Scale (GCS): 15 = 0 points, 13-14 = +1 point, 10-12 =
        +2 points, 6-9 = +3 points, <6 = +4 points
       4. Bilirubin (mg/dL): <1.2 = 0 points, 1.2-1.9 = +1 point, 2.0-5.9 = +2
        points, 6.0-11.9 = +3 points, ≥12.0 = +4 points
       5. Mean arterial pressure (MAP) or administration of vasopressors:
        No hypotension = 0 points, MAP <70 mmHg = +1 point, Dopamine ≤5 or
        Dobutamine (any dose) = +2 points, Dopamine >5 or Epinephrine ≤0.1
        or norepinephrine ≤0.1 = +3 points, Dopamine >15 or Epinephrine >0.1
        or norepinephrine >0.1 = +4 points
       6. Creatinine (mg/dL) or urine output: <1.2 = 0 points, 1.2-1.9 = +1
       point, 2.0-3.4 = +2 points, 3.5-4.9 or urine output <500 mL/day = +3
       points, ≥5.0 or urine output <200 mL/day = +4 points

    The total SOFA Score is calculated by summing the points
    for each criterion.\n\n
    """

    explanation += "The patient's current SOFA score is 0.\n"

    sofa_score = 0

    pao2 = input_parameters["partial_pressure_oxygen"][0]
    fio2 = input_parameters["fio2"][0]

    dopamine = input_parameters.get("dopamine", [0])
    dobutamine = input_parameters.get("dobutamine", [0])
    epinephrine = input_parameters.get("epinephrine", [0])
    norepinephrine = input_parameters.get("norepinephrine", [0])

    explanation += (
        f"The patient's partial pressure of oxygen is {pao2} mm "
        f"Hg and FiO₂ percentage is {fio2} %. "
    )
    ratio = round_number(pao2 / fio2)
    explanation += (
        f"This means that the patient's partial pressure of "
        f"oxygen to FiO₂ ratio is {ratio}. "
    )

    if "mechanical_ventilation" not in input_parameters:
        explanation += (
            "Whether the patient is on mechanical ventillation "
            "is not reported and so we assume this to be false. "
        )
        input_parameters["mechanical_ventilation"] = False
    elif input_parameters["mechanical_ventilation"]:
        explanation += (
            "The patient is reported to be on mechanical " "ventillation. "
        )
    else:
        explanation += (
            "The patient is reported to not be on mechanical " "ventillation. "
        )
        input_parameters["mechanical_ventilation"] = False

    if "cpap" not in input_parameters:
        explanation += (
            "Whether the patient is on continuous positive "
            "airway pressure is not reported and so we assume "
            "this to be false. "
        )
        input_parameters["cpap"] = False
    elif input_parameters["cpap"]:
        explanation += (
            "The patient is reported to be using continuous "
            "positive airway pressure. "
        )
    else:
        explanation += (
            "The patient is reported to not be using continuous "
            "positive airway pressure. "
        )

    if 300 <= ratio < 400:
        explanation += (
            f"Because the patient's partial pressure of oxygen "
            f"to FiO₂ ratio is between 300 and 400, we increase "
            f"the score by one point, makeing the current total "
            f"{sofa_score} + 1 = {sofa_score + 1}.\n"
        )
        sofa_score += 1
    elif 200 <= ratio < 300:
        explanation += (
            f"Because the patient's partial pressure of oxygen "
            f"to FiO₂ ratio is between 200 and 300, we increase "
            f"the score by two points, makeing the current "
            f"total {sofa_score} + 2 = {sofa_score + 2}.\n"
        )
        sofa_score += 2
    elif ratio <= 199 and (
        not input_parameters["mechanical_ventilation"]
        and not input_parameters["cpap"]
    ):
        explanation += (
            f"Because the patient's partial pressure of oxygen "
            f"to FiO₂ ratio is between 200 and 300, the patient "
            f"is not on mechanical ventillation and is not using "
            f"continious positive airway pressure, we increase "
            f"the score by two points, makeing the current "
            f"total {sofa_score} + 2 = {sofa_score + 2}.\n"
        )
        sofa_score += 2
    elif 100 <= ratio < 199 and (
        input_parameters["mechanical_ventilation"] or input_parameters["cpap"]
    ):
        explanation += (
            f"Because the patient's partial pressure of oxygen "
            f"to FiO₂ ratio is between 100 to 199, and the "
            f"patient is using at least one of (i) mechanical "
            f"ventillation or (ii) continious positive airway "
            f"pressure, we increase the score by three points, "
            f"makeing the current total {sofa_score} + 3 = "
            f"{sofa_score + 3}.\n"
        )
        sofa_score += 3
    elif ratio < 100 and input_parameters["mechanical_ventilation"]:
        explanation += (
            f"Because the patient's partial pressure of oxygen "
            f"to FiO₂ ratio is less than 100, and the patient "
            f"is using at least one of (i) mechanical "
            f"ventillation or (ii) continious positive airway "
            f"pressure, we increase the score by four points, "
            f"makeing the current total {sofa_score} + 4 = "
            f"{sofa_score + 4}.\n"
        )
        sofa_score += 4

    if (
        'sys_bp' in input_parameters
        and 'dia_bp' in input_parameters
        and 1 / 3 * input_parameters['sys_bp'][0]
        + 2 / 3 * input_parameters['dia_bp'][0]
        < 70
        and (
            not dobutamine[0] and not epinephrine[0] and not norepinephrine[0]
        )
    ):
        sys_bp = input_parameters['sys_bp'][0]
        dia_bp = input_parameters['dia_bp'][0]
        map = round_number(1 / 3 * sys_bp + 2 / 3 * dia_bp)
        explanation = (
            f"The patient's systolic blood pressure is {sys_bp} "
            f"mm Hg and the patient's diastolic blood pressure "
            f"is {dia_bp} mm Hg, making the patient's mean "
            f"arterial blood pressure {map} mm Hg. "
        )
        explanation += (
            f"For one point to be given, the patient's mean "
            f"arterial pressure must be less than 70 mm Hg, "
            f"making the current total {sofa_score} + 1 "
            f"= {sofa_score + 1}.\n"
        )
        sofa_score += 1
    elif dopamine[0] <= 5 or dobutamine[0]:
        explanation += (
            f"For two points to be given, the patient must "
            f"be taking less than or equal to 5 micrograms/kg/min "
            f"or any amount of dobutamine. Because at least "
            f"one of these cases is true for the patient, "
            f"we increment the score by two points, "
            f"making the current total {sofa_score} + 2 "
            f"= {sofa_score + 2}.\n"
        )
        sofa_score += 2
    elif dopamine[0] > 5 or epinephrine[0] <= 0.1 or norepinephrine[0] <= 0.1:
        explanation += (
            f"For three points to be given, the patient "
            f"must be taking more than 5 micrograms/kg/min, "
            f"less than or equal to 0.1 micrograms/kg/min "
            f"of epinephrine, or less than or equal to 0.1 "
            f"micrograms/kg/min of norepinephrine. "
            f"Because at least one of these cases is true for the "
            f"patient, we increment the score by three "
            f"points, making the current total "
            f"{sofa_score} + 3 = {sofa_score + 3}.\n"
        )
        sofa_score += 3
    elif dopamine[0] > 15 or epinephrine[0] > 0.1 or norepinephrine[0] > 0.1:
        explanation += (
            f"For four points to be given, the patient "
            f"must be taking more than 15 micrograms/kg/min, "
            f"more than 0.1 micrograms/kg/min of epinephrine, "
            f"or more than 0.1 micrograms/kg/min of norepinephrine. "
            f"Because at least one of these cases is true "
            f"for the patient, we increment the score by "
            f"four points, making the current total "
            f"{sofa_score} + 4 = {sofa_score + 4}.\n"
        )
        sofa_score += 4

    if 'gcs' not in input_parameters:
        gcs = 15
        explanation += f"The patient's glasgow coma score is {gcs}. "
    else:
        gcs = input_parameters["gcs"]
        explanation += (
            "The patient's glasgow coma score is not "
            "reported so we take it to be 15. "
        )

    if gcs < 6:
        explanation += (
            f"Because the patient's glasgow coma score is "
            f"less than 6, we add 4 points to the score, "
            f"making the current score {sofa_score} + 4 "
            f"= {sofa_score + 4}.\n "
        )
        sofa_score += 4
    elif 6 <= gcs <= 9:
        explanation += (
            f"Because the patient's glasgow coma score "
            f"is between 6 and 9, we add 3 points to the "
            f"score, making the current score "
            f"{sofa_score} + 3 = {sofa_score + 3}.\n "
        )
        sofa_score += 3
    elif 10 <= gcs <= 12:
        explanation += (
            f"Because the patient's glasgow coma score "
            f"is between 10 and 12, we add 2 points to "
            f"the score, making the current score "
            f"{sofa_score} + 2 = {sofa_score + 2}.\n "
        )
        sofa_score += 2
    elif 13 <= gcs <= 14:
        explanation += (
            f"Because the patient's glasgow coma score "
            f"is between 13 and 14, we add 1 point to "
            f"the score, making the current score "
            f"{sofa_score} + 1 = {sofa_score + 1}.\n "
        )
        sofa_score += 1
    else:
        explanation += (
            f"Because the patient's glasgow coma score "
            f"is 15, we add 0 points to the score, "
            f"keeping the score at {sofa_score}.\n "
        )

    bilirubin_exp, bilirubin = conversion_explanation(
        input_parameters['bilirubin'][0],
        'bilirubin',
        584.66,
        None,
        input_parameters['bilirubin'][1],
        "mg/dL",
    )
    explanation += bilirubin_exp

    if bilirubin < 1.2:
        explanation += (
            f"Because the patient's bilirubin concentration is "
            f"less than 1.2 mg/dL, we add 0 points to the score, "
            f"keeping the score at {sofa_score}.\n "
        )
    if 1.2 <= bilirubin < 2.0:
        explanation += (
            f"Because the patient's bilirubin concentration is "
            f"at least 1.2 mg/dL but less than 2.0 mg/dL, "
            f"we increment the score by one point, "
            f"make the current score {sofa_score} + 1 = "
            f"{sofa_score + 1}.\n"
        )
        sofa_score += 1
    elif 2.0 <= bilirubin < 6.0:
        explanation += (
            f"Because the patient's bilirubin concentration is "
            f"at least 2.0 mg/dL but less than 6.0 mg/dL, "
            f"we increment the score by two points, "
            f"make the current score {sofa_score} + 2 "
            f"= {sofa_score + 2}.\n"
        )
        sofa_score += 2
    elif 6.0 <= bilirubin < 12.0:
        explanation += (
            f"Because the patient's bilirubin concentration "
            f"is at least 6.0 mg/dL but less than 12.0 mg/dL, "
            f"we increment the score by three points, "
            f"make the current score {sofa_score} + 3 "
            f"= {sofa_score + 3}.\n"
        )
        sofa_score += 3
    elif bilirubin >= 12.0:
        explanation += (
            f"Because the patient's bilirubin concentration is "
            f"at least 12.0 mg/dL, we increment the score by "
            f"four points, make the current score"
            f"{sofa_score} + 4 = {sofa_score + 4}.\n"
        )
        sofa_score += 4

    platelet_count_exp, platelet_count = (
        convert_to_units_per_liter_explanation(
            input_parameters["platelet_count"][0],
            input_parameters["platelet_count"][1],
            "platelet",
            "µL",
        )
    )
    explanation += platelet_count_exp

    if platelet_count >= 150000:
        explanation += (
            f"Because the patient's platelet count is at "
            f"least 150*10³/µL, we do not any points to "
            f"the score, keeping the current score "
            f"at {sofa_score}.\n"
        )
    if 100000 <= platelet_count < 150000:
        explanation += (
            f"Because the patient's platelet count is "
            f"between 100*10³/µL but less than 150*10³/µL, "
            f"we increment the score by one point, "
            f"making the current score {sofa_score} + 1 "
            f"= {sofa_score + 1}.\n"
        )
        sofa_score += 1
    elif 50000 <= platelet_count < 100000:
        explanation += (
            f"Because the patient's platelet count is "
            f"between 50*10³/µL but less than 100*10³/µL, "
            f"we increment the score by two points, "
            f"making the current score {sofa_score} + 2 "
            f"= {sofa_score + 2}.\n"
        )
        sofa_score += 2
    elif 20000 <= platelet_count < 50000:
        explanation += (
            f"Because the patient's platelet count is "
            f"between 20*10³/µL but less than 50*10³/µL, "
            f"we increment the score by three points, "
            f"making the current score {sofa_score} + 3 "
            f"= {sofa_score + 3}.\n"
        )
        sofa_score += 3
    elif platelet_count < 20000:
        explanation += (
            f"Because the patient's platelet count is "
            f"less than 20*10³/µL, we increment the score "
            f"by four points, making the current score "
            f"{sofa_score} + 4 = {sofa_score + 4}.\n"
        )
        sofa_score += 4

    if 'creatinine' not in input_parameters:
        urine_output = input_parameters["urine_output"][0]

        explanation += f"The patients urine output is {urine_output} mL/day. "

        if urine_output < 500:
            explanation += (
                f"Because the patient's urine output is "
                f"less than 500 mL/day, we increment the "
                f"score by three points, making the current "
                f"total {sofa_score} + 3 = {sofa_score + 3}.\n"
            )
            sofa_score += 3
        elif urine_output < 200:
            explanation += (
                f"Because the patient's urine output is "
                f"less than 200 mL/day, we increment the "
                f"score by four points, making the current "
                f"total {sofa_score} + 4 = {sofa_score + 4}.\n"
            )
            sofa_score += 4

    elif 'urine_output' not in input_parameters:
        creatinine_exp, creatinine = conversion_explanation(
            input_parameters['creatinine'][0],
            "creatinine",
            113.12,
            None,
            input_parameters['creatinine'][1],
            "mg/dL",
        )

        explanation += creatinine_exp

        if 1.2 <= creatinine < 2.0:
            explanation += (
                f"Because the patient's creatinine concentration "
                f"is at least 1.2 mg/dL but less than 2.0 mg/dL, "
                f"we increment the score by one point, "
                f"making the current total {sofa_score} + 1 "
                f"= {sofa_score + 1}.\n"
            )
            sofa_score += 1
        elif 2.0 <= creatinine < 3.5:
            explanation += (
                f"Because the patient's creatinine concentration "
                f"is at least 2.0 mg/dL but less than 3.5 mg/dL, "
                f"we increment the score by two points, making "
                f"the current total {sofa_score} + 2 = "
                f"{sofa_score + 2}.\n"
            )
            sofa_score += 2
        elif 3.5 <= creatinine < 5.0:
            explanation += (
                f"Because the patient's creatinine concentration "
                f"is at least 3.5 mg/dL but less than 5.0 mg/dL, "
                f"we increment the score by three points, "
                f"making the current total {sofa_score} + 3 "
                f"= {sofa_score + 3}.\n"
            )
            sofa_score += 3
        elif creatinine >= 5.0:
            explanation += (
                f"Because the patient's creatinine concentration "
                f"is greater than 5.0 mg/dL, "
                f"we increment the score by four points, "
                f"making the current total {sofa_score} + 4 "
                f"= {sofa_score + 4}.\n"
            )
            sofa_score += 4

    explanation += f"Hence, the patient's SOFA score is {sofa_score} points.\n"

    return {"Explanation": explanation, "Answer": sofa_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            'partial_pressure_oxygen': (80, 'mm'),
            'fio2': (0.2, 'Hg'),
            'platelet_count': (150000, 'µL'),
            'gcs': 15,
            'dopamine': (97.2, "pg/mL"),
            'dobutamine': (15, "µg/kg/min"),
            'epinephrine': (19, "pg/mL"),
            'norepinephrine': (200, "pg/mL"),
            'cpap': False,
            'sys_bp': (70, "mm"),
            'dia_bp': (12, "Hg"),
            'bilirubin': (2.8, "mg/dL"),
            'creatinine': (3.7, 'mg/dL'),
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_sofa_explanation(input_variables)
        print(result)
        print("-" * 50)
