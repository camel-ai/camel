import unit_converter_new
from rounding import round_number

def mme_explanation(input_parameters):

    explanation = """
    The Opioid Conversion Table with MME (Morphine Milligram Equivalent) conversion factors are listed below:
    
       1. Codeine: MME conversion factor = 0.15
       2. FentaNYL buccal: MME conversion factor = 0.13
       3. HYDROcodone: MME conversion factor = 1
       4. HYDROmorphone: MME conversion factor = 5
       5. Methadone: MME conversion factor = 4.7
       6. Morphine: MME conversion factor = 1
       7. OxyCODONE: MME conversion factor = 1.5
       8. OxyMORphone: MME conversion factor = 3
       9. Tapentadol: MME conversion factor = 0.4
       10. TraMADol: MME conversion factor = 0.2
       11. Buprenorphine: MME conversion factor = 10

    """

    explanation += "\n\nThe curent Morphine Milligram Equivalents (MME) is 0 MME per day.\n"
    
    mme_drug = {"Codeine": 0.15, 
            "FentaNYL buccal": 0.13,
            "FentANYL patch": 2.4,
            "HYDROcodone": 1,
            "HYDROmorphone": 5,
            "Methadone": 4.7, 
            "Morphine": 1, 
            "OxyCODONE": 1.5, 
            "OxyMORphone": 3, 
            "Tapentadol": 0.4, 
            "TraMADol": 0.2, 
            "Buprenorphine": 10}
    
    mme_equivalent = 0
    
    for drug_name in input_parameters:
        if "Day" in drug_name:
            continue 

        name = drug_name.split(" Dose")[0]

        units = input_parameters[name + " Dose"][1]


        if name != "FentaNYL buccal" and name != "FentaNYL patch":
            drug_mg_exp, drug_mg = unit_converter_new.conversion_explanation(input_parameters[name + " Dose"][0], name, None, None, units, "mg")
            if units == "mg":
                explanation += f"The patient's dose of {name} is {drug_mg} mg. "
            else:
                explanation += f"The patient's dose of {name} is measured in {units}. We need to convert this to mg. "
                explanation += drug_mg_exp + "\n"
        else:
            drug_mg_exp, drug_mg = unit_converter_new.conversion_explanation(input_parameters[name + " Dose"][0], name, None, None, units, "µg")
            if units == "µg":
                explanation += f"The patient's dose of {name} is {drug_mg} µg.\n"
            else:
                explanation += f"The patient's dose of {name} is measured in {units}. We need to convert this to µg. "
                explanation += drug_mg_exp + "\n"


        target_unit = "mg" if name != "FentaNYL buccal" and name != "FentaNYL patch" else "µg"

        dose_per_day_key = name + " Dose Per Day"

        dose_per_day = input_parameters[dose_per_day_key][0]

        total_per_day = round_number(drug_mg * dose_per_day)

        explanation += f"The patient takes {dose_per_day} doses/day of {name}. This means that the patient takes {round_number(drug_mg)} {target_unit}/dose {name} * {dose_per_day} dose/day = {total_per_day} {target_unit}/day. "

        explanation += f"To convert to mme/day of {name}, multiply the {total_per_day} {target_unit}/day by the mme conversion factor, {mme_drug[name]} mme/{target_unit}, giving us {round_number(mme_drug[name] * total_per_day)} mme/day. "
    
        explanation += f"Adding the mme/day of {name} to the total mme/day gives us {round_number(mme_equivalent)} + {round_number(mme_drug[name] * total_per_day)} = {round_number(mme_equivalent + mme_drug[name] * total_per_day)} mme/day.\n"

        mme_equivalent += dose_per_day * mme_drug[name] * drug_mg

        mme_equivalent = round_number(mme_equivalent)


    explanation += f"The patient's mme/day is {mme_equivalent} mme/day."
        
    return {"Explanation": explanation, "Answer": mme_equivalent}

