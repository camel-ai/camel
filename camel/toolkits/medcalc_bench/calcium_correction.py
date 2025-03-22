"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function calculate_corrected_calcium_explanation
- translation

Date: March 2025
"""

from utils.unit_converter_new import conversion_explanation
from utils.rounding import round_number


def calculate_corrected_calcium_explanation(params):
    """
    Calculates the patient's corrected calcium concentration and generates a detailed explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following key-value pairs:
            - "albumin" (array): The patient's albumin concentration in the format (value, unit).
                - Value (float): The numerical albumin concentration value.
                - Unit (str): The unit of albumin concentration, eg. "g/L", "mg/dL", "g/mL" and so on.
            - "calcium" (array): The patient's calcium concentration in the format (value, unit).
                - Value (float): The numerical calcium concentration value.
                - Unit (str): The unit of calcium concentration, eg. "g/L", "mg/dL", "g/mL" and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's corrected calcium concentration (in mg/dL).

    Notes:
        - Uses the `conversion_explanation` function to convert Albumin level to standard unit g/dL.
        - Uses the `conversion_explanation` function to convert Calcium level to standard unit mg/dL.

    Example:
        calculate_corrected_calcium_explanation({"albumin": [4, "mg/dL"], "calcium": [40, "mg/L"]})
        output: "{'Explanation': "To compute the patient's correct calcium level in mg/dL, the formula is  (0.8 * (Normal Albumin (in g/dL) - Patient's Albumin (in g/dL))) + Serum Calcium (in mg/dL).\nThe patient's normal albumin level is 4.0 g/dL.\nThe concentration of Albmumin is 4 g/dL. \nThe concentration of Calcium is 40 mg/L. We need to convert the concentration to mg/dL. The mass units of the source and target are the same so no conversion is needed. The current volume unit is L and the target volume unit is dL. The conversion factor is 10.0 dL for every unit of L. Our next step will be to divide the mass by the volume conversion factor of 10.0 to get the final concentration in terms of mg/dL. This will result to 40 mg Calcium/10.0 dL = 4.0 mg Calcium/dL. The concentration value of 40 mg Calcium/L converts to 4.0 mg Calcium/dL. \nPlugging these values into the formula, we get (0.8 * (4.0 g/dL - 4 g/dL)) + 4.0 mg/dL = 4.0 mg/dL.\nThe patient's corrected calcium concentration 4.0 mg/dL.\n", 'Answer': 4.0}"
    """

    # Extract parameters from the input dictionary
    normal_albumin = 4.0  # Normal albumin level in g/dL
    
    albumin = params.get('albumin')
    albumin_val = albumin[0]
    albumin_units = albumin[1]

    calcium = params.get('calcium')
    calcium_val = calcium[0]
    calcium_units = calcium[1]

    output = f"To compute the patient's correct calcium level in mg/dL, the formula is  (0.8 * (Normal Albumin (in g/dL) - Patient's Albumin (in g/dL))) + Serum Calcium (in mg/dL).\n"

    # Generate explanation
    output += "The patient's normal albumin level is 4.0 g/dL.\n"
    albumin_explanation, albumin = conversion_explanation(albumin_val, "Albmumin", 66500, None, albumin_units, "g/dL")
    calcium_explanation, calcium = conversion_explanation(calcium_val, "Calcium", 40.08, 2, calcium_units, "mg/dL")

    output += f"{albumin_explanation}\n"
    output += f"{calcium_explanation}\n"

    corrected_calcium = round_number(0.8 * (normal_albumin - albumin) + calcium)

    output += f"Plugging these values into the formula, we get "
    output += f"(0.8 * ({normal_albumin} g/dL - {albumin} g/dL)) + {calcium} mg/dL = {corrected_calcium} mg/dL.\n"

    output += f"The patient's corrected calcium concentration {corrected_calcium} mg/dL.\n"

    return {"Explanation": output, "Answer": corrected_calcium}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "albumin": [4, "g/dL"],
            "calcium": [40, "mg/L"],
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = calculate_corrected_calcium_explanation(input_variables)
        print(result)
        print("-" * 50)
