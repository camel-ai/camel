"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function weight_conversion_explanation
- translation

Date: March 2025
"""

from utils.height_conversion import height_conversion_explanation_in
from utils.rounding import round_number


def ibw_explanation(input_variables):
    """
    Calculates the patient's Ideal Body Weight (IBW) and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "height" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters), "in" (inches), or other supported units.
            - "sex" (str): The patient's gender, which can be either "Male" or "Female".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's ideal body weight (in kilograms).

    Notes:
        - Uses the `height_conversion_explanation_in` function to convert height to inches.
        - Uses the `round_number` function to round the result.
        - If the input gender is not "Male" or "Female," the function will not calculate IBW.

    Example:
        ibw_explanation({'height': (72, 'in'), 'sex': 'Male'})
        output: "{'Explanation': "The patient's gender is Male.\nThe patient's height is 170 cm, which is
            170 cm * 0.393701 in/cm = 66.929 in. \nFor males, the ideal body weight (IBW) is calculated as
            follows:\nIBW = 50 kg + 2.3 kg * (height (in inches) - 60)\nPlugging in the values gives us
            50 kg + 2.3 kg * (66.929 (in inches) - 60) = 65.937 kg.\nHence, the patient's IBW is 65.937 kg.",
            'Answer': 65.937}"
    """

    height = input_variables["height"]
    gender = input_variables["sex"]

    height_explanation, height = height_conversion_explanation_in(height)

    explanation = f"The patient's gender is {gender}.\n" + f"{height_explanation}\n"

    if gender == "Male":
        ibw = round_number(50 + 2.3 * (height - 60))
        explanation += (f"For males, the ideal body weight (IBW) is calculated as follows:\n"
                       f"IBW = 50 kg + 2.3 kg * (height (in inches) - 60)\n"
                       f"Plugging in the values gives us 50 kg + 2.3 kg * ({height} (in inches) - 60) = {ibw} kg.\n")
                   
    elif gender == "Female":
        ibw = round_number(45.5 + 2.3 * (height - 60))
        explanation += (f"For females, the ideal body weight (IBW) is calculated as follows:\n"
                       f"IBW = 45.5 kg + 2.3 kg * (height (in inches) - 60)\n"
                       f"Plugging in the values gives us 45.5 kg + 2.3 kg * ({height} (in inches) - 60) = {ibw} kg.\n")
        
    explanation += f"Hence, the patient's IBW is {ibw} kg."
    
    return {"Explanation": explanation, "Answer": ibw}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "height": (72, 'in'),  # weight 150 lbs
            "sex": "Male"  # Male
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = ibw_explanation(input_variables)
        print(result)
        print("-" * 50)
