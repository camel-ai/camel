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
"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function targetweight_explanation
- translation

Date: March 2025
"""

import math

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def mrdr_gfr_explanation(input_variables):
    """
    Calculates the patient's Glomerular Filtration Rate (GFR) and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "age" (tuple): The patient's blood creatinine level in the format (value, unit).
                - Value (float): blood creatinine level.
                - Unit (str): The unit can be "mg/dL", "µmol/L", and so on.
            - "creatinine" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters) or "in" (inches).
            - "sex" (str): The patient's gender, which can be either "Male" or "Female".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's Glomerular Filtration Rate (GFR).

    Notes:
        - Uses the `conversion_explanation` function to convert source unit to target unit.

    Example:
        mrdr_gfr_explanation({"age": (49, 'years'),"creatinine": (10.6, 'mg/dL'),"sex": "Male"})
        output: "{'Explanation': "The patient is 49 years old. The concentration of Creatinine is 10.6 mg/dL. \nThe race of the patient is not provided, so the default value of the race coefficient is 1.0.\nThe patient is male, so the gender coefficient is 1.\nThe patient's estimated GFR is calculated using the MDRD equation as:\nGFR = 175 * creatinine^(-1.154) * age^(-0.203) * race_coefficient * gender_coefficient. The creatinine concentration is mg/dL.\nPlugging in these values will give us: 175 * 10.6^(-1.154) * 49^(-0.203) * 1 * 1=5.209.\nHence, the patient's GFR is 5.209 mL/min/1.73m².\n", 'Answer': 5.209}"
    """

    gender = input_variables["sex"]

    age_explanation, age = age_conversion_explanation(input_variables["age"])
    creatinine_exp, creatinine_conc = conversion_explanation(
        input_variables["creatinine"][0],
        "Creatinine",
        113.12,
        None,
        input_variables["creatinine"][1],
        "mg/dL",
    )

    explanation = ""
    explanation += f"{age_explanation}"
    explanation += f"{creatinine_exp}\n"

    race_coefficient = 1

    if "race" in input_variables:
        race = input_variables["race"]
        if race == "Black":
            race_coefficient = 1.212
            explanation += (
                "The patient is Black, so the race coefficient is 1.212.\n"
            )
        else:
            explanation += "The patient is not Black, so the race coefficient is defaulted to 1.0.\n"
    else:
        explanation += "The race of the patient is not provided, so the default value of the race coefficient is 1.0.\n"

    gender_coefficient = 1
    if gender == "Female":
        gender_coefficient = 0.742
        explanation += (
            "The patient is female, so the gender coefficient is 0.742.\n"
        )
    else:
        explanation += "The patient is male, so the gender coefficient is 1.\n"

    gfr = round_number(
        175
        * math.exp(math.log(creatinine_conc) * -1.154)
        * math.exp(math.log(age) * -0.203)
        * race_coefficient
        * gender_coefficient
    )

    explanation += (
        f"The patient's estimated GFR is calculated using the MDRD equation as:\n"
        f"GFR = 175 * creatinine^(-1.154) * age^(-0.203) * race_coefficient * gender_coefficient. The creatinine concentration is mg/dL.\n"
        f"Plugging in these values will give us: 175 * {creatinine_conc}^(-1.154) * {age}^(-0.203) * {race_coefficient} * {gender_coefficient}={gfr}.\n"
        f"Hence, the patient's GFR is {gfr} mL/min/1.73m².\n"
    )

    return {"Explanation": explanation, "Answer": gfr}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {"age": (49, 'years'), "creatinine": (10.6, 'mg/dL'), "sex": "Male"},
        {"age": (71, 'years'), "creatinine": (1.0, 'mg/dL'), "sex": "Female"},
    ]
    # {'age': [49, 'years'], 'creatinine': [10.6, 'mg/dL'], 'sex': 'Male'}
    # {'age': [71, 'years'], 'creatinine': [1.0, 'mg/dL'], 'sex': 'Female'}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = mrdr_gfr_explanation(input_variables)
        print(result)
        print("-" * 50)
