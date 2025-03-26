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
- rewrite function bazett_calculator_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number


def bazett_calculator_explanation(input_variables):
    r"""
    Calculates the patient's corrected QT interval using the Bazett Formula and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "heart_rate" (tuple): The patient's heart rate in the format (value, unit).
                - Value (float): The value of the patient's heart rate.
                - Unit (str): The unit of heart rate should be "beats per minute".
            - "qt_interval" (tuple): The QT interval of 330 msec.
                - Value (float): The value of QT interval.
                - Unit (str): The unit of QT interval, "msec".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's corrected QT interval using the Bazett Formula.

    Notes:
        - None

    Example:
        bazett_calculator_explanation({"heart_rate": (176, "beats per minute"),"qt_interval": (330, "msec"),})

        output: "{'Explanation': "The corrected QT interval using the Bazett formula is computed as
        QTc = QT interval / √ (RR interval), where the QT interval is in msec,
        and RR interval is given as 60/(heart rate).\nThe patient's heart rate is 176 beats per minute.
        \nThe QT interval is 330 msec.\nThe RR interval is computed as 60/(heart rate),
        and so the RR interval is 60/176 = 0.341.\nHence, plugging in these values,
        we will get 330/√(0.341) = 565.115.\nThe patient's corrected QT interval (QTc) is 565.115 msec. ",
        'Answer': 565.115}"
    """

    heart_rate = input_variables["heart_rate"][0]
    qt_interval = input_variables["qt_interval"][0]

    explanation = "The corrected QT interval using the Bazett formula is computed as " \
                  "QTc = QT interval / √ (RR interval), where the QT interval is in msec, " \
                  "and RR interval is given as 60/(heart rate).\n"

    explanation += f"The patient's heart rate is {heart_rate} beats per minute.\n"
    explanation += f"The QT interval is {qt_interval} msec.\n"

    rr_interval_sec = round_number(60 / heart_rate)
    explanation += f"The RR interval is computed as 60/(heart rate), " \
                   f"and so the RR interval is 60/{heart_rate} = {rr_interval_sec}.\n"

    qt_c = round_number(qt_interval/(rr_interval_sec ** 0.5))
    explanation += f"Hence, plugging in these values, we will get {qt_interval}/√({rr_interval_sec}) = {qt_c}.\n"

    explanation += f"The patient's corrected QT interval (QTc) is {qt_c} msec. "

    return {"Explanation": explanation, "Answer": qt_c}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "heart_rate": (176, "beats per minute"),
            "qt_interval": (330, "msec"),
        },
        {
            "heart_rate": (150, "beats per minute"),
            "qt_interval": (330, "msec"),
        },
    ]

    # {'Heart Rate or Pulse': [176, 'beats per minute'], 'QT interval': [330, 'msec']}
    # {'Heart Rate or Pulse': [150, 'beats per minute'], 'QT interval': [330, 'msec']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = bazett_calculator_explanation(input_variables)
        print(result)
        print("-" * 50)
