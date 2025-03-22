import json
import height_conversion
from rounding import round_number

def targetweight_explanation(input_variables):

    bmi  = input_variables["body_mass_index"][0]
    height_exp, height = height_conversion.height_conversion_explanation(input_variables["height"])
    target_weight_val = round_number(bmi * (height * height))

    explanation = ""

    explanation += f"The patient's target bmi is {bmi} kg/m^2. "

    explanation += f"{height_exp}"
    
    explanation += f"From this, the patient's target weight is {bmi} kg/m^2 * {height} m * {height} m = {target_weight_val} kg. "
   
    return {"Explanation": explanation, "Answer": target_weight_val}

