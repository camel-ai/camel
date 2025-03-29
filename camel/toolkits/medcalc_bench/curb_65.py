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
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def curb_65_explanation(input_parameters):
    r"""
    Calculates the patient's CURB-65 score and generates a
    detailed explanatory text.

        {'age': (37, 'years'),
         'sys_bp': (90.0, 'mm hg'),
         'dia_bp': (50.0, 'mm hg'),
         'respiratory_rate': (30.0, 'breaths per minute'),
         'bun': (3.5, 'mmol/L')}

    Parameters:
        input_parameters (dict): A dictionary containing the following
        key-value pairs:
            - "age" (tuple): The patient's albumin concentration in the
            format (value, unit).
                - Value (float): Age.
                - Unit (str): The unit can be "months", "years".
            - "sys_bp" (tuple): The patient's systolic blood pressure (
            value, unit).
                - Value (float): Systolic blood pressure.
                - Unit (str): The unit of systolic blood pressure,
                which can be 'mm hg'.
            - "dia_bp" (tuple): The patient's diastolic blood pressure (
            value, unit).
                - Value (float): Diastolic blood pressure.
                - Unit (str): The unit of diastolic blood pressure,
                which can be 'mm hg'.
            - "respiratory_rate" (tuple): The patient's respiratory rate
            in the format (value, unit).
                - Value (float): The value of platelet respiratory rate.
                - Unit (str): The unit of respiratory rate,
                e.g. "breaths per minute" and so on.
            - "bun" (tuple): The patient's Blood Urea Nitrogen in the
            format (value, unit).
                - Value (float): The value of BUN.
                - Unit (str): The unit of BUN,
                e.g. "mmol/L" and so on.
            - "confusion" (boolean): Whether the patient has confusion is
            not reported.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's CURB-65 score.

    Notes:
        - None

    Example:
        curb_65_explanation({'age': (37, 'years'),
        'sys_bp': (90.0, 'mm hg'),
        'dia_bp': (50.0, 'mm hg'),
        'respiratory_rate': (30.0, 'breaths per minute'),
        'bun': (3.5, 'mmol/L')})

        output: "{'Explanation': "\n    The CURB-65 Score criteria are
        listed below:\n\n       1. Confusion: No = 0 points, Yes = +1
        point\n       2. BUN >19 mg/dL (>7 mmol/L urea): No = 0 points,
        Yes = +1 point\n       3. Respiratory Rate ≥30: No = 0 points,
        Yes = +1 point\n       4. Systolic BP <90 mmHg or Diastolic BP ≤60
        mmHg: No = 0 points, \n       Yes = +1 point\n       5. Age ≥65: No
        = 0 points, Yes = +1 point\n    \n    The total CURB-65 score is
        calculated by summing the points for each \n    criterion.\n\n\n
        The CURB-65 score is current at 0 points.\nThe patient is 37 years
        old. The patient's age is less than 65 years, and so we add 0 points
        to the score, keeping the current total at 0.\nWhether the patient
        has confusion is not reported in the note. Hence, we assume this to
        be false, and so 0 points are added to the score, making the current
        total 0.\nThe concentration of BUN is 3.5 mmol/L. We need to convert
        the concentration to mg/dL. Let's first convert the mass of BUN from
        mmol to mg. The mass of BUN is 3.5 mmol. To convert 3.5 mmol
        of BUN to mol, multiply by the conversion factor 0.001, giving
        us 3.5 mmol BUN * 0.001 mol/mmol = 0.004 mol BUN. To convert from
        mol BUN to grams, multiply by the molar mass 28.02 g/mol, which
        will give 0.004 mol BUN * 28.02 g/mol = 0.112 g BUN. To convert
        0.112 g of BUN to mg, multiply by the conversion factor 1000.0,
        giving us 0.112 g BUN * 1000.0 mg/g = 112.0 mg BUN. The current
        volume unit is L and the target volume unit is dL. The conversion
        factor is 10.0 dL for every unit of L. Our next step will be to
        divide the mass by the volume conversion factor of 10.0 to get the
        final concentration in terms of mg/dL. This will result to 112.0 mg
        BUN/10.0 dL = 11.2 mg BUN/dL. The concentration value of 3.5 mmol
        BUN/L converts to 11.2 mg BUN/dL. The patient's BUN concentration
        is less than or equal to 19 mg/dL and so 0 points are added to
        score, keeping the current total at 0.\nThe patient's respiratory
        rate is 30 breaths per minute. Because the respiratory rate is
        greater than 30 breaths per minute, 1 point is added to the score,
        making the current total 0 + 1 = 1.\nThe patient's systiolic blood
        pressure is 90 mm Hg. The patient's diastolic blood pressure is 50
        mm Hg. For a point to be added, the systiolic blood
        pressure must be less than 90 mm Hg or the diastolic blood pressure
        must be less than or equal to 60 mm Hg. Because at least one of
        these statements is true, 1 point is added to score, making the
        current total 1 + 1 = 2.\nThe patient's CURB-65 score is 2.\n",
        'Answer': 2}"
    """
    curb_65_score = 0

    explanation = r"""
    The CURB-65 Score criteria are listed below:

       1. Confusion: No = 0 points, Yes = +1 point
       2. BUN >19 mg/dL (>7 mmol/L urea): No = 0 points, Yes = +1 point
       3. Respiratory Rate ≥30: No = 0 points, Yes = +1 point
       4. Systolic BP <90 mmHg or Diastolic BP ≤60 mmHg: No = 0 points, 
       Yes = +1 point
       5. Age ≥65: No = 0 points, Yes = +1 point
    
    The total CURB-65 score is calculated by summing the points for each 
    criterion.\n\n
    """

    explanation += "The CURB-65 score is current at 0 points.\n"

    bun_exp, bun = conversion_explanation(
        input_parameters["bun"][0],
        "BUN",
        28.02,
        None,
        input_parameters["bun"][1],
        "mg/dL",
    )

    respiratory_rate = int(input_parameters["respiratory_rate"][0])
    sys_bp = int(input_parameters["sys_bp"][0])
    dia_bp = int(input_parameters["dia_bp"][0])
    age_exp, age = age_conversion_explanation(input_parameters["age"])

    explanation += age_exp

    if age >= 65:
        explanation += (
            f"The patient's age is greater than or equal to 65 "
            f"years, and so we add 1 point to the score, making "
            f"the current total {curb_65_score} + 1 = "
            f"{curb_65_score + 1}.\n"
        )
        curb_65_score += 1
    else:
        explanation += (
            f"The patient's age is less than 65 years, and so we "
            f"add 0 points to the score, keeping the current "
            f"total at {curb_65_score}.\n"
        )

    if 'confusion' not in input_parameters:
        explanation += (
            f"Whether the patient has confusion is not reported "
            f"in the note. Hence, we assume this to be false, "
            f"and so 0 points are added to the score, making the "
            f"current total {curb_65_score}.\n"
        )
    elif input_parameters["confusion"]:
        explanation += (
            f"Because the patient has confusion, "
            f"1 point is added to score making the current "
            f"total {curb_65_score} + 1 = {curb_65_score + 1}.\n"
        )
        curb_65_score += 1
    else:
        explanation += (
            f"Because the patient does not have confusion, "
            f"0 points are added to the score, keeping the score "
            f"at {curb_65_score}.\n"
        )

    explanation += bun_exp

    if bun > 19:
        explanation += (
            f"The patient's BUN concentration is greater than 19 "
            f"mg/dL and so we add 1 point to score making the "
            f"current total {curb_65_score} + 1 = "
            f"{curb_65_score + 1}.\n"
        )
        curb_65_score += 1
    else:
        explanation += (
            f"The patient's BUN concentration is less than or "
            f"equal to 19 mg/dL and so 0 points are added to "
            f"score, keeping the current total at "
            f"{curb_65_score}.\n"
        )

    explanation += (
        f"The patient's respiratory rate is {respiratory_rate} "
        f"breaths per minute. "
    )

    if respiratory_rate >= 30:
        explanation += (
            f"Because the respiratory rate is greater than 30 "
            f"breaths per minute, 1 point is added to the score, "
            f"making the current total {curb_65_score} + 1 = "
            f"{curb_65_score + 1}.\n"
        )
        curb_65_score += 1
    else:
        explanation += (
            f"Because the respiratory rate is greater than 30 "
            f"breaths per minute, 0 points are added to the "
            f"score, keeping the current total at "
            f"{curb_65_score}.\n"
        )

    explanation += (
        f"The patient's systiolic blood pressure is {sys_bp} mm "
        f"Hg. The patient's diastolic blood pressure is {dia_bp} "
        f"mm Hg. "
    )

    if sys_bp < 90 or dia_bp <= 60:
        explanation += (
            f"For a point to be added, the systiolic "
            f"blood pressure must be less than 90 mm Hg or the "
            f"diastolic blood pressure must be less than or "
            f"equal to 60 mm Hg. Because at least one of these "
            f"statements is true, 1 point is added to score, "
            f"making the current total {curb_65_score} + 1 = "
            f"{curb_65_score + 1}.\n"
        )
        curb_65_score += 1
    else:
        explanation += (
            f"For a point to be added, the systiolic "
            f"blood pressure must be less than 90 mm Hg or the "
            f"diastolic blood pressure must be less than or "
            f"equal to 60 mm Hg. Because neither of these "
            f"statements are true, 0 points are added to score, "
            f"keeping the current total to {curb_65_score}.\n"
        )

    explanation += f"The patient's CURB-65 score is {curb_65_score}.\n"

    return {"Explanation": explanation, "Answer": curb_65_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            'age': (37, 'years'),
            'sys_bp': (90.0, 'mm hg'),
            'dia_bp': (50.0, 'mm hg'),
            'respiratory_rate': (30.0, 'breaths per minute'),
            'bun': (3.5, 'mmol/L'),
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = curb_65_explanation(input_variables)
        print(result)
        print("-" * 50)
