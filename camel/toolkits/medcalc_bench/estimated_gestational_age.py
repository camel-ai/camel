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
- rewrite function targetweight_explanation
- translation

Date: March 2025
"""

from datetime import datetime


def compute_gestational_age_explanation(input_parameters):
    r"""
    Calculates the patient's gestational age and generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following key-value pairs:
            - "current_date" (date): The current date in the format "%m/%d/%Y".
            - "menstrual_date" (date): The patient's menstrual date in the format "%m/%d/%Y".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's gestational age.

    Notes:
        - None

    Example:
        compute_gestational_age_explanation({"current_date": "04/29/2022", "menstrual_date": "01/06/2022"})
        output: "{'Explanation': "To compute the estimated gestational age,
        we compute the number of weeks and days apart today's date is from the patient's last menstrual period date.
        The current date is 04/29/2022 and the patient's last menstrual period date was 01/06/2022.
        The gap between these two dates is 16 weeks and 1 days. Hence,
        the estimated gestational age is 16 weeks and 1 days. ", 'Answer': ('16 weeks', '1 days')}"
    """

    date2 = input_parameters["current_date"]
    date1 = input_parameters["menstrual_date"]

    explanation = "To compute the estimated gestational age, we compute the number of weeks and days " \
                  "apart today's date is from the patient's last menstrual period date. "
    explanation += f"The current date is {date2} and the patient's last menstrual period date was {date1}. "

    datetime1 = datetime.strptime(date1, "%m/%d/%Y")
    datetime2 = datetime.strptime(date2, "%m/%d/%Y")

    delta = abs(datetime2 - datetime1)

    weeks = delta.days // 7
    days = delta.days % 7

    if weeks == 0:
        explanation += f"The gap between these two dates is {days} days. " \
                       f"Hence, the estimated gestational age is {days} days. "
    elif days == 0:
        explanation += f"The gap between these two dates is {weeks} weeks. " \
                       f"Hence, the estimated gestational age is {weeks} weeks. "
    else:
        explanation += f"The gap between these two dates is {weeks} weeks and {days} days. " \
                       f"Hence, the estimated gestational age is {weeks} weeks and {days} days. "

    return {
        "Explanation": explanation,
        "Answer": (f"{weeks} weeks", f"{days} days"),
    }


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "current_date": "04/29/2022",
            "menstrual_date": "01/06/2022",
        },
        {
            "current_date": "11/15/2005",
            "menstrual_date": "06/16/2005",
        },
    ]

    # {'Current Date': '04/29/2022', 'Last menstrual date': '01/06/2022'}
    # {'Current Date': '11/15/2005', 'Last menstrual date': '06/16/2005'}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_gestational_age_explanation(input_variables)
        print(result)
        print("-" * 50)
