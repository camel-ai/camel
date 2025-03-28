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
- rewrite function compute_centor_score_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.convert_temperature import (
    fahrenheit_to_celsius_explanation,
)


def compute_centor_score_explanation(input_variables):
    r"""
    Calculates the patient's Centor Score and generates a detailed
    explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following
        key-value pairs:
            - "age" (tuple): The patient's albumin concentration in the
            format (value, unit).
                - Value (float): Age.
                - Unit (str): The unit can be "months", "years".
            - "temperature" (tuple): The patient's temperature in the
            format (value, unit).
                - Value (float): Temperature.
                - Unit (str): The unit can be "fahrenheit", "celsius".
            - "exudate_swelling_tonsils" (boolean): Exudate or swelling on
            tonsils
            - "tender_lymph_nodes" (boolean): Tender/swollen anterior
            cervical lymph nodes
            - "cough_absent" (boolean): Whether cough present

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's Centor Score.

    Notes:
        - None

    Example:
        compute_centor_score_explanation({
            "age": (48, "years"),
            "temperature": (99.0, "degrees fahreinheit"),
            "exudate_swelling_tonsils": False,
            "tender_lymph_nodes": False,
            "cough_absent": False,
        })

        output: "{'Explanation': "\n    The criteria listed in the Centor
        Score formula are listed below:\n    \n       1. Age: 3-14 years =
        +1 point, 15-44 years = 0 points, \n       ≥45 years = -1 point\n
        2. Exudate or swelling on tonsils: No = 0 points, Yes = +1
        point\n       3. Tender/swollen anterior cervical lymph nodes:
        \n       No = 0 points, Yes = +1 point\n       4. Temperature >38°C
        (100.4°F): No = 0 points, Yes = +1 point\n       5. Cough:
        Cough present = 0 points, Cough absent = +1 point\n    \n
        The Centor score is calculated by summing\n    the points for
        each criterion.\n\n\n    The current Centor score is 0.\nThe
        patient is 48 years old. Because the age is greater than 44 years,
        we decrease the score by one point, making the score 0 - 1 = -1.
        \nThe patient's temperature is 99.0 degrees fahrenheit. To convert
        to degrees celsius, apply the formula 5/9 * [temperature (degrees
        fahrenheit) - 32]. This means that the patient's temperature is
        5/9 * 67.0 = 37.222 degrees celsius. The patient's temperature is
        less than or equal to 38 degrees Celsius, and so we do not make any
        changes to the score, keeping the score at -1.\nThe patient note
        reports 'cough absent' as absent for the patient. Hence, we do not
        change the score, keeping the current score at -1.\nThe patient
        note reports 'tender/swollen anterior cervical lymph nodes' as
        absent for the patient. Hence, we do not change the score, keeping
        the current score at -1.\nThe patient note reports 'exudate or
        swelling on tonsils' as absent for the patient. Hence, we do not
        change the score, keeping the current score at -1.\nHence, the
        Centor score forthe patient is -1.\n", 'Answer': -1}"
    """

    explanation = """
    The criteria listed in the Centor Score formula are listed below:
    
       1. Age: 3-14 years = +1 point, 15-44 years = 0 points, 
       ≥45 years = -1 point
       2. Exudate or swelling on tonsils: No = 0 points, Yes = +1 point
       3. Tender/swollen anterior cervical lymph nodes: 
       No = 0 points, Yes = +1 point
       4. Temperature >38°C (100.4°F): No = 0 points, Yes = +1 point
       5. Cough: Cough present = 0 points, Cough absent = +1 point
    
    The Centor score is calculated by summing
    the points for each criterion.\n\n
    """

    centor_score = 0
    age_explanation, age = age_conversion_explanation(input_variables["age"])
    explanation += "The current Centor score is 0.\n"
    explanation += age_explanation

    if 3 <= age <= 14:
        explanation += (
            f"Because the age is between 3 and 14 years, we add "
            f"one point to the score making current score "
            f"{centor_score} + 1 = {centor_score + 1}.\n"
        )
        centor_score += 1
    elif 15 <= age <= 44:
        explanation += (
            f"Because the age is in between 15 and 44 years, "
            f"the score does not change, keeping the score at "
            f"{centor_score}.\n"
        )
    elif age >= 45:
        explanation += (
            f"Because the age is greater than 44 years, "
            f"we decrease the score by one point, making the "
            f"score {centor_score} - 1 = {centor_score - 1}.\n"
        )
        centor_score -= 1

    explanation_temp, temp_val = fahrenheit_to_celsius_explanation(
        input_variables["temperature"][0], input_variables["temperature"][1]
    )

    explanation += explanation_temp
    if temp_val > 38:
        explanation += (
            f"The patient's temperature is greater than 38 "
            f"degrees Celsius, and so we add one point to the "
            f"score, making the current score {centor_score} + 1 "
            f"= {centor_score + 1}.\n"
        )
        centor_score += 1
    elif temp_val <= 38:
        explanation += (
            f"The patient's temperature is less than or equal to "
            f"38 degrees Celsius, and so we do not make any "
            f"changes to the score, keeping the score at "
            f"{centor_score}.\n"
        )

    default_parameters_dict = {
        "cough_absent": "cough absent",
        "tender_lymph_nodes": "tender/swollen "
        "anterior cervical "
        "lymph nodes",
        "exudate_swelling_tonsils": "exudate or " "swelling on " "tonsils",
    }

    for parameter in default_parameters_dict:
        if parameter not in input_variables:
            explanation += (
                f"The patient note does not mention details "
                f"about '{default_parameters_dict[parameter]}' "
                f"and so we assume it to be absent. "
            )
            input_variables[parameter] = False
            explanation += (
                f"Hence, we do not change the score, keeping the "
                f"current score at {centor_score}.\n"
            )
        elif not input_variables[parameter]:
            explanation += (
                f"The patient note reports '"
                f"{default_parameters_dict[parameter]}' as "
                f"absent for the patient. Hence, "
                f"we do not change the score, "
                f"keeping the current score at {centor_score}.\n"
            )
        else:
            explanation += (
                f"The patient note reports '"
                f"{default_parameters_dict[parameter]}' as "
                f"present for the patient. "
                f"Hence, we increase the score by 1, "
                f"making the current score "
                f"{centor_score} + 1 = {centor_score + 1}.\n"
            )
            centor_score += 1

    explanation += (
        f"Hence, the Centor score for" f"the patient is {centor_score}.\n"
    )

    return {"Explanation": explanation, "Answer": centor_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "age": (48, "years"),
            "temperature": (99.0, "degrees fahreinheit"),
            "exudate_swelling_tonsils": False,
            "tender_lymph_nodes": False,
            "cough_absent": False,
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_centor_score_explanation(input_variables)
        print(result)
        print("-" * 50)
