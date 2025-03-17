import weight_conversion
import ideal_body_weight
from rounding import round_number


def abw_explanation(input_variables):

    weight_explanation, weight = weight_conversion.weight_conversion_explanation(input_variables["weight"])
    ibw_explanation =  ideal_body_weight.ibw_explanation(input_variables)

    explanation = f"{ibw_explanation['Explanation']}"
    explanation += f"{weight_explanation}"
   

    ibw = ibw_explanation["Answer"]
        
    abw = round_number(ibw + 0.4 * (weight - ibw))
    abw_explanation_string = ""
    abw_explanation_string += f"To compute the ABW value, apply the following formula: "
    abw_explanation_string += f"ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). "
    abw_explanation_string += f"ABW = {ibw} kg + 0.4 * ({weight} kg  - {ibw} kg) = {abw} kg. "
    abw_explanation_string += f"The patient's adjusted body weight is {abw} kg.\n"

    explanation += abw_explanation_string

    return {"Explanation": explanation, "ABW": abw_explanation_string, "Answer": abw}

