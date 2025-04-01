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
- rewrite function compute_cardiac_index_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_cardiac_index_explanation(input_variables):
    r"""
    Calculates the patient's cardiac index and generates a detailed
    explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following
        key-value pairs:
            - "elevated_risk_surgery" (boolean): Elevated-risk surgery (
            intraperitoneal, intrathoracic, or suprainguinal vascular).
            - "ischemetic_heart_disease" (boolean): History of ischemic
            heart disease (history of myocardial infarction, positive
            exercise test, current chest pain due to myocardial ischemia,
            use of nitrate therapy, or ECG with pathological Q waves).
            - "congestive_heart_failure" (boolean): History of congestive
            heart failure (pulmonary edema, bilateral rales or S3 gallop,
            paroxysmal nocturnal dyspnea, or chest x-ray showing pulmonary
            vascular redistribution).
            - "cerebrovascular_disease" (boolean): History of
            cerebrovascular disease (prior transient ischemic
            attack or stroke).
            - "pre_operative_insulin_treatment" (boolean): Pre-operative
            treatment with insulin.
            - "pre_operative_creatinine" (tuple): The patient's
            pre-operative creatinine information in the format (value, unit).
                - Value (float): The value of pre-operative creatinine.
                - Unit (str): The unit of creatinine,
                which can be "mg/dL", "μmol/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's cardiac index.

    Notes:
        - None

    Example:
        compute_cardiac_index_explanation({
            "elevated_risk_surgery": False,
            "ischemetic_heart_disease": False,
            "congestive_heart_failure": False,
            "cerebrovascular_disease": False,
            "pre_operative_insulin_treatment": False,
            "pre_operative_creatinine": (1.0, "mg/dL"),
        })

        output: "{'Explanation': "\n    The criteria for the Revised Cardiac
        Risk Index (RCRI) are listed below:\n    \n       1. Elevated-risk
        surgery (intraperitoneal, intrathoracic, \n       or suprainguinal
        vascular): No = 0 points, Yes = +1 point\n       2. History of
        ischemic heart disease (history of myocardial \n       infarction,
        positive exercise test, current chest pain due to \n
        myocardial ischemia, use of nitrate therapy, or ECG with pathological
        \n       Q waves): No = 0 points, Yes = +1 point\n       3. History
        of congestive heart failure (pulmonary edema, bilateral \n
        rales or S3 gallop, paroxysmal nocturnal dyspnea, or chest x-ray
        \n       showing pulmonary vascular redistribution): \n       No = 0
        points, Yes = +1 point\n       4. History of cerebrovascular disease
        (prior transient ischemic \n       attack or stroke): No = 0 points,
        Yes = +1 point\n       5. Pre-operative treatment with insulin: No = 0
        points, Yes = +1 point\n       6. Pre-operative creatinine >2 mg/dL
        (176.8 μmol/L): No = 0 points, \n       Yes = +1 point\n    \n    The
        total score is calculated by summing the points for each criterion.\n
        \n\n    The current cardiac risk index is 0.\nThe patient note reports
        elevated risk surgery as 'absent' for the patient. This means that the
        total score remains unchanged at 0.\nThe patient note reports
        ischemetic heart disease as 'absent' for the patient. This means that
        the total score remains unchanged at 0.\nThe patient note reports
        congestive heart failure as 'absent' for the patient. This means that
        the total score remains unchanged at 0.\nThe patient note reports
        cerebrovascular disease as 'absent' for the patient. This means that
        the total score remains unchanged at 0.\nThe patient note reports
        pre-operative insulin treatment as 'absent' for the patient. This
        means that the total score remains unchanged at 0.\nThe concentration
        of Pre-Operative Creatinine is 1.0 mg/dL. The patient has pre-operative
         creatinine <= 2 mg/dL, so we keep the score the same at 0.\n\nThe
         cardiac risk index score is 0.\n", 'Answer': 0}"
    """

    # List of parameters and their default values
    parameters = {
        'elevated_risk_surgery': "elevated risk surgery",
        'ischemetic_heart_disease': "ischemetic heart disease",
        'congestive_heart_failure': "congestive heart failure",
        'cerebrovascular_disease': "cerebrovascular disease",
        'pre_operative_insulin_treatment': "pre-operative insulin treatment",
        'pre_operative_creatinine': "pre-operative creatinine",
    }

    output = """
    The criteria for the Revised Cardiac Risk Index (RCRI) are listed below:
    
       1. Elevated-risk surgery (intraperitoneal, intrathoracic, 
       or suprainguinal vascular): No = 0 points, Yes = +1 point
       2. History of ischemic heart disease (history of myocardial 
       infarction, positive exercise test, current chest pain due to 
       myocardial ischemia, use of nitrate therapy, or ECG with pathological 
       Q waves): No = 0 points, Yes = +1 point
       3. History of congestive heart failure (pulmonary edema, bilateral 
       rales or S3 gallop, paroxysmal nocturnal dyspnea, or chest x-ray 
       showing pulmonary vascular redistribution): 
       No = 0 points, Yes = +1 point
       4. History of cerebrovascular disease (prior transient ischemic 
       attack or stroke): No = 0 points, Yes = +1 point
       5. Pre-operative treatment with insulin: No = 0 points, Yes = +1 point
       6. Pre-operative creatinine >2 mg/dL (176.8 μmol/L): No = 0 points, 
       Yes = +1 point
    
    The total score is calculated by summing the points for each criterion.\n\n
    """

    # Initializing scores and output explanation
    cri = 0
    output += "The current cardiac risk index is 0.\n"

    for param_name, full_name in parameters.items():
        param_value = input_variables.get(param_name)

        # If parameter is missing, assume it as False
        if param_value is None:
            output += (
                f"The patient note does not mention about {full_name} "
                f"and is assumed to be absent. "
            )
            input_variables[param_name] = False
            param_value = False
        elif param_name != 'pre_operative_creatinine':
            value = 'absent' if not param_value else 'present'
            output += (
                f"The patient note reports {full_name} as '{value}' "
                f"for the patient. "
            )
        elif param_name == 'pre_operative_creatinine':
            explanation, param_value = conversion_explanation(
                param_value[0],
                "Pre-Operative Creatinine",
                113.12,
                None,
                param_value[1],
                "mg/dL",
            )
            input_variables['pre_operative_creatinine'] = [
                param_value,
                "mg/dL",
            ]
            output += explanation

        if param_name == 'pre_operative_creatinine':
            if param_value > 2:
                output += (
                    f"The patient has pre-operative creatinine > 2 "
                    f"mg/dL, so we increment the score by one and the "
                    f"current total will be {cri} + 1 = {cri + 1}.\n"
                )
                cri += 1
            else:
                output += (
                    f"The patient has pre-operative creatinine <= 2 "
                    f"mg/dL, so we keep the score the same at {cri}.\n"
                )
            continue

        if param_value:
            output += (
                f"This means that we increment the score by one and "
                f"the current total will be {cri} + 1 = {cri + 1}.\n"
            )
            cri += 1
        else:
            output += (
                f"This means that the total score "
                f"remains unchanged at {cri}.\n"
            )

    output += f"\nThe cardiac risk index score is {cri}.\n"

    return {"Explanation": output, "Answer": cri}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "elevated_risk_surgery": False,
            "ischemetic_heart_disease": False,
            "congestive_heart_failure": False,
            "cerebrovascular_disease": False,
            "pre_operative_insulin_treatment": False,
            "pre_operative_creatinine": (1.0, "mg/dL"),
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_cardiac_index_explanation(input_variables)
        print(result)
        print("-" * 50)
