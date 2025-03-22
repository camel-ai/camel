import age_conversion
import weight_conversion
import unit_converter_new
from rounding import round_number

def free_water_deficit_explanation(input_variables):
    
    explanation = ""

    explanation += f"The formula for computing the free water deficit is (total body water percentage) * (weight) * (sodium/140 - 1), where the total body water percentage is a percentage expressed as a decimal, weight is in kg, and the sodium concentration is in mmol/L.\n"

    age_exp, age = age_conversion.age_conversion_explanation(input_variables["age"])
    gender = input_variables["sex"]

    explanation += f"The patient's total body weight percentage is based on the patient's age and gender.\n"
    explanation += age_exp
    explanation += f"The patient's is a {gender}.\n"


    if 0 <= age < 18:
        tbw = 0.6
        explanation += f"The patient is less than 18 years old and so the patient is a child. This means total body water percentage value is 0.6.\n"
    elif 18 <= age < 65 and gender == "Male":
        tbw = 0.6
        explanation += f"The patient's age is between 18 and 64 and so the patient is an adult. For adult male's the total body water percentage value is 0.60.\n"
    elif 18 <= age < 65 and gender == "Female":
        tbw = 0.5
        explanation += f"The patient's age is between 18 and 64 and so the patient is an adult. For adult female's the total body water percentage value is 0.50.\n"
    elif age >= 65 and gender == "Male":
        tbw = 0.5
        explanation += f"The patient's age is greater than 64 years and so the patient is considered elderly. For elderly male's, the total body water percentage value is 0.50.\n"
    elif age >= 65 and gender == "Female":
        tbw = 0.45
        explanation += f"The patient's age is greater than 64 years and so the patient is considered elderly. For elderly female's, the total body water percentage value is 0.45.\n"

    weight_exp, weight = weight_conversion.weight_conversion_explanation(input_variables["weight"])
    explanation += weight_exp

    sodium_exp, sodium = unit_converter_new.conversion_explanation(input_variables["sodium"][0], "sodium", 22.99, 1, input_variables["sodium"][1], "mmol/L")
    explanation += sodium_exp

    
    answer = round_number(tbw * weight * (sodium/140 - 1))

    explanation += f"Plugging in these values into the equation, we get {tbw} * {weight} * ({sodium}/140 - 1) = {answer} L. "
    explanation += f"The patient's free body water deficit is {answer} L.\n"


    return {"Explanation": explanation, "Answer": answer}

