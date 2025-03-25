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
- rewrite function compute_glasgow_coma_score_explanation
- translation

Date: March 2025
"""


def compute_glasgow_coma_score_explanation(input_variables):
    r"""
    Calculates the patient's Glasgow Coma Score and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "insulin" (array): The patient's insulin level in the format (value, unit).
                - Value (float): The value of insulin level.
                - Unit (str): The unit of insulin level, eg. "µIU/mL", "pmol/L", and so on.
            - "glucose" (array): The patient's blood glucose level in the format (value, unit).
                - Value (float): The value of blood glucose level.
                - Unit (str): The unit of blood glucose level, eg. "mmol/L", "mEq/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's Homeostatic Model Assessment for Insulin Resistance.

    Notes:
        - None

    Example:
        compute_glasgow_coma_score_explanation({'insulin': [756.0, 'pmol/L'], 'glucose': [97.3, 'mg/dL']})
        output: "{'Explanation': "\n    The Glasgow Coma Scale (GCS) for assessing a patient’s level of consciousness is
         shown below:\n    \n       1. Best Eye Response: Spontaneously = +4 points, To verbal command = +3 points,
         To pain = +2 points, \n       No eye opening = +1 point\n       2. Best Verbal Response: Oriented = +5 points,
         Confused = +4 points, Inappropriate words = +3 points, \n       Incomprehensible sounds = +2 points,
         No verbal response = +1 point\n       3. Best Motor Response: Obeys commands = +6 points,
         Localizes pain = +5 points, Withdrawal from pain = +4 points,\n
         Flexion to pain = +3 points, Extension to pain = +2 points, No motor response = +1 point\n\n
         For each criteria, if a patient's value is not mentioned/not testable in the note, \n
         we assume that it gets the full score for that attribute.  \n
         The total GCS score is calculated by summing the points for each of the three components.\n\n\n
         The current glasgow coma score is 0.\nBased on the patient note,
         the best eye response for the patient is 'eye opening to pain',
         and so we add 2 points making the current total 0 + 2 = 2.\nBased on the patient note,
         the best verbal response for the patient is 'oriented',
         and so we add 5 points making the current total 2 + 5 = 7.\nBased on the patient note,
         the best motor response for the patient is 'localizes pain',
         and so we add 5 points making the current total 7 + 5 = 12.\nHence,
         the patient's glasgow coma score is 12.\n", 'Answer': 12}"
    """

    glasgow_dictionary = {"best_eye_response":
                              {"eyes open spontaneously": 4,
                               "eye opening to verbal command": 3,
                               "eye opening to pain": 2,
                               "no eye opening": 1,
                               "not testable": 4},
                          "best_verbal_response":
                              {"oriented": 5,
                               "confused": 4,
                               "inappropriate words": 3,
                               "incomprehensible sounds": 2,
                               "no verbal response": 1,
                               "not testable": 4},
                          "best_motor_response":
                              {"obeys commands": 6,
                               "localizes pain": 5,
                               "withdrawal from pain": 4,
                               "flexion to pain": 3,
                               "extension to pain": 2,
                               "no motor response": 1},
                          }

    best_eye_response_value = input_variables["best_eye_response"]
    best_verbal_response_value = input_variables["best_verbal_response"]
    best_motor_response_value = input_variables["best_motor_response"]

    eye_score = glasgow_dictionary["best_eye_response"][best_eye_response_value]
    verbal_score = glasgow_dictionary["best_verbal_response"][best_verbal_response_value]
    motor_score = glasgow_dictionary["best_motor_response"][best_motor_response_value]

    glasgow_score = 0

    eye_point = "points" if eye_score == 0 or eye_score > 1 else "point"
    verbal_point = "points" if verbal_score == 0 or verbal_score > 1 else "point"
    motor_point = "points" if motor_score == 0 or motor_score > 1 else "point"

    explanation = """
    The Glasgow Coma Scale (GCS) for assessing a patient’s level of consciousness is shown below:
    
       1. Best Eye Response: Spontaneously = +4 points, To verbal command = +3 points, To pain = +2 points, 
       No eye opening = +1 point
       2. Best Verbal Response: Oriented = +5 points, Confused = +4 points, Inappropriate words = +3 points, 
       Incomprehensible sounds = +2 points, No verbal response = +1 point
       3. Best Motor Response: Obeys commands = +6 points, Localizes pain = +5 points, Withdrawal from pain = +4 points,
        Flexion to pain = +3 points, Extension to pain = +2 points, No motor response = +1 point

    For each criteria, if a patient's value is not mentioned/not testable in the note, 
    we assume that it gets the full score for that attribute.  
    The total GCS score is calculated by summing the points for each of the three components.\n\n
    """

    explanation += "The current glasgow coma score is 0.\n" 

    if best_eye_response_value == 'not testable': 
        explanation += f"Based on the patient note, the best eye response for the patient is '{best_eye_response_value}'" \
                       f", and so we assume the the patient can open his or her eyes spontaneously. " \
                       f"Hence, we add {eye_score} {eye_point}, making the current total " \
                       f"{glasgow_score} + {eye_score} = {glasgow_score + eye_score}.\n"
        glasgow_score += eye_score
    else:
        explanation += f"Based on the patient note, the best eye response for the patient is '{best_eye_response_value}'" \
                       f", and so we add {eye_score} {eye_point} making the current total " \
                       f"{glasgow_score} + {eye_score} = {glasgow_score + eye_score}.\n"
        glasgow_score += eye_score

    if best_verbal_response_value == 'not testable': 
        explanation += f"Based on the patient note, the best verbal response for the patient is " \
                       f"'{best_verbal_response_value}', and so we assume the the patient's verbal response is oriented." \
                       f" Hence, we add {verbal_score} {verbal_point}, making the current total " \
                       f"{glasgow_score} + {verbal_score} = {glasgow_score + verbal_score}.\n"
        glasgow_score += verbal_score
    else:
        explanation += f"Based on the patient note, the best verbal response for the patient is " \
                       f"'{best_verbal_response_value}', and so we add {verbal_score} {verbal_point} " \
                       f"making the current total {glasgow_score} + {verbal_score} = {glasgow_score + verbal_score}.\n"
        glasgow_score += verbal_score
   
    explanation += f"Based on the patient note, the best motor response for the patient is " \
                   f"'{best_motor_response_value}', and so we add {motor_score} {motor_point} " \
                   f"making the current total {glasgow_score} + {motor_score} = {glasgow_score + motor_score}.\n"
    glasgow_score += motor_score
    explanation += f"Hence, the patient's glasgow coma score is {glasgow_score}.\n"

    return {"Explanation": explanation, "Answer": glasgow_score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "best_eye_response": "eye opening to pain",
            "best_verbal_response": "oriented",
            "best_motor_response": "localizes pain"
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_glasgow_coma_score_explanation(input_variables)
        print(result)
        print("-" * 50)
