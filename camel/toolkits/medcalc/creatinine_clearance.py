import weight_conversion
import height_conversion
import ideal_body_weight
import adjusted_body_weight
import bmi_calculator
import unit_converter_new
import age_conversion
from rounding import round_number


def generate_cockcroft_gault_explanation(params):
  
    weight_exp, weight= weight_conversion.weight_conversion_explanation(params["weight"])

    output = "The formula for computing Cockcroft-Gault is given by CrCl = ((140 - age) * adjusted weight * (gender_coefficient)) / (serum creatinine * 72), where the gender_coefficient is 1 if male, and 0.85 if female. The serum creatinine concentration is in mg/dL.\n"
    output += f"The patient's gender is {params['sex'].lower()}, "
    gender_coefficient =  1 if params["sex"] == "Male" else 0.85
    output += f"which means that the gender coefficient is {gender_coefficient}.\n" 
    age_explanation, age = age_conversion.age_conversion_explanation(params["age"])

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
    serum_creatinine_explanation, serum_creatinine = unit_converter_new.conversion_explanation(serum_creatinine_value, "creatinine", 113.12, None, serum_creatinine_units, "mg/dL")
    
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

    creatinine_clearance = round_number ( ((140 - age) * adjusted_weight * constant) / (serum_creatinine * 72) )

    # Explanation of Cockcroft-Gault equation and result
    output += f"\nUsing the Cockcroft-Gault equation:\n"
    output += f"CrCl = ((140 - age) * adjusted weight * gender_coefficient) / (serum creatinine * 72).\n"
    output += f"Plugging the patient's values gives us ((140 - {age}) * {adjusted_weight} * {gender_coefficient}) / ({serum_creatinine} * 72) = {creatinine_clearance} mL/min. "
    output += f"Hence, the patient's creatinine clearance is {creatinine_clearance} mL/min.\n"

    return {"Explanation": output, "Answer": creatinine_clearance}


