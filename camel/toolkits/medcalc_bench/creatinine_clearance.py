"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function generate_cockcroft_gault_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.weight_conversion import weight_conversion_explanation
from camel.toolkits.medcalc_bench.utils.unit_converter_new import conversion_explanation
from camel.toolkits.medcalc_bench.utils.age_conversion import age_conversion_explanation
from camel.toolkits.medcalc_bench.utils.rounding import round_number
import ideal_body_weight
import adjusted_body_weight
import bmi_calculator


def generate_cockcroft_gault_explanation(params):
    """
    Calculates the patient's Creatinine Clearance and generates a detailed explanatory text.

    Parameters:
        params (dict): A dictionary containing the following key-value pairs:
            - "sex" (str): The patient's gender, which can be either "Male" or "Female".
            - "weight" (tuple): The patient's weight information in the format (value, unit).
                - Value (float): The numerical weight measurement.
                - Unit (str): The unit of weight, which can be "lbs" (pounds), "g" (grams), or "kg" (kilograms).
            - "height" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters) or "in" (inches).
            - "creatinine" (tuple): The patient's height information in the format (value, unit).
                - Value (float): The numerical height measurement.
                - Unit (str): The unit of height, which can be "cm" (centimeters) or "in" (inches).
            - "age" (array): The patient's albumin concentration in the format (value, unit).
                - Value (float): Age.
                - Unit (str): The unit can be "months", "years".

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's Creatinine Clearance.

    Notes:
        - Use the `weight_conversion_explanation` function to convert weight to kilogram.
        - Use the `bmi_calculator` function to calculate BMI.
        - Use the `ideal_body_weight` function to calculate Ideal Body Weight (IBW)

    Example:
        generate_cockcroft_gault_explanation({"sex": "Female","weight": (55.0, "kg"),"height": (162.8, "cm"),"creatinine": (0.57, "mg/dL"),"age": (16, "years")})
        output: "{'Explanation': "The formula for computing Cockcroft-Gault is given by CrCl = ((140 - age) * adjusted weight * (gender_coefficient)) / (serum creatinine * 72), where the gender_coefficient is 1 if male, and 0.85 if female. The serum creatinine concentration is in mg/dL.\nThe patient's gender is female, which means that the gender coefficient is 0.85.\nThe patient is 16 years old. \nThe concentration of creatinine is 0.57 mg/dL. \nThe formula for computing the patient's BMI is (weight)/(height * height), where weight is the patient's weight in kg and height is the patient's height in m.\nThe patient's height is 162.8 cm, which is 162.8 cm * 1 m / 100 cm = 1.628 m. The patient's weight is 55.0 kg. The patient's bmi is therefore 55.0 kg / (1.628 m * 1.628 m) = 20.752 kg/m^2.The patient's BMI is 20.8, indicating they are normal weight.\nBecause the patient is normal, we take take minimum of the ideal body weight and the patient's body as the patient's adjusted weight for the Cockroft-Gault Equation. Hence, the adjusted body weight is the minimum of the two giving us an adjusted body weight of 54.918 kg.\n\nUsing the Cockcroft-Gault equation:\nCrCl = ((140 - age) * adjusted weight * gender_coefficient) / (serum creatinine * 72).\nPlugging the patient's values gives us ((140 - 16) * 54.918 * 0.85) / (0.57 * 72) = 141.042 mL/min. Hence, the patient's creatinine clearance is 141.042 mL/min.\n", 'Answer': 141.042}"
    """

    weight_exp, weight = weight_conversion_explanation(params["weight"])

    output = "The formula for computing Cockcroft-Gault is given by CrCl = ((140 - age) * adjusted weight * (gender_coefficient)) / (serum creatinine * 72), where the gender_coefficient is 1 if male, and 0.85 if female. The serum creatinine concentration is in mg/dL.\n"
    output += f"The patient's gender is {params['sex'].lower()}, "
    gender_coefficient = 1 if params["sex"] == "Male" else 0.85
    output += f"which means that the gender coefficient is {gender_coefficient}.\n" 
    age_explanation, age = age_conversion_explanation(params["age"])

    output += f"{age_explanation}\n"

    serum_creatinine_value = params['creatinine'][0]
    serum_creatinine_units = params['creatinine'][1]
    is_male = True if params["sex"] == "Male" else False

    bmi_response = bmi_calculator.bmi_calculator_explanation(params)
    bmi = float(bmi_response["Answer"])

    if bmi < 18.5:
        weight_status = "underweight"
    elif 18.5 <= bmi <= 24.9:
        weight_status = "normal weight"
    else:
        weight_status = "overweight/obese"
    
    ideal_weight_response = ideal_body_weight.ibw_explanation(params)
    adjusted_weight_response = adjusted_body_weight.abw_explanation(params)
    serum_creatinine_explanation, serum_creatinine = conversion_explanation(serum_creatinine_value, "creatinine", 113.12, None, serum_creatinine_units, "mg/dL")
    
    output += serum_creatinine_explanation + "\n"         
    
    output += f"{bmi_response['Explanation']}"
    output += f"The patient's BMI is {bmi:.1f}, indicating they are {weight_status}.\n"

    adjusted_weight = 0

    if bmi < 18.5:
        output += f"Because the patient is underweight, we take the patient's weight, {weight} kg as the patient's adjusted weight needed for the Cockroft-Gault Equation. "
        adjusted_weight = weight
    elif 18.5 <= bmi <= 24.9:
        adjusted_weight = min(ideal_weight_response["Answer"], weight)
        output += f"Because the patient is normal, we take take minimum of the ideal body weight and the patient's body as the patient's adjusted weight for the Cockroft-Gault Equation. "
        output += f"Hence, the adjusted body weight is the minimum of the two giving us an adjusted body weight of {adjusted_weight} kg.\n"
    
    else:
        output += f"Because the patient is overweight/obese, we use the adjusted body weight formula to get the adjusted weight used for Cockroft-Gault Equation. "
        output += f"Shown below is the computation for IBW (ideal body weight).\n"
        output += f"{ideal_weight_response['Explanation']}"
        output += f"Shown below is the computation for ABW (adjusted body weight).\n"
        output += f"{adjusted_weight_response['ABW']}"
        adjusted_weight = adjusted_weight_response["Answer"]
    
    # Calculate creatinine clearance
    if is_male:
        constant = 1
    else:
        constant = 0.85

    creatinine_clearance = round_number(((140 - age) * adjusted_weight * constant) / (serum_creatinine * 72))

    # Explanation of Cockcroft-Gault equation and result
    output += f"\nUsing the Cockcroft-Gault equation:\n"
    output += f"CrCl = ((140 - age) * adjusted weight * gender_coefficient) / (serum creatinine * 72).\n"
    output += f"Plugging the patient's values gives us ((140 - {age}) * {adjusted_weight} * {gender_coefficient}) / ({serum_creatinine} * 72) = {creatinine_clearance} mL/min. "
    output += f"Hence, the patient's creatinine clearance is {creatinine_clearance} mL/min.\n"

    return {"Explanation": output, "Answer": creatinine_clearance}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "sex": "Female",
            "weight": (55.0, "kg"),
            "height": (162.8, "cm"),
            "creatinine": (0.57, "mg/dL"),
            "age": (16, "years")
        },
        {
            "sex": "Male",
            "weight": (68.0, "kg"),
            "height": (176.0, "cm"),
            "creatinine": (1.0, "mg/dL"),
            "age": (56, "years")
        },
    ]
    # {'sex': 'Female', 'weight': [55.0, 'kg'], 'height': [162.8, 'cm'], 'creatinine': [0.57, 'mg/dL'], 'age': [16, 'years']}
    # {'sex': 'Male', 'age': [56, 'years'], 'weight': [68.0, 'kg'], 'height': [176.0, 'cm'], 'creatinine': [1.0, 'mg/dL']}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = generate_cockcroft_gault_explanation(input_variables)
        print(result)
        print("-" * 50)
