import anion_gap
import unit_converter_new
from rounding import round_number

def compute_albumin_corrected_anion_explanation(input_parameters):

    explanation = "The formula for computing a patient's albumin corrected anion gap is: anion_gap (in mEq/L) + 2.5 * (4 - albumin (in g/dL)).\n"

    anion_gap_data = anion_gap.compute_anion_gap_explanation(input_parameters)

    explanation += anion_gap_data["Explanation"]

    albumin_exp, albumin = unit_converter_new.conversion_explanation(input_parameters["albumin"][0], "albumin", None, None, input_parameters["albumin"][1], "g/dL")

    explanation += albumin_exp

    anion_gap_val = anion_gap_data["Answer"]
    answer = anion_gap_val + 2.5 * (4 - albumin) 
    final_answer = round_number(answer)

    explanation += f"Plugging in these values into the albumin corrected anion gap formula, we get {anion_gap_val} (mEq/L) + 2.5 * (4 - {albumin} (in g/dL)) = {final_answer} mEq/L. "
    explanation += f"Hence, the patient's albumin corrected anion gap is {final_answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": final_answer}
