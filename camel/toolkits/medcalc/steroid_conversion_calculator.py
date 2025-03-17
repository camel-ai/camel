import unit_converter_new
from rounding import round_number

def compute_steroid_conversion_explanation(input_parameters):


   explanation = """
    The Steroid Conversions providing equivalent doses for various corticosteroids are listed below:
    
       1. Betamethasone: Route = IV, Equivalent Dose = 0.75 mg
       2. Cortisone: Route = PO, Equivalent Dose = 25 mg
       3. Dexamethasone (Decadron): Route = IV or PO, Equivalent Dose = 0.75 mg
       4. Hydrocortisone: Route = IV or PO, Equivalent Dose = 20 mg
       5. MethylPrednisoLONE: Route = IV or PO, Equivalent Dose = 4 mg
       6. PrednisoLONE: Route = PO, Equivalent Dose = 5 mg
       7. PredniSONE: Route = PO, Equivalent Dose = 5 mg
       8. Triamcinolone: Route = IV, Equivalent Dose = 4 mg 
    """


    conversion_dict = {"Betamethasone IV": 1, 
                    "Cortisone PO": 33.33, 
                    "Dexamethasone IV": 1, 
                    "Dexamethasone PO": 1,
                    "Hydrocortisone IV": 26.67,
                    "Hydrocortisone PO": 26.67,
                    "MethylPrednisoLONE IV": 5.33,
                    "MethylPrednisoLONE PO": 5.33,
                    "PrednisoLONE PO": 6.67, 
                    "PredniSONE PO": 6.67, 
                    "Triamcinolone IV": 5.33
                }
    
    explanation += "\n\n"
    input_drug_mass_exp, input_drug_mass = unit_converter_new.conversion_explanation(input_parameters["input steroid"][1], input_parameters["input steroid"][0], None, None, input_parameters["input steroid"][2], "mg")
    explanation += input_drug_mass_exp

    target_drug_name = input_parameters["target steroid"]
    input_drug_name = input_parameters["input steroid"][0]
    input_unit = input_parameters["input steroid"][2]


    from_multiplier = conversion_dict[input_drug_name]
    to_multiplier = conversion_dict[target_drug_name]

    from_multiplier = conversion_dict[input_drug_name]
    to_multiplier = conversion_dict[target_drug_name]
    
    conversion_factor = round_number(to_multiplier / from_multiplier)
    converted_amount = round_number(input_drug_mass * conversion_factor)
    input_drug_mass = round_number(input_drug_mass)

    explanation += f"To convert from the {input_drug_name} to {target_drug_name}, multiply by the conversion factor, {conversion_factor} mg {target_drug_name}/{input_drug_name}, giving us {input_drug_mass} mg {input_drug_name} * {conversion_factor} mg {target_drug_name}/mg {input_drug_name} = {converted_amount} mg {target_drug_name}. "
    
    explanation += f"{input_drug_mass} {input_unit} of {input_drug_name} is equal to {converted_amount} mg of {target_drug_name}.\n"
    

    return {"Explanation": explanation, "Answer": converted_amount}

