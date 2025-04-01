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
- rewrite function compute_has_bled_score_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)


def compute_has_bled_score_explanation(input_variables):
    r"""
    Calculates the patient's Centor Score and generates a detailed
    explanatory text.

        {
            "age": (45, 'years'),
            "hypertension": False,
            "liver_disease_has_bled": False,
            "renal_disease_has_bled": False,
            "stroke": False,
            "prior_bleeding": False,
            "labile_inr": False,
            "medications_for_bleeding": False,
            "alcoholic_drinks": 6
        }

    Parameters:
        input_variables (dict): A dictionary containing the following
        key-value pairs:
            - "age" (tuple): The patient's albumin concentration in the
            format (value, unit).
                - Value (float): Age.
                - Unit (str): The unit can be "months", "years".
            - "hypertension" (boolean): Hypertension (Uncontrolled,
            >160 mmHg systolic).
            - "liver_disease_has_bled" (boolean): Liver disease
            (Cirrhosis or bilirubin > 2x normal with AST/ALT/AP > 3x normal)
            - "renal_disease_has_bled" (boolean): Renal disease (Dialysis,
            transplant, Cr >2.26 mg/dL or > 200 µmol/L).
            - "stroke" (boolean): Stroke history.
            - "prior_bleeding" (boolean): Prior major bleeding or
            predisposition to bleeding.
            - "labile_inr" (boolean): Labile INR (Unstable/high INRs,
            time in therapeutic range < 60%).
            - "medications_for_bleeding" (boolean): Medication usage
            predisposing to bleeding (Aspirin, clopidogrel, NSAIDs).
            - "alcoholic_drinks" (int): Alcohol use (≥8 drinks/week).

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's HAS-BLED Score.

    Notes:
        - None

    Example:
        compute_has_bled_score_explanation()

        output: ""
    """

    explanation = """
    The criteria for the HAS-BLED score are listed below below:
    
       1. Hypertension (Uncontrolled, >160 mmHg systolic): 
       No = 0 points, Yes = +1 point
       2. Renal disease (Dialysis, transplant, Cr >2.26 mg/dL or > 200 
       µmol/L): No = 0 points, Yes = +1 point
       3. Liver disease (Cirrhosis or bilirubin > 2x normal with AST/ALT/AP 
       > 3x normal): No = 0 points, Yes = +1 point
       4. Stroke history: No = 0 points, Yes = +1 point
       5. Prior major bleeding or predisposition to bleeding: 
       No = 0 points, Yes = +1 point
       6. Labile INR (Unstable/high INRs, time in therapeutic range < 60%): 
       No = 0 points, Yes = +1 point
       7. Age >65: No = 0 points, Yes = +1 point
       8. Medication usage predisposing to bleeding (Aspirin, clopidogrel, 
       NSAIDs): No = 0 points, Yes = +1 point
       9. Alcohol use (≥8 drinks/week): No = 0 points, Yes = +1 point
    
    The total HAS-BLED score is calculated by summing the points for each 
    criterion.
    """

    has_bled_score = 0

    num_alcolic_drinks = input_variables["alcoholic_drinks"]

    explanation += "The current HAS-BLED score is 0.\n"
    age_explanation, age_value = age_conversion_explanation(
        input_variables["age"]
    )
    explanation += age_explanation

    if age_value > 65:
        explanation += (
            f"Because the patient's age is greater than 65 years, "
            f"we increment the score by 1, making the "
            f"current score {has_bled_score} + 1 = "
            f"{has_bled_score + 1}.\n"
        )
        has_bled_score += 1
    else:
        explanation += (
            f"Because the patient's age is less than "
            f"66 years, we don't change the score, "
            f"keeping the current score at {has_bled_score}.\n"
        )

    if num_alcolic_drinks >= 8:
        explanation += (
            f"The patient has {num_alcolic_drinks} drinks a "
            f"week. Because the patient has at least 8 alcoholic "
            f"drinks a week, we increment the score by 1, "
            f"making the current score {has_bled_score} + 1 "
            f"= {has_bled_score + 1}.\n"
        )
        has_bled_score += 1
    else:
        explanation += (
            f"The patient has {num_alcolic_drinks} drinks a "
            f"week. Because the patient has less than 8 "
            f"alcoholic drinks a week, we don't change the "
            f"score, keeping the current score "
            f"at {has_bled_score}.\n"
        )

    default_parameters_set = {
        "hypertension": "hypertension",
        "liver_disease_has_bled": "liver disease",
        "renal_disease_has_bled": "renal disease",
        "stroke": "stroke history",
        "prior_bleeding": "prior bleeding",
        "labile_inr": "labile inr",
        "medications_for_bleeding": "medications " "for bleeding",
    }

    for parameter, name in default_parameters_set.items():
        if parameter not in input_variables:
            explanation += (
                f"The issue, {name}, is missing from "
                f"the patient note and so we assume it to "
                f"be absent and so we do not change the score, "
                f"keeping the current score at {has_bled_score}.\n"
            )
            input_variables[parameter] = False
        elif not input_variables[parameter]:
            explanation += (
                f"The issue, {name}, is reported to be absent "
                f"for the patient and so we do not change "
                f"the score, keeping the current score "
                f"at {has_bled_score}.\n"
            )
        else:
            explanation += (
                f"The issue, {name}, is reported to be present "
                f"for the patient note and so we increase the "
                f"score by 1, making the current score "
                f"{has_bled_score} + 1 = {has_bled_score + 1}.\n"
            )
            has_bled_score += 1

    explanation += (
        f"Hence, the patient's HAS-BLED score " f"is {has_bled_score}.\n"
    )

    return {"Explanation": explanation, "Answer": has_bled_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "age": (45, 'years'),
            "hypertension": False,
            "liver_disease_has_bled": False,
            "renal_disease_has_bled": False,
            "stroke": False,
            "prior_bleeding": False,
            "labile_inr": False,
            "medications_for_bleeding": False,
            "alcoholic_drinks": 6,
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_has_bled_score_explanation(input_variables)
        print(result)
        print("-" * 50)
