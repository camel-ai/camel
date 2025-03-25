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
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function compute_ldl_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_ldl_explanation(input_parameters):
    r"""
    Calculates the patient's LDL cholestrol concentration and generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following key-value pairs:
            - "hdl_cholestrol" (tuple): The concentration of HDL cholestrol in the format (value, unit).
                - Value (float): The value of HDL cholestrol.
                - Unit (str): The unit of HDL cholestrol, eg. "µIU/mL", "pmol/L", and so on.
            - "triglycerides" (tuple): The concentration of triglycerides in the format (value, unit).
                - Value (float): The concentration of triglycerides.
                - Unit (str): The unit of triglycerides, eg. "mmol/L", "mEq/L", and so on.
            - "total_cholestrol" (tuple): The concentration of total cholestrol in the format (value, unit).
                - Value (float): The value of total cholestrol.
                - Unit (str): The unit of total cholestrol, eg. "mmol/L", "mEq/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's LDL cholestrol concentration.

    Notes:
        - None

    Example:
        compute_homa_ir_explanation({"hdl_cholestrol": (37.0, 'mg/dL'),"triglycerides": (205.0, 'mg/dL'),"total_cholestrol": (210.0, 'mg/dL')})

        output: "{'Explanation': "To compute the patient's LDL cholestrol, apply the following formula: LDL cholesterol = total cholesterol - HDL - (triglycerides / 5), where the units for total cholestrol, HDL cholestrol, and triglycerides are all mg/dL.\nThe concentration of total cholestrol is 210.0 mg/dL. \nThe concentration of hdl cholestrol is 37.0 mg/dL. \nThe concentration of triglycerides is 205.0 mg/dL. \nPlugging in these values will give us 210.0 mg/dL - 37.0 mg/dL - (205.0/5) mg/dL = 132.0 mg/dL.\nThe patients concentration of LDL cholestrol is 132.0 mg/dL.\n", 'Answer': 132.0}"
    """

    explanation = "To compute the patient's LDL cholestrol, apply the following formula: LDL cholesterol = total cholesterol - HDL - (triglycerides / 5), where the units for total cholestrol, HDL cholestrol, and triglycerides are all mg/dL.\n"

    total_cholestrol_exp, total_cholestrol = conversion_explanation(
        input_parameters["total_cholestrol"][0],
        "total cholestrol",
        386.654,
        None,
        input_parameters["total_cholestrol"][1],
        "mg/dL",
    )
    hdl_cholestrol_exp, hdl_cholestrol = conversion_explanation(
        input_parameters["hdl_cholestrol"][0],
        "hdl cholestrol",
        386.654,
        None,
        input_parameters["hdl_cholestrol"][1],
        "mg/dL",
    )
    triglycerides_exp, triglycerides = conversion_explanation(
        input_parameters["triglycerides"][0],
        "triglycerides",
        861.338,
        None,
        input_parameters["triglycerides"][1],
        "mg/dL",
    )

    explanation += total_cholestrol_exp + '\n'
    explanation += hdl_cholestrol_exp + '\n'
    explanation += triglycerides_exp + '\n'

    answer = round_number(
        total_cholestrol - hdl_cholestrol - (triglycerides / 5)
    )

    explanation += f"Plugging in these values will give us {total_cholestrol} mg/dL - {hdl_cholestrol} mg/dL - ({triglycerides}/5) mg/dL = {answer} mg/dL.\n"

    explanation += (
        f"The patients concentration of LDL cholestrol is {answer} mg/dL.\n"
    )

    return {"Explanation": explanation, "Answer": answer}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "hdl_cholestrol": (37.0, 'mg/dL'),
            "triglycerides": (205.0, 'mg/dL'),
            "total_cholestrol": (210.0, 'mg/dL'),
        },
        {
            "total_cholestrol": (165.0, 'mg/dL'),
            "triglycerides": (104.0, 'mg/dL'),
            "hdl_cholestrol": (50.0, 'mg/dL'),
        },
    ]
    # {'high-density lipoprotein cholesterol': [37.0, 'mg/dL'], 'Triglycerides': [205.0, 'mg/dL'], 'Total cholesterol': [210.0, 'mg/dL']}
    # {'Total cholesterol': [165.0, 'mg/dL'], 'Triglycerides': [104.0, 'mg/dL'], 'high-density lipoprotein cholesterol': [50.0, 'mg/dL']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_ldl_explanation(input_variables)
        print(result)
        print("-" * 50)
