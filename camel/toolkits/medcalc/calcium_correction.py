import unit_converter_new
from rounding import round_number

def calculate_corrected_calcium_explanation(params):

    # Extract parameters from the input dictionary
    normal_albumin = 4.0  # Normal albumin level in g/dL
    
    albumin = params.get('albumin')
    albumin_val = albumin[0]
    albumin_units = albumin[1]

    calcium = params.get('calcium')
    calcium_val = calcium[0]
    calcium_units = calcium[1]

    output = f"To compute the patient's correct calcium level in mg/dL, the formula is  (0.8 * (Normal Albumin (in g/dL) - Patient's Albumin (in g/dL))) + Serum Calcium (in mg/dL).\n"


    # Generate explanation
    output += "The patient's normal albumin level is 4.0 g/dL.\n"
    albumin_explanation, albumin  = unit_converter_new.conversion_explanation(albumin_val, "Albmumin", 66500, None, albumin_units, "g/dL" )
    calcium_explanation, calcium  = unit_converter_new.conversion_explanation(calcium_val, "Calcium", 40.08, 2, calcium_units, "mg/dL")

    output += f"{albumin_explanation}\n"
    output += f"{calcium_explanation}\n"

    corrected_calcium = round_number(0.8 * (normal_albumin - albumin) + calcium)

    output += f"Plugging these values into the formula, we get "
    output += f"(0.8 * ({normal_albumin} g/dL - {albumin} g/dL)) + {calcium} mg/dL = {corrected_calcium} mg/dL.\n"


    output += f"The patient's corrected calcium concentration {corrected_calcium} mg/dL.\n"

    return {"Explanation": output, "Answer": corrected_calcium}

   
