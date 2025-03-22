import unit_converter_new
import albumin_corrected_delta_gap
from rounding import round_number



def compute_albumin_delta_ratio_explanation(input_parameters):

    albumin_delta_gap_resp =  albumin_corrected_delta_gap.compute_albumin_corrected_delta_gap_explanation(input_parameters)
    bicarbonate_val = unit_converter_new.conversions(input_parameters["bicarbonate"][0], input_parameters["bicarbonate"][1], "mEq/L", 61.02, 1)

    explanation = f"The formula for computing the albumin corrected delta ratio is albumin corrected delta gap (mEq/L)/(24 - bicarbonate mEq/L).\n"

    albmin_corrected_delta_gap_val = albumin_delta_gap_resp["Answer"]

    explanation += f"{albumin_delta_gap_resp['Explanation']}"

    final_answer = round_number(albumin_delta_gap_resp['Answer']/(24 - bicarbonate_val))

    explanation += f"Plugging in the albumin corrected delta gap and the bicarbonate concentration into the albumin corrected delta ratio formula, we get {albmin_corrected_delta_gap_val} mEq/L / {24 - bicarbonate_val} mEq/L = {final_answer}. "
    explanation += f"The patient's albumin corrected delta ratio is {final_answer}.\n"

    return {"Explanation": explanation, "Answer": final_answer}
 

