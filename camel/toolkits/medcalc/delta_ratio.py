import delta_gap
import unit_converter_new
from rounding import round_number



def compute_delta_ratio_explanation(input_parameters):

    delta_gap_resp = delta_gap.compute_delta_gap_explanation(input_parameters)
    bicarbonate_val = unit_converter_new.conversions(input_parameters["bicarbonate"][0], input_parameters["bicarbonate"][1], "mEq/L", 61.02, 1)
    
    explanation = f"The formula for computing the delta ratio is delta gap (mEq/L)/(24 - bicarbonate mEq/L).\n"

    delta_gap_val = delta_gap_resp["Answer"]

    explanation += f"{delta_gap_resp['Explanation']}"

    answer = round_number(delta_gap_resp['Answer']/(24 - bicarbonate_val))

    explanation += f"Plugging in the delta gap and the bicarbonate concentration for the delta ratio formula, we get {delta_gap_val} mEq/L / {24 - bicarbonate_val} mEq/L = {answer}. "

    explanation += f"The patient's delta ratio is {answer}.\n"

    return {"Explanation": explanation, "Answer": answer}

