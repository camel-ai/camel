import anion_gap
from rounding import round_number

def compute_delta_gap_explanation(input_parameters):

    explanation = f"To compute the formula of the delta gap, the formula is anion gap (in mEq/L) - 12. The first step is to compute the patient's anion gap.\n"

    anion_gap_resp = anion_gap.compute_anion_gap_explanation(input_parameters)

    explanation += anion_gap_resp["Explanation"]

    anion_gap_val = anion_gap_resp["Answer"]

    answer = round_number(anion_gap_val - 12.0)

    explanation += f"Plugging in {anion_gap_val} mEq/L for the delta gap formula, we get {anion_gap_val} - 12 = {answer} mEq/L. "
    explanation += f"Hence, the patient's delta gap is {answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": answer }
