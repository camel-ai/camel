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
- rewrite function add_40_weeks_explanation
- translation

Date: March 2025
"""

from datetime import datetime, timedelta


def add_40_weeks_explanation(input_data):
    r"""
    Calculates the patient's estimated due date and generates a detailed explanatory text.

    Parameters:
        input_data (dict): A dictionary containing the following key-value pairs:
            - "cycle_length" (int): The cycle length of the patient's menstrual period.
            - "menstrual_date" (date): The patient's menstrual date in the format "%m/%d/%Y".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's estimated due date.

    Notes:
        - None

    Example:
        add_2_weeks_explanation({"cycle_length": 21,"menstrual_date": "09/17/2011",})

        output: "{'Explanation': "The patient's estimated due date based on their last period is computed by
        using Naegele's Rule. Using Naegele's Rule, we add 40 weeks to the patient's last menstrual period date.
        We then add or subtract days from the patient's estimated due date depending on how many more or less days
        a patient's cycle length is from the standard 28 days. \nThe patient's last menstrual period was 09/17/2011.
        \nThe date after adding 40 weeks to the patient's last menstrual period date is 06/23/2012.
        \nBecause the patient's cycle length is 21 days, this means that we must subtract 7 days
        from the patient's estimate due date.
        Hence, the patient's estimated due date is 06/30/2012. \n", 'Answer': '06/30/2012'}"
    """

    input_date_str = input_data["menstrual_date"]
    cycle_length = input_data["cycle_length"]
    
    explanation = "The patient's estimated due date based on their last period is computed by using Naegele's Rule. "
    explanation += "Using Naegele's Rule, we add 40 weeks to the patient's last menstrual period date. " \
                   "We then add or subtract days from the patient's estimated due date " \
                   "depending on how many more or less days a patient's cycle length is from the standard 28 days. \n"
    explanation += f"The patient's last menstrual period was {input_date_str}. \n"

    input_date = datetime.strptime(input_date_str, "%m/%d/%Y")
    future_date = input_date + timedelta(weeks=40)

    explanation += f"The date after adding 40 weeks to the patient's last menstrual period date is {future_date.strftime('%m/%d/%Y')}. \n"

    if cycle_length == 28:
        explanation += f"Because the patient's cycle length is 28 days, we do not make any changes to the date. " \
                       f"Hence, the patient's estimated due date is {future_date.strftime('%m/%d/%Y')}. \n"
    elif cycle_length < 28:
        cycle_length_gap = abs(cycle_length - 28)
        future_date = future_date + timedelta(days=cycle_length_gap)
        explanation += f"Because the patient's cycle length is {abs(cycle_length)} days, " \
                       f"this means that we must subtract {cycle_length_gap} days from the patient's estimate due date." \
                       f" Hence, the patient's estimated due date is {future_date.strftime('%m/%d/%Y')}. \n"
    elif cycle_length > 28:
        cycle_length_gap = abs(cycle_length - 28)
        future_date = future_date + timedelta(days=cycle_length_gap)
        explanation += f"Because the patient's cycle length is {cycle_length} days, " \
                       f"this means that we must add {cycle_length_gap} days to the patient's estimate due date. " \
                       f"Hence, the patient's estimated due date is {future_date.strftime('%m/%d/%Y')}. \n"

    return {"Explanation": explanation, "Answer": future_date.strftime('%m/%d/%Y')}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "cycle_length": 21,
            "menstrual_date": "09/17/2011",
        },
        {
            "cycle_length": 28,
            "menstrual_date": "12/03/2023",
        },
    ]

    # {'cycle length': 21, 'Last menstrual date': '09/17/2011'}
    # {'cycle length': 28, 'Last menstrual date': '12/03/2023'}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = add_40_weeks_explanation(input_variables)
        print(result)
        print("-" * 50)
