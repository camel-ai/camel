"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function bsa_calculator_explaination
- translation

Date: March 2025
"""

import math
from camel.toolkits.medcalc_bench.utils.height_conversion import height_conversion_explanation_cm
from camel.toolkits.medcalc_bench.utils.weight_conversion import weight_conversion_explanation
from camel.toolkits.medcalc_bench.utils.rounding import round_number


def bsa_calculator_explaination(input_variables):
    """
    Calculates the patient's Body Surface Area and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "weight" (tuple): The patient's weight information in the format (value, unit).
                - Value (float): The numerical weight measurement.
                - Unit (str): The unit of weight, which can be "lbs" (pounds), "g" (grams), or "kg" (kilograms).
            - "height" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters) or "in" (inches).

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's Body Surface Area.

    Notes:
        - Uses the `height_conversion_explanation_cm` function to convert height to cm.
        - Uses the `weight_conversion_explanation` function to convert weight to kilogram.

    Example:
        bsa_calculator_explaination({'weight': [58.0, 'kg'], 'height': [179.0, 'cm']})
        output: "{'Explanation': "For the body surface area computation, the formula is sqrt((weight (in kgs) * height (in cm))/3600, where the units of weight is in kg and the units of height is in cm.\nThe patient's height is 179.0 cm. \nThe patient's weight is 58.0 kg. \nTherefore, the patient's bsa is sqrt((58.0 (in kgs) * 179.0 (in cm))/3600) = 1.698 m^2.", 'Answer': 1.698}"
    """

    height_explaination, height = height_conversion_explanation_cm(input_variables["height"])
    weight_explanation, weight = weight_conversion_explanation(input_variables["weight"])
    
    output = "For the body surface area computation, the formula is sqrt((weight (in kgs) * height (in cm))/3600, where the units of weight is in kg and the units of height is in cm.\n"

    output += height_explaination + "\n"
    output += weight_explanation + "\n"
 
    answer = round_number(math.sqrt(weight * height/3600))
    output += f"Therefore, the patient's bsa is sqrt(({weight} (in kgs) * {height} (in cm))/3600) = {answer} m^2."

    return {"Explanation": output, "Answer": answer}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "weight": (58.0, "kg"),
            "height": (179.0, "cm"),
        }
    ]

    # {'weight': [58.0, 'kg'], 'height': [179.0, 'cm']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = bsa_calculator_explaination(input_variables)
        print(result)
        print("-" * 50)
