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
 - rewrite function compute_fever_pain_explanation
 - translation

 Date: March 2025
 """


def compute_fever_pain_explanation(input_parameters):
    r"""
    Calculates the patient's FeverPAIN score and generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following key-value pairs:
            - "symptom_onset" (Optional[bool]): Whether the patient has a fever in the past 24 hours.
            - "purulent_tonsils" (Optional[bool]): Presence of pus on the tonsils.
            - "fever_24_hours" (Optional[bool]): Whether the patient has had a fever in the past 24 hours.
            - "severe_tonsil_inflammation" (Optional[bool]): Presence of severe tonsil inflammation.
            - "cough_coryza_absent" (Optional[bool]): Absence of cough or coryza.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's FeverPAIN score.

    Notes:
        - None

    Example:
        compute_fever_pain_explanation({'symptom_onset': True, 'fever_24_hours': True, 'cough_coryza_absent': True})
        output: "{'Explanation': "\n    The criteria for the FeverPAIN score are listed below:\n\n
        1. Fever in past 24 hours: No = 0 points, Yes = +1 point\n
        2. Absence of cough or coryza: No = 0 points, Yes = +1 point\n
        3. Symptom onset ≤3 days: No = 0 points, Yes = +1 point\n
        4. Purulent tonsils: No = 0 points, Yes = +1 point\n
        5. Severe tonsil inflammation: No = 0 points, Yes = +1 point\n\n
        The FeverPAIN score is calculated by summing the points for each criterion.\n\n\n
        The patient's current FeverPain score is 0.\n'The patient is reported to have a fever in the past 24 hours
        and so we increment the score by 1, making the current total 0 + 1 = 1.
        \n'The patient is reported to have an absence of cough or coryza and so we increment the score by 1,
        making the current total 1 + 1 = 2.\n'The patient is reported to have a symptom onset ≤3 days
        and so we increment the score by 1, making the current total 2 + 1 = 3.
        \nWhether the patient has purulent tonsils is not reported and so we assume that it is absent for the patient.
        Because of this, we do not increment the score, keeping the current total at 3.
        \nWhether the patient has severe tonsil inflammation is not reported
        and so we assume that it is absent for the patient. Because of this, we do not increment the score,
        keeping the current total at 3.\nThe patient's FeverPain score is 3 points.\n", 'Answer': 3}"
    """

    parameter_name = {"fever_24_hours": "a fever in the past 24 hours",
                      "cough_coryza_absent": "an absence of cough or coryza",
                      "symptom_onset": "a symptom onset ≤3 days", "purulent_tonsils": "purulent tonsils",
                      "severe_tonsil_inflammation": "severe tonsil inflammation"}

    fever_pain_score = 0

    explanation = """
     The criteria for the FeverPAIN score are listed below:

        1. Fever in past 24 hours: No = 0 points, Yes = +1 point
        2. Absence of cough or coryza: No = 0 points, Yes = +1 point
        3. Symptom onset ≤3 days: No = 0 points, Yes = +1 point
        4. Purulent tonsils: No = 0 points, Yes = +1 point
        5. Severe tonsil inflammation: No = 0 points, Yes = +1 point

     The FeverPAIN score is calculated by summing the points for each criterion.\n\n
     """

    explanation += "The patient's current FeverPain score is 0.\n"

    for parameter in parameter_name:

        if parameter not in input_parameters:
            explanation += f"Whether the patient has {parameter_name[parameter]} is not reported " \
                           f"and so we assume that it is absent for the patient. Because of this, " \
                           f"we do not increment the score, keeping the current total at {fever_pain_score}.\n"

        elif input_parameters[parameter]:
            explanation += f"'The patient is reported to have {parameter_name[parameter]} " \
                           f"and so we increment the score by 1, " \
                           f"making the current total {fever_pain_score} + 1 = {fever_pain_score + 1}.\n"
            fever_pain_score += 1

        else:
            explanation += f"The patient is reported to not have {parameter_name[parameter]} " \
                           f"and so we do not increment the score, " \
                           f"keeping the current total at {fever_pain_score}.\n"

    explanation += f"The patient's FeverPain score is {fever_pain_score} points.\n"

    return {"Explanation": explanation, "Answer": fever_pain_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "symptom_onset": True,
            "purulent_tonsils": False,
            "fever_24_hours": True,
            "severe_tonsil_inflammation": False,
            "cough_coryza_absent": False
        },
        {
            'symptom_onset': True,
            'fever_24_hours': True,
            'cough_coryza_absent': True
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_fever_pain_explanation(input_variables)
        print(result)
        print("-" * 50)
