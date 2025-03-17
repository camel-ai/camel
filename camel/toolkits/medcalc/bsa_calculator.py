import math
import height_conversion
import weight_conversion
from rounding import round_number

def bsa_calculator_explaination(input_variables):

    height_explaination, height = height_conversion.height_conversion_explanation_cm(input_variables["height"])
    weight_explanation, weight = weight_conversion.weight_conversion_explanation(input_variables["weight"])
    
    output = "For the body surface area computation, the formula is sqrt((weight (in kgs) * height (in cm))/3600, where the units of weight is in kg and the units of height is in cm.\n"

    output += height_explaination + "\n"
    output += weight_explanation + "\n"
 
    answer = round_number(math.sqrt(weight * height/3600))
    output += f"Therefore, the patient's bsa is sqrt(({weight} (in kgs) * {height} (in cm))/3600) = {answer} m^2."

    return {"Explanation": output, "Answer": answer}

