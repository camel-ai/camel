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
- rewrite function ckd_epi_2021
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion,
    age_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def ckd_epi_2021(input_parameters):
    r"""
    Calculates the patient's Glomerular Filtration Rate (GFR) and
    generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following
        key-value pairs:
            - "sex" (str): The patient's gender, which can be either "Male"
            or "Female".
            - "creatinine" (tuple): The patient's height information in the
            format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height,
                which can be "cm" (centimeters) or "in" (inches).
            - "age" (tuple): The patient's albumin concentration in the
            format (value, unit).
                - Value (float): Age.
                - Unit (str): The unit can be "months", "years".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's Glomerular Filtration Rate (GFR).

    Notes:
        - None

    Example:
        ckd_epi_2021({
            'sex': 'Male',
            'age': (17, 'years'),
            'creatinine': (3.7, 'mg/dL')
        })

        output: "{'Explanation': "The formula for computing GFR is 142 x (
        Scr/A)**B x 0.9938**age x (gender_coeffcient), where the **
        indicates an exponent operation, Scr is the concentration of serum
        creatinine in mg/dL and gender_coefficient is 1.012 if the patient
        is female, else the coeffient is 1. The coefficients A and B are
        dependent on the patient's gender and the patient's creatinine
        concentration.\nThe patient is 17 years old. The patient's gender is
        Male, and so the patient's gender coefficient is 1.0.\nThe
        concentration of Serum Creatinine is 3.7 mg/dL. Because the
        patient's gender is male and the creatinine concentration is
        greater than or equal to 0.9 mg/dL, A = 0.9 and B = -1.2.\nPlugging
        in these values, we get 142 * (3.7/0.9)**-1.2 * 0.9938**17 *
        1.0 = 23.422.\nHence, the GFR value is 23.422 ml/min/1.73 m².\n",
        'Answer': 23.422}"
    """

    age = age_conversion(input_parameters["age"])
    gender = input_parameters["sex"]
    creatinine_val, creatinine_label = (
        input_parameters["creatinine"][0],
        input_parameters["creatinine"][1],
    )

    creatinine_val_exp, creatinine_val = conversion_explanation(
        creatinine_val,
        "creatinine",
        113.12,
        None,
        creatinine_label,
        "mg/dL",
    )

    if creatinine_val <= 0.7 and gender == "Female":
        a = 0.7
        b = -0.241

    elif creatinine_val <= 0.9 and gender == "Male":
        a = 0.9
        b = -0.302

    elif creatinine_val > 0.7 and gender == "Female":
        a = 0.7
        b = -1.2

    elif creatinine_val > 0.9 and gender == "Male":
        a = 0.9
        b = -1.2

    if gender == "Female":
        gender_coefficient = 1.012
    else:
        gender_coefficient = 1

    return 142 * (creatinine_val / a) ** b * 0.9938**age * gender_coefficient


def ckd_epi_2021_explanation(input_parameters):
    explanation = (
        "The formula for computing GFR is 142 x (Scr/A)**B x "
        "0.9938**age x (gender_coeffcient), where the ** indicates "
        "an exponent operation, Scr is the concentration of serum "
        "creatinine in mg/dL and gender_coefficient is 1.012 if "
        "the patient is female, else the coeffient is 1. The "
        "coefficients A and B are dependent on the patient's "
        "gender and the patient's creatinine concentration.\n"
    )

    age_explanation, age = age_conversion_explanation(input_parameters["age"])
    gender = input_parameters["sex"]

    explanation += age_explanation
    explanation += f"The patient's gender is {gender}, "

    if gender == "Female":
        gender_coefficient = 1.012
        explanation += (
            f"and so the patient's gender coefficient is "
            f"{gender_coefficient}.\n"
        )
    else:
        gender_coefficient = 1.000
        explanation += (
            f"and so the patient's gender coefficient is "
            f"{gender_coefficient}.\n"
        )

    creatinine_val, creatinine_label = (
        input_parameters["creatinine"][0],
        input_parameters["creatinine"][1],
    )
    creatinine_val_exp, creatinine_val = conversion_explanation(
        creatinine_val,
        "Serum Creatinine",
        113.12,
        None,
        creatinine_label,
        "mg/dL",
    )

    explanation += creatinine_val_exp

    if creatinine_val <= 0.7 and gender == "Female":
        explanation += (
            "Because the patient's gender is female and the "
            "creatinine concentration is less than or equal to "
            "0.7 mg/dL, A = 0.7 and B = -0.241.\n"
        )
        a = 0.7
        b = -0.241

    elif creatinine_val <= 0.9 and gender == "Male":
        explanation += (
            "Because the patient's gender is male and the "
            "creatinine concentration is less than or equal to "
            "0.9 mg/dL, A = 0.7 and B = -0.302.\n"
        )
        a = 0.7
        b = -0.302

    elif creatinine_val > 0.7 and gender == "Female":
        explanation += (
            "Because the patient's gender is female and the "
            "creatinine concentration is greater than or equal "
            "to 0.7 mg/dL, A = 0.7 and B = -1.2.\n"
        )
        a = 0.7
        b = -1.2

    elif creatinine_val > 0.9 and gender == "Male":
        explanation += (
            "Because the patient's gender is male and the "
            "creatinine concentration is greater than or equal "
            "to 0.9 mg/dL, A = 0.9 and B = -1.2.\n"
        )
        a = 0.9
        b = -1.2

    result = round_number(
        142 * (creatinine_val / a) ** b * 0.9938**age * gender_coefficient
    )

    explanation += (
        f"Plugging in these values, we get 142 * ("
        f"{creatinine_val}/{a})**{b} * {0.9938}**{age} * "
        f"{gender_coefficient} = {result}.\n"
    )
    explanation += f"Hence, the GFR value is {result} ml/min/1.73 m².\n"

    return {"Explanation": explanation, "Answer": result}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {'sex': 'Male', 'age': (17, 'years'), 'creatinine': (3.7, 'mg/dL')}
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = ckd_epi_2021_explanation(input_variables)
        print(result)
        print("-" * 50)
