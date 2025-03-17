import unit_converter_new
from rounding import round_number

def compute_anion_gap_explanation(input_parameters):

    explanation = ""
    explanation += "The formula for computing a patient's anion gap is: sodium (mEq/L) - (chloride (mEq/L)+ bicarbonate (mEq/L)).\n"

    sodium = input_parameters["sodium"]
    chloride = input_parameters["chloride"]
    bicarbonate = input_parameters["bicarbonate"]

    sodium_exp, sodium = unit_converter_new.conversion_explanation(sodium[0], "sodium", 22.99, 1, sodium[1], "mEq/L")
    chloride_exp, chloride = unit_converter_new.conversion_explanation(chloride[0], "chloride", 35.45, 1, chloride[1], "mEq/L")
    bicarbonate_exp, bicarbonate = unit_converter_new.conversion_explanation(bicarbonate[0], "bicarbonate", 61.02, 1, bicarbonate[1], "mEq/L")

    explanation += sodium_exp + "\n"
    explanation += chloride_exp + "\n"
    explanation += bicarbonate_exp + "\n"

    answer = round_number(sodium - (chloride + bicarbonate))


    explanation += f"Plugging in these values into the anion gap formula gives us {sodium} mEq/L - ({chloride} mEq/L + {bicarbonate} mEq/L) = {answer} mEq/L. "
    explanation += f"Hence, The patient's anion gap is {answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": answer}


