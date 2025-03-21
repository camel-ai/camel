import json


def adjusted_body_weight(
        weight_value: float,  # Numeric part of the weight (e.g., 89)
        weight_unit: str,  # Unit of the weight (e.g., "kg")
        height_value: float,  # Numeric part of the height (e.g., 163)
        height_unit: str,  # Unit of the height (e.g., "cm")
        sex: str,  # Gender ("male"/"female")
        age: int  # Age
) -> str:
    """
    Calculate the patient's Adjusted Body Weight (ABW) and generate a detailed explanatory text.

    Parameters:
        weight_value (float): The numeric value of the patient's weight.
        weight_unit (str): The unit of the patient's weight, one of the following:
            - "lbs" for pounds.
            - "g" for grams.
            - "kg" for kilograms.
        height_value (float): The numeric value of the patient's height.
        height_unit (str): The unit of the patient's height, one of the following:
            - "cm" for centimeters.
            - "in" for inches.
        sex (str): The patient's gender, one of the following:
            - "Male" for male.
            - "Female" for female.
        age (int): The patient's age (integer). Currently unused but may be used for future extensions.

    Returns:
        str: A JSON string containing the calculation process and result, formatted as follows:
            {
                "weight": ("Weight (float)", "Weight unit (string)"),
                "height": ("Height (float)", "Height unit (string)"),
                "sex": "Gender Male/Female",
                "age": "Age"
            }

    Notes:
        - The `abw_explanation` function is used to calculate the adjusted body weight.
        - The `json.dumps` function is used to serialize the result into a JSON string.
        - If the input gender is not "male" or "female", the function will not calculate IBW and ABW.
    """

    # Construct the input variables dictionary
    input_variables = {
        "weight": (float(weight_value), str(weight_unit)),  # Weight: (value, unit)
        "height": (float(height_value), str(height_unit)),  # Height: (value, unit)
        "sex": str(sex),  # Gender
        "age": int(age)  # Age
    }
    # Return the result
    return input_variables


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        [150, "lbs", 170, "cm", "Male", 32]
    ]

    # Iterate the test cases and print the results
    for i, input in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input}")
        result = adjusted_body_weight(input[0], input[1], input[2], input[3], input[4], input[5])
        print(result)
        print("-" * 50)
