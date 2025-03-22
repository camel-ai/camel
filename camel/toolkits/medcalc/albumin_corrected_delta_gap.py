import albumin_corrected_anion
from rounding import round_number


def compute_albumin_corrected_delta_gap_explanation(input_parameters):

    explanation = f"To compute the formula of albumin corrected delta gap, the formula is albumin corrected anion gap (in mEq/L) - 12.\n"

    albumin_corrected_resp = albumin_corrected_anion.compute_albumin_corrected_anion_explanation(input_parameters)

    explanation += albumin_corrected_resp["Explanation"]

    albumin_corrected_val = albumin_corrected_resp["Answer"]

    answer = round_number(albumin_corrected_val - 12.0)

    explanation += f"Plugging in {albumin_corrected_val} mEq/L for the anion gap into the albumin corrected delta gap formula, we get {albumin_corrected_val} - 12 = {answer} mEq/L. "
    explanation += f"Hence, the patient's albumin corrected delta gap is {answer} mEq/L.\n"

    return {"Explanation": explanation, "Answer": answer}
