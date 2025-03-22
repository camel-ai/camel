import unit_converter_new
from rounding import round_number


def compute_homa_ir_explanation(input_variables):

    explanation = "The formula for computing HOMA-IR score is (insulin (µIU/mL) * glucose mg/dL)/405.\n"

    insulin = input_variables["insulin"][0]

    if input_variables["insulin"][1] == "µIU/mL":
        explanation += f"The concentration of insulin is {insulin} µIU/mL.\n"
    
    elif input_variables["insulin"][1] == "pmol/L":
        insulin =  input_variables["insulin"][0] * 6
        explanation += f"The concentration of insulin is {insulin} pmol/L. We to need convert the concentration of insulin to pmol/L, by multiplying by the conversion factor of 6.0 µIU/mL/pmol/L. This makes the insulin concentration {input_variables['insulin'][0]} * 6 µIU/mL/pmol/L = {insulin} µIU/mL.\n"

    elif input_variables["insulin"][1] == "ng/mL":
        insulin = input_variables["insulin"][0] * 24.8
        explanation += f"The concentration of insulin is {insulin} ng/mL. We to need convert the concentration of insulin to µIU/mL, by multiplying by the conversion factor 24.8 µIU/mL/ng/mL. This makes the insulin concentration {input_variables['insulin'][0]} * 24.8 µIU/mL/ng/mL = {insulin} ng/mL.\n"

    glucose_exp, glucose = unit_converter_new.conversion_explanation(input_variables["glucose"][0], "glucose", 180.16, None, input_variables["glucose"][1], "mg/dL")

    explanation += glucose_exp + "\n"

    answer = round_number((insulin * glucose)/405)

    explanation += f"Plugging into the formula will give us {insulin} * {glucose}/405 = {answer}. Hence, the patient's HOMA-IR score is {answer}. \n"

    return {"Explanation": explanation, "Answer": answer}


