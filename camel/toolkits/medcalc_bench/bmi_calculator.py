"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function bmi_calculator_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.height_conversion import height_conversion_explanation
from camel.toolkits.medcalc_bench.utils.weight_conversion import weight_conversion_explanation
from camel.toolkits.medcalc_bench.utils.rounding import round_number


def bmi_calculator_explanation(input_variables):
    """
    Calculates the patient's BMI and generates a detailed explanatory text.

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
            - "Answer" (float): The patient's BMI.

    Notes:
        - Uses the `height_conversion_explanation` function to convert height to inches.
        - Uses the `weight_conversion_explanation` function to convert weight to kilogram.

    Example:
        bmi_calculator_explanation({"weight": (150, "lbs"), "height": (170, "cm")})
        output: "{'Explanation': "The formula for computing the patient's BMI is (weight)/(height * height), where weight is the patient's weight in kg and height is the patient's height in m.\nThe patient's height is 170 cm, which is 170 cm * 1 m / 100 cm = 1.7 m. The patient's weight is 150 lbs so this converts to 150 lbs * 0.453592 kg/lbs = 68.039 kg. The patient's bmi is therefore 68.039 kg / (1.7 m * 1.7 m) = 23.543 kg/m^2.", 'Answer': 23.543}"
    """

    height_explanation, height = height_conversion_explanation(input_variables["height"])
    weight_explanation, weight = weight_conversion_explanation(input_variables["weight"])

    output = "The formula for computing the patient's BMI is (weight)/(height * height), where weight is the patient's weight in kg and height is the patient's height in m.\n"

    output += height_explanation
    output += weight_explanation
    ans = round_number(weight/(height * height))
    output += f"The patient's bmi is therefore {weight} kg / ({height} m * {height} m) = {ans} kg/m^2."

    return {"Explanation": output, "Answer": ans}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "weight": (150, "lbs"),  # weight 150 lbs
            "height": (170, "cm"),  # height 170 cm
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = bmi_calculator_explanation(input_variables)
        print(result)
        print("-" * 50)
