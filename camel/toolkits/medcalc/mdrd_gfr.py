import math
import unit_converter_new
import age_conversion
from rounding import round_number

def mrdr_gfr_explanation(input_variables):
    gender = input_variables["sex"]


    age_explanation, age = age_conversion.age_conversion_explanation(input_variables["age"])
    creatinine_exp, creatinine_conc = unit_converter_new.conversion_explanation(input_variables["creatinine"][0], "Creatinine", 113.12, None, input_variables["creatinine"][1], "mg/dL")

    explanation = ""
    explanation += f"{age_explanation}"
    explanation += f"{creatinine_exp}\n"

    race_coefficient = 1

    if "race" in input_variables:
        race = input_variables["race"]
        if race == "Black":
            race_coefficient = 1.212
            explanation += "The patient is Black, so the race coefficient is 1.212.\n"
        else:
            explanation += "The patient is not Black, so the race coefficient is defaulted to 1.0.\n"
    else:
        explanation += "The race of the patient is not provided, so the default value of the race coefficient is 1.0.\n"

    gender_coefficient = 1
    if gender == "Female":
        gender_coefficient = 0.742
        explanation += "The patient is female, so the gender coefficient is 0.742.\n"
    else:
        explanation += "The patient is male, so the gender coefficient is 1.\n"

    gfr = round_number(175 * math.exp(math.log(creatinine_conc) * -1.154) * math.exp(math.log(age) * -0.203) * race_coefficient * gender_coefficient)


    explanation += (f"The patient's estimated GFR is calculated using the MDRD equation as:\n"
                    f"GFR = 175 * creatinine^(-1.154) * age^(-0.203) * race_coefficient * gender_coefficient. The creatinine concentration is mg/dL.\n"
                    f"Plugging in these values will give us: 175 * {creatinine_conc}^(-1.154) * {age}^(-0.203) * {race_coefficient} * {gender_coefficient}={gfr}.\n"
                    f"Hence, the patient's GFR is {gfr} mL/min/1.73m².\n")

    return {"Explanation": explanation, "Answer": gfr}

