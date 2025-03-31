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
- rewrite function framingham_risk_score_explanation
- translation

Date: March 2025
"""

import math

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def framingham_risk_score_explanation(input_parameters):
    age_exp, age = age_conversion_explanation(input_parameters["age"])
    gender = input_parameters["sex"]

    explanation = f"The patient's gender is {gender}.\n"

    if gender == "Male":
        explanation += (
            "For males, the formula for computing the framingham "
            "risk score is 52.00961 * ln(age) + 20.014077 * ln("
            "total_cholestrol) + -0.905964 * ln(hdl_cholestrol) "
            "+ 1.305784 * ln(sys_bp) + 0.241549 * bp_medicine + "
            "12.096316 * smoker + -4.605038 * ln(age) * "
            "ln(total_cholestrol) + -2.84367 * ln(age_smoke) "
            "* smoker + -2.93323 * ln(age) * "
            "ln(age) -  172.300168, where 'bp_medicine' is a "
            "binary variable for whether a patient's blood "
            "pressure is being treated with medicine, total "
            "cholestrol and hdl cholestrol are in mg/dL, "
            "and 'smoker' is whether the patient is a "
            "smoker or not.\n"
        )
        explanation += (
            "From this, we use the risk score to get "
            "likelihood for a patient getting myocardial "
            "infraction (MI) or dying in the next 10 years: "
            "1 - 0.9402^exp(risk_score), where risk_score "
            "is the value from the formula above.\n"
        )
        explanation += age_exp

        if age > 70:
            age_smoke = 70
            explanation += (
                "For male patient's whose age is greater "
                "than 70, the age variable is set to 70 within "
                "the 'age' term for the β x ln(Age) x "
                "Smoker term.\n"
            )
        else:
            age_smoke = age

    if gender == "Female":
        explanation += (
            "For females, the formula for computing the "
            "framingham risk score is 31.764001 * ln(age) + "
            "22.465206 * ln(total_cholestrol) - 1.187731 * ln("
            "hdl_cholestrol) + 2.552905 * ln(sys_bp) + 0.420251 "
            "* bp_medicine + 13.07543 * smoker + -5.060998 "
            "* ln(age) * ln(total_cholestrol) + -2.996945 * "
            "ln(age_smoke) * smoker - 146.5933061, where "
            "'bp_medicine' is a binary variable for whether "
            "a patient's blood pressure is being treated "
            "with medicine, total cholestrol and hdl cholestrol "
            "are in mg/dL, and 'smoker' is whether the "
            "patient is a smoker or not.\n"
        )
        explanation += (
            "From this, we use the risk score to get likelihood "
            "for a patient getting myocardial infraction (MI) "
            "or dying in the next 10 years: 1 - "
            "0.9402^exp(risk_score), where risk_score "
            "is the value from the formula above.\n"
        )
        explanation += age_exp

        if age > 78:
            age_smoke = 78
            explanation += (
                "For female patient's whose age is greater than "
                "78, the age variable is set to 78 "
                "within the 'age' variable for the "
                "β x ln(Age) x Smoker term.\n"
            )
        else:
            age_smoke = age

    if "smoker" in input_parameters:
        if input_parameters["smoker"]:
            explanation += (
                "The patient is a smoker, making the "
                "smoking variable equal to 1.\n"
            )
            smoker = 1
        else:
            explanation += (
                "The patient is not a smoker, making "
                "the smoking variable equal to 0.\n"
            )
            smoker = 0
    else:
        explanation += (
            "The note does not specify whether the patient is a "
            "smoker and so we assume this to be false, "
            "making the smoking variable equal to 0.\n"
        )
        smoker = 0

    sys_bp = input_parameters["sys_bp"][0]

    explanation += (
        f"The patient's systolic blood pressure is {sys_bp} mm Hg.\n"
    )

    if "bp_medicine" in input_parameters:
        if input_parameters["bp_medicine"]:
            explanation += (
                "The patient has been specified to "
                "take medication for treating their "
                "blood pressure, making the bp_medicine "
                "variable equal to 1.\n"
            )
            bp_medicine = 1
        else:
            explanation += (
                "The patient has been specified to not "
                "take medication for treating their blood "
                "pressure, making the bp_medicine variable "
                "equal to 0.\n"
            )
            bp_medicine = 0
    else:
        explanation += (
            "The note does not specify whether the patient "
            "takes medicine for treating blood pressure and "
            "so we assume this to be false, making the "
            "bp_medicine variable equal to 0.\n"
        )
        bp_medicine = 0

    total_cholestrol_exp, total_cholestrol = conversion_explanation(
        input_parameters["total_cholestrol"][0],
        "total cholestrol",
        386.65,
        None,
        input_parameters["total_cholestrol"][1],
        "mmol/L",
    )
    hdl_cholestrol_exp, hdl_cholestrol = conversion_explanation(
        input_parameters["hdl_cholestrol"][0],
        "hdl cholestrol",
        386.65,
        None,
        input_parameters["hdl_cholestrol"][1],
        "mmol/L",
    )

    explanation += total_cholestrol_exp + '\n'
    explanation += hdl_cholestrol_exp + '\n'

    if gender == "Male":
        risk_score = round(
            52.00961 * math.log(age)
            + 20.014077 * math.log(total_cholestrol)
            - 0.905964 * math.log(hdl_cholestrol)
            + 1.305784 * math.log(sys_bp)
            + 0.241549 * bp_medicine
            + 12.096316 * smoker
            - 4.605038 * (math.log(age) * math.log(total_cholestrol))
            - 2.84367 * (math.log(age_smoke) * smoker)
            - 2.93323 * (math.log(age) * math.log(age))
            - 172.300168,
            1,
        )
        percentage = round(1 - 0.9402 ** math.exp(risk_score), 1)
        explanation += (
            f"Plugging in these values will give us "
            f"the risk score:  52.00961 * ln({age}) "
            f"+ 20.014077 * ln({total_cholestrol}) + -0.905964 * "
            f"ln({hdl_cholestrol}) + 1.305784 * "
            f"ln({sys_bp}) + 0.241549 * {bp_medicine}  "
            f"+ 12.096316 * {smoker} + -4.605038 * "
            f"ln({age}) * ln({total_cholestrol}) + "
            f"-2.84367 * ln({age_smoke}) * {smoker} "
            f"+ -2.93323 * ln({age}) * ln({age}) -  "
            f"172.300168 = {risk_score}.\n"
        )
        explanation += (
            f"Plugging this into the MI risk equation "
            f"gives us 1 - 0.9402^exp({risk_score}) = "
            f"{percentage}. We then multiply this by a "
            f"100 to obtain the percentage which "
            f"gives us {percentage} * 100 = "
            f"{round(percentage * 100, 3)}%.\n"
        )
    else:
        risk_score = round(
            31.764001 * math.log(age)
            + 22.465206 * math.log(total_cholestrol)
            - 1.187731 * math.log(hdl_cholestrol)
            + 2.552905 * math.log(sys_bp)
            + 0.420251 * bp_medicine
            + 13.07543 * smoker
            - 5.060998 * (math.log(age) * math.log(total_cholestrol))
            - 2.996945 * (math.log(age_smoke) * smoker)
            - 146.5933061,
            1,
        )
        percentage = round(1 - 0.98767 ** math.exp(risk_score), 1)
        explanation += (
            f"Plugging in these values will "
            f"give us the risk score: 31.764001 * "
            f"ln({age}) + 22.465206 * ln({total_cholestrol}) - "
            f"1.187731 * "
            f"ln({hdl_cholestrol}) + 2.552905 * "
            f"ln({sys_bp}) + 0.420251 * {bp_medicine} "
            f"+ 13.07543 * {smoker} + -5.060998 * "
            f"ln({age}) * ln({total_cholestrol}) + "
            f"-2.996945 * ln({age_smoke}) * {smoker} - "
            f"146.5933061 = {risk_score}.\n"
        )
        explanation += (
            f"Plugging this into the MI risk formula "
            f"gives us 1 - 0.98767^exp({risk_score}) = "
            f"{percentage}. We then multiply this by a "
            f"100 to obtain the percentage which "
            f"gives us {percentage} * 100 = "
            f"{round(percentage * 100, 3)}%.\n"
        )

    explanation += (
        f"The patient's percentage of getting MI or dying is"
        f" {round(percentage * 100, 3)} %.\n"
    )

    return {"Explanation": explanation, "Answer": round(percentage * 100, 3)}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            'sex': 'Male',
            'age': (17, 'years'),
            'sys_bp': (70, "mm"),
            'dia_bp': (12, "Hg"),
            "smoker": True,
            "bp_medicine": True,
            "total_cholestrol": (210.0, 'mg/dL'),
            "hdl_cholestrol": (37.0, 'mg/dL'),
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = framingham_risk_score_explanation(input_variables)
        print(result)
        print("-" * 50)
