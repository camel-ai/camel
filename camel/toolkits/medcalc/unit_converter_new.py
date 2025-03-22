from rounding import round_number

def vol_to_vol_explanation(value, src_unit, tgt_unit, compound="", conversion_factor=False):
        
        conversion_factors_L = {
            'L': 1,
            'dL': 0.1,
            'mL': 0.001,
            'µL': 0.000001,
            'mm^3': 0.000001,
            'cm^3': 0.001,
            'm^3': 1000,
        }

        explanation = ""
        
        if src_unit == tgt_unit:
            return f"The volume of {compound} is {value} {tgt_unit}. ", value
        else:

            if not conversion_factor:
                answer = round_number(value * conversion_factor)

                explanation += f"To convert {src_unit} {compound} to {tgt_unit}, multiply by the conversion factor {conversion_factor} {tgt_unit}/{src_unit}, resulting to {src_unit} {compound} * {conversion_factor} {tgt_unit}/{src_unit} = {answer} {tgt_unit} {compound}. "   
            else:
                conversion_factor = conversion_factors_L[src_unit]/conversion_factors_L[tgt_unit]
                answer = round_number(conversion_factor)
                explanation += f"The conversion factor is {answer} {tgt_unit} for every unit of {src_unit}. "

        return explanation, answer

def molg_to_molg_explanation(mass, compound, src_unit, tgt_unit):

 
    conversion_factors_mol = {
        'mol': 1,
        'mmol': 0.001,
        'µmol': 0.000001,
        'pmol': 0.000000001,
    }

    conversion_factors_g = {
        'kg': 1000,
        'g': 1,
        'mg': 0.001,
        'µg': 0.000001
    }

    if "mol" in src_unit and "mol" in tgt_unit:
        conversion_factors_dict = conversion_factors_mol
    elif "g" in src_unit and "g" in tgt_unit:
        conversion_factors_dict = conversion_factors_g

    explanation = ""

    if src_unit == tgt_unit:
        return f"The mass of {compound} is {mass} {tgt_unit}. ", mass
    else:

        conversion_factor = round_number(conversion_factors_dict[src_unit]/conversion_factors_dict[tgt_unit])
        
        answer = round_number(mass * conversion_factor)
         
        explanation += f"To convert {mass} {src_unit} of {compound} to {tgt_unit}, multiply by the conversion factor {conversion_factor}, giving us {mass} {src_unit} {compound} * {conversion_factor} {tgt_unit}/{src_unit} = {answer} {tgt_unit} {compound}. "            

        return explanation, answer
    

def mol_g_explanation(value, compound, molar_mass, src_unit, tgt_unit):

    explanation = ""

    mol_explanation, mol = molg_to_molg_explanation(value, compound, src_unit, 'mol')

    explanation += mol_explanation

    grams_value = round_number(mol * molar_mass)
  
    explanation += f"To convert from mol {compound} to grams, multiply by the molar mass {molar_mass} g/mol, which will give {mol} mol {compound} * {molar_mass} g/mol = {grams_value} g {compound}. "
        
    grams_explanation, grams = molg_to_molg_explanation(grams_value, compound, "g", tgt_unit)

    explanation += grams_explanation

    return explanation, grams


def g_to_mol_explanation(value, compound, molar_mass, src_unit, tgt_unit):

    explanation = ""

    g_explanation, grams = molg_to_molg_explanation(value, compound, src_unit, 'g')

    explanation += g_explanation

    mol = round_number(grams/molar_mass)
   
    explanation += f"To convert from grams of {compound} to moles, divide by the molar mass {molar_mass} g/mol, which will give {grams} g/({molar_mass} g {compound}/mol) = {mol} mol {compound}. "

    mol_explanation, answer = molg_to_molg_explanation(mol, compound, 'mol', tgt_unit)

    explanation += mol_explanation

    return explanation, answer

def mEq_to_mol_explanation(value, compound, valence, tgt_unit):

    explanation = f"To convert from {value} mEq to {tgt_unit}, convert from mEq to mmol. "

    mol = round_number(value/valence)

    explanation += f"The compound {value} has a valence of {valence}, and so divide the valence by the value of mEq to get, {value} mEq/({valence} mEq/mmol) = {mol} mmol {compound}. "
    
    if tgt_unit != 'mmol':
        mol_explanation, mol = molg_to_molg_explanation(mol, compound, 'mmol', tgt_unit)

        explanation += mol_explanation

    return explanation, mol


def mol_to_mEq_explanation(value, compound, valence, src_unit):

    mmol_value = value 

    explanation = ""

    if src_unit != 'mmol':

        explanation = f"To convert from {value} {src_unit} to mEq, first convert from {src_unit} to mmol. "
        mmol_explanation, mmol_value = molg_to_molg_explanation(value, compound, src_unit, 'mmol')
        explanation += mmol_explanation

    mEq_val = round_number(mmol_value * valence)

    explanation += f"The compound, {compound}, has a valence of {valence}, and so multiply the valence by the value of mmol to get, {value} mmol * {valence} mEq/mmol = {mEq_val} mEq {compound}. "

    return explanation, mEq_val


def mEq_to_g_explanation(value, compound, molar_mass, valence, tgt_unit):

    explanation = f"To convert from {value} mEq to {tgt_unit} mmol, first convert from mEq to mmol. "

    mmol_val = round_number(value/valence)

    explanation += f"The compound, {compound}, has a valence of {valence}, and so divide the valence by the value of mEq to get, {value} mEq/({valence} mEq/mmol) = {mmol_val} mmol {compound}. "

    mol_explanation, mol_value = molg_to_molg_explanation(mmol_val, compound, 'mmol', 'mol')

    explanation += mol_explanation

    gram_explanation, answer = mol_g_explanation(mol_value, compound, molar_mass, 'mol', tgt_unit)

    explanation += gram_explanation

    return explanation, answer 

def g_to_mEq_explanation(value, compound, molar_mass, valence, src_unit):

    explanation = f"To convert from {value} {src_unit} to mEq, first convert from {src_unit} to mmol."

    mol_explanation, mol_value = g_to_mol_explanation(value, compound, molar_mass, src_unit, "mmol")

    explanation += mol_explanation

    answer = round_number(mol_value * valence)

    explanation += f"To convert from {mol_value} mmol {compound} to mEq, multiply the mmol amount by the valence, to get {mol_value} mmol * {valence} mEq/mmol = {answer} mEq {compound}. "

    return explanation, answer 

def conversion_explanation(value, compound, molar_mass, valence, src_unit, tgt_unit):

    conversion_factors_mass = set(['mol', 'mmol', 'µmol', 'pmol', 'kg', 'g', 'mg', 'µg', 'mEq'])
    conversion_factors_volume = set(['L', 'dL', 'mL', 'µL', 'mm^3', 'cm^3', 'm^3'])

    explanation = ""

    if "/" in src_unit and "/" in tgt_unit:

        src_mass_unit = src_unit.split("/")[0]
        src_volume_unit = src_unit.split("/")[1]

        tgt_mass_unit = tgt_unit.split("/")[0]
        tgt_volume_unit = tgt_unit.split("/")[1]

        if src_mass_unit == tgt_mass_unit and src_volume_unit == tgt_volume_unit:
            return f"The concentration of {compound} is {value} {src_mass_unit}/{src_volume_unit}. ", value

        explanation += f"The concentration of {compound} is {value} {src_mass_unit}/{src_volume_unit}. We need to convert the concentration to {tgt_mass_unit}/{tgt_volume_unit}. "

        if src_mass_unit != tgt_mass_unit:
            explanation += f"Let's first convert the mass of {compound} from {src_mass_unit} to {tgt_mass_unit}. "
            mass_explanation, mass_value = mass_conversion_explanation(value, compound, valence, molar_mass, src_mass_unit, tgt_mass_unit)

        else:
            explanation += f"The mass units of the source and target are the same so no conversion is needed. "
            mass_value = value

        if src_mass_unit != tgt_mass_unit:
            explanation += mass_explanation

        if src_volume_unit == tgt_volume_unit:
            volume_conversion_factor = 1
            result = round_number(mass_value/volume_conversion_factor)

            explanation += f"The volume units is {tgt_volume_unit} so no volume conversion is needed. "
            explanation += f"Hence, the concentration value of {value} {src_mass_unit} {compound}/{src_volume_unit} converts to {result} {tgt_mass_unit} {compound}/{tgt_volume_unit}. "

            return explanation, result
        else:
            explanation += f"The current volume unit is {src_volume_unit} and the target volume unit is {tgt_volume_unit}. "
            explanation_volume, volume_conversion_factor = vol_to_vol_explanation(1, src_volume_unit, tgt_volume_unit, "water", True)
            explanation += explanation_volume

        result = round_number(mass_value/volume_conversion_factor)

        explanation += f"Our next step will be to divide the mass by the volume conversion factor of {volume_conversion_factor} to get the final concentration in terms of {tgt_mass_unit}/{tgt_volume_unit}. "
        explanation += f"This will result to {mass_value} {tgt_mass_unit} {compound}/{volume_conversion_factor} {tgt_volume_unit} = {result} {tgt_mass_unit} {compound}/{tgt_volume_unit}. "
        explanation += f"The concentration value of {value} {src_mass_unit} {compound}/{src_volume_unit} converts to {result} {tgt_mass_unit} {compound}/{tgt_volume_unit}. "

        return explanation, result 


    elif ("/" not in src_unit and "/" not in tgt_unit) and src_unit in conversion_factors_mass and tgt_unit in conversion_factors_mass:

        if src_unit == tgt_unit:
            return f"The mass of {compound} is {round_number(value)} {tgt_unit}. ", value

        explanation, result = mass_conversion_explanation(value, compound, valence, molar_mass, src_unit, tgt_unit)
        return explanation, result

    elif ("/" not in src_unit and "/" not in tgt_unit) and src_unit in conversion_factors_volume and tgt_unit in conversion_factors_volume:

        if src_unit == tgt_unit:
            return f"The volume is {value} {tgt_unit}. ", value

        explanation, value = vol_to_vol_explanation(value, src_unit, tgt_unit)
        return explanation, result
       

def mass_conversion_explanation(value, compound, valence, molar_mass, src_mass_unit, tgt_mass_unit):
        
    explanation = f"The mass of {compound} is {value} {src_mass_unit}. "

    if ("g" in src_mass_unit and "g" in tgt_mass_unit) or ("mol" in src_mass_unit and "mol" in tgt_mass_unit):
        conv_explanation, mass_value = molg_to_molg_explanation(value, compound, src_mass_unit, tgt_mass_unit)
        explanation += conv_explanation

    elif ("mol" in src_mass_unit and "g" in tgt_mass_unit):
        conv_explanation, mass_value = mol_g_explanation(value, compound, molar_mass, src_mass_unit, tgt_mass_unit)
        explanation += conv_explanation

    elif ("g" in src_mass_unit and "mol" in tgt_mass_unit):
        conv_explanation, mass_value = g_to_mol_explanation(value, compound, molar_mass, src_mass_unit, tgt_mass_unit)
        explanation += conv_explanation

    elif ("mol" in src_mass_unit and "mEq" in tgt_mass_unit):
        conv_explanation, mass_value =  mol_to_mEq_explanation(value, compound, valence, src_mass_unit)
        explanation += conv_explanation

    elif ("mEq" in src_mass_unit and "mol" in tgt_mass_unit):
        conv_explanation, mass_value = mEq_to_mol_explanation(value, compound, valence, tgt_mass_unit)
        explanation += conv_explanation

    elif ("mEq" in src_mass_unit and "g" in tgt_mass_unit):
        conv_explanation, mass_value =  mEq_to_g_explanation(value, compound, molar_mass, valence, tgt_mass_unit)
        explanation += conv_explanation

    elif ("g" in src_mass_unit and "mEq" in tgt_mass_unit):
        conv_explanation, mass_value =  g_to_mEq_explanation(value, compound, molar_mass, valence, src_mass_unit)
        explanation += conv_explanation

    return explanation, mass_value


def convert_to_units_per_liter_explanation(value, unit, compound, target_unit):
  
    # Dictionary to define conversion factors to liters
    unit_to_liter = {
        'L': 1,
        'dL': 1e-1,
        'mL': 1e-3,
        'µL': 1e-6,
        'mm^3': 1e-6,
        'cm^3': 1e-3,
        'm^3': 1e3,
    }

    explanation = ""

    if unit == target_unit:
        return f"The patient's concentration of {compound} is {value} count/{unit}. ", value
    else:
        explanation += f"The patient's concentration of {compound} is {value} count/{unit}. "

    conversions_factor = round_number(unit_to_liter[target_unit]/unit_to_liter[unit])

    print(conversions_factor)

    result = round_number(conversions_factor * value)

    explanation += f"To convert {value} count/{unit} of {compound} to {target_unit}, multiply by the conversion factor {conversions_factor} {unit}/{target_unit} which will give {value} {compound} count/{unit} * {conversions_factor} {unit}/{target_unit} = {result} {compound} count/{target_unit}. "
    return explanation, result 


def mmHg_to_kPa_explanation(mmHg, compound):
    answer = round_number(0.133322 * mmHg)
    explanation = f"To convert the partial pressure of {compound} from mm Hg of {compound} to kPa, multiply by the conversion factor of 0.133322 mm Hg/kPa, which will give us {mmHg} * 0.133322 mm Hg/kPa = {answer} kPa of {compound}.\n"

    return explanation, answer

def kPa_to_mmHg_explanation(kPa, compound):
    answer = round_number(7.50062 * kPa)
    explanation = f"To convert the partial pressure of {compound} from mm Hg of {compound} to kPa, multiply by the conversion factor of 0.133322 mm Hg/kPa, which will give us {kPa} * 0.133322 mm Hg/kPa = {answer} kPa of {compound}.\n"

    return explanation, answer


