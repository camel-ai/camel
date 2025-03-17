import height_conversion
import weight_conversion
from rounding import round_number


def bmi_calculator_explanation(input_variables):

    height_explanation, height = height_conversion.height_conversion_explanation(input_variables["height"])
    weight_explanation, weight = weight_conversion.weight_conversion_explanation(input_variables["weight"])

    output = "The formula for computing the patient's BMI is (weight)/(height * height), where weight is the patient's weight in kg and height is the patient's height in m.\n"

    output += height_explanation
    output += weight_explanation
    result = round_number(weight/(height * height))
    output += f"The patient's bmi is therefore {weight} kg / ({height} m * {height} m) = {result} kg/m^2."

    return {"Explanation": output, "Answer": result}
    
