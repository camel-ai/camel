"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function add_2_weeks_explanation
- translation

Date: March 2025
"""

from datetime import datetime, timedelta


def add_2_weeks_explanation(input_data):
    """
    Calculates the patient's estimated conception date and generates a detailed explanatory text.

    Parameters:
        input_data (dict): A dictionary containing the following key-value pairs:
            - "cycle_length" (int): The cycle length of the patient's menstrual period.
            - "menstrual_date" (date): The patient's menstrual date in the format "%m/%d/%Y".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's estimated conception date.

    Notes:
        - None

    Example:
        add_2_weeks_explanation({"cycle_length": 20, "menstrual_date": "01/21/2004"})
        output: ""
    """

    input_date_str = input_data["menstrual_date"]
    cycle_length = input_data["cycle_length"]
    
    explanation = "The patient's estimated date of conception based on their last period is computed by adding to 2 weeks to the patient's last menstrual period date. "
    explanation += f"The patient's last menstrual period was {input_date_str}. \n"

    input_date = datetime.strptime(input_date_str, "%m/%d/%Y")
    future_date = input_date + timedelta(weeks=2)

    explanation += f"Hence, the estimated date of conception after adding 2 weeks to the patient's last menstrual period date is {future_date.strftime('%m/%d/%Y')}. \n"

    return {"Explanation": explanation, "Answer": future_date.strftime('%m/%d/%Y')}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "cycle_length": 20,
            "menstrual_date": "01/21/2004",
        },
        {
            "cycle_length": 25,
            "menstrual_date": "11/06/2005",
        },
    ]

    # {'cycle length': 20, 'Last menstrual date': '01/21/2004'}
    # {'cycle length': 25, 'Last menstrual date': '11/06/2005'}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = add_2_weeks_explanation(input_variables)
        print(result)
        print("-" * 50)
