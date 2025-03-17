import json
import random
import steroid_conversion_calculator
from datetime import datetime, timedelta
import importlib.util
import height_conversion
from rounding import round_number

random.seed(42)


def random_date():

    month = random.randint(1, 12)

    year = random.randint(2000, 2024)

    if month in set([1, 3, 5, 7, 8, 10, 12]):
        day = random.randint(1, 31)
    elif month == 2:
        if month % 4 == 0:
            day = random.randint(1, 29)
        else:
            day = random.randint(1, 28)
    else:
        day = random.randint(1,30)

    return month, day, year

def estimated_date_calculator():

    cycle_length = random.randint(20, 30)

    month, day, year = random_date()

    date_obj = datetime(year, month, day)
    
    modified_date_string = date_obj.strftime("%m/%d/%Y")

    edd_note = f"The patient's last menstrual period was on {modified_date_string}. Her cycle length is {cycle_length} days."

    input_parameters = {"cycle_length": cycle_length, "menstrual_date": modified_date_string}

    return edd_note, input_parameters


def estimated_date_of_conception():

    cycle_length = random.randint(20, 30)

    month, day, year = random_date()

    date_obj = datetime(year, month, day)

    modified_date_string = date_obj.strftime("%m/%d/%Y")

    edc_note = f"The patient's last menstrual period was on {modified_date_string}. Her cycle length is {cycle_length} days."
    
    input_parameters = {"cycle_length": cycle_length, "menstrual_date": modified_date_string}

    return edc_note, input_parameters


def estimated_gestational_age():


    month, day, year = random_date()

    week_to_add = random.randint(0, 37)
    days_to_add = random.randint(0, 6)

    date_obj = datetime(year, month, day)

    date_obj_str = date_obj.strftime("%m/%d/%Y")

    modified_date = date_obj + timedelta(weeks=week_to_add, days=days_to_add)

    modified_date_string = modified_date.strftime("%m/%d/%Y")

    ega_note = f"The patient's last menstrual period was on {date_obj_str}. Today's date is {modified_date_string}."
    
    input_parameters = {"current_date": modified_date_string, "menstrual_date": date_obj_str}

    return ega_note, input_parameters


def qt_interval_patient_notes_bazett():


    heart_rate = round(random.uniform(45, 180))

    qt_interval = round(330, 470)

    note = f"Patient has a heart rate of {heart_rate} bpm and a QT interval of {qt_interval} msec."

    input_parameters = {"heart_rate": [heart_rate, "beats per minute"], "qt_interval": [qt_interval, "msec"]}
    
    return note, input_parameters


def qt_interval_patient_notes_framingham():

    heart_rate = round(random.uniform(45, 180))

    qt_interval = round(330, 470)

    note = f"Patient has a heart rate of {heart_rate} bpm and a QT interval of {qt_interval} msec."

    input_parameters = {"heart_rate": [heart_rate, "beats per minute"], "qt_interval": [qt_interval, "msec"]}
    
    return note, input_parameters


def qt_interval_patient_notes_fridericia():

    heart_rate = round(random.uniform(45, 180))

    qt_interval = round(330, 470)

    note = f"Patient has a heart rate of {heart_rate} bpm and a QT interval of {qt_interval} msec."

    input_parameters = {"heart_rate": [heart_rate, "beats per minute"], "qt_interval": [qt_interval, "msec"]}
    
    return note, input_parameters


def qt_interval_patient_notes_hodges():

    heart_rate = round(random.uniform(45, 180))

    qt_interval = round(330, 470)

    note = f"Patient has a heart rate of {heart_rate} bpm and a QT interval of {qt_interval} msec."

    input_parameters = {"heart_rate": [heart_rate, "beats per minute"], "qt_interval": [qt_interval, "msec"]}
    
    return note, input_parameters


def qt_interval_patient_notes_rautaharju():


    heart_rate = round(random.uniform(45, 180))

    qt_interval = round(330, 470)

    note = f"Patient has a heart rate of {heart_rate} bpm and a QT interval of {qt_interval} msec."

    input_parameters = {"heart_rate": [heart_rate, "beats per minute"], "qt_interval": [qt_interval, "msec"]}
    
    return note, input_parameters


def mme_conversion():
    
    mme_drugs = ["Codeine", "FentaNYL buccal", "FentANYL patch", "HYDROcodone", "HYDROmorphone", "Methadone", "Morphine", "OxyCODONE", "OxyMORphone", "Tapentadol", "TraMADol"]
    

    drugs = random.sample(mme_drugs, 3)

    note = "The patient takes "

    input_parameters = {}

    for i in range(3):

        num_doses = random.randint(1, 3)
        num_amount = round(random.randint(1, 7)) * 10

        key_name_dose = drugs[i] + " Dose"
        key_name_dose_per_day = drugs[i] + " Dose Per Day"

        if drugs[i] == "FentaNYL buccal" or drugs[i] == "FentaNYL patch":
            input_parameters[key_name_dose] = [num_amount , "µg"]
        else:
            input_parameters[key_name_dose] = [num_amount , "mg"]
        
        input_parameters[key_name_dose_per_day] = [num_doses, "per day"]

        add_s = 's'

        if num_doses == 1:
            add_s = ''

        if i == len(drugs) - 1:
            note += f"and {num_amount} mg of {drugs[i]} {num_doses} time{add_s} a day."
        else:
            note += f"{num_amount} mg of {drugs[i]} {num_doses} time{add_s} a day, "

    return note, input_parameters

def steroid_conversion():

  
    steroid_names = ['Betamethasone IV', 'Cortisone PO', 'Dexamethasone IV', 'Dexamethasone PO', 'Hydrocortisone IV', 'Hydrocortisone PO',  'MethylPrednisoLONE IV', 'MethylPrednisoLONE PO', 'PredniSONE PO', 'PrednisoLONE PO', 'Triamcinolone IV']
    
    choices = random.sample(steroid_names, 2)

    random_value = round(random.uniform(0.6, 9), 2)

    input_parameters = {"input steroid": ['Betamethasone IV', random_value, "mg"], "target steroid": choices[0]}
    
    amount = round_number(steroid_conversion_calculator.compute_steroid_conversion(input_parameters))

    note = f"Patient has taken {amount} mg of {choices[0]}. "

    input_parameters = {"input steroid": [choices[0], round_number(amount), "mg"], "target steroid": choices[1]}

    return note, input_parameters

# Have the functions for generating the values. Just ask the LLM to compute the value. 

def target_weight():

    height_units = ["cm", "m", "in"]

    height_value = round(random.uniform(1.4, 2.0) , 2)

    height_unit = random.choice(height_units)

    if height_unit == "in":
        height_value = round(height_conversion.height_conversion_in([height_value, "m"]))
    elif height_unit == "cm":
        height_value = round(height_conversion.height_conversion_cm([height_value, "m"]))
    elif height_unit == "m":
        height_value = round(height_conversion.height_conversion([height_value, "m"]), 2)

    bmi = round(random.uniform(18, 25) , 1)

    note = f"Patient has a height of {height_value} {height_unit} and their target BMI is {bmi} kg/m^2."

    input_parameters = {"body_mass_index": [bmi, "kg/m^2"], "height": [height_value, height_unit]}
    
    return note, input_parameters


with open("/Users/khandekarns/Documents/GSM8k-Med/calculator_implementations/calc_info.json") as file:
    calc_info  = json.load(file)

problems = {}

calc_ids = ["11", "13", "24", "56", "57", "58", "59", "61", "49", "68", "69"]


calculator_id_to_name = {
                         "11": "qt_interval_patient_notes_bazett", 
                         "13": "estimated_date_calculator",
                         "24": "steroid_conversion", 
                         "56": "qt_interval_patient_notes_framingham",
                         "57": "qt_interval_patient_notes_fridericia",
                         "58": "qt_interval_patient_notes_hodges",
                         "59": "qt_interval_patient_notes_rautaharju",
                         "61": "target_weight",
                         "49": "mme_conversion",
                         "68": "estimated_date_of_conception",
                         "69": "estimated_gestational_age"
                        }


data = {}

for calc_id in calculator_id_to_name:

    calculator_name_formal = calc_info[calc_id]["calculator name"]

    data[calc_id] = {}

    for i in range(21, 101):

        function_name = calculator_id_to_name[calc_id]

        if function_name in globals() and callable(globals()[function_name]):
            note, input_parameters =  globals()[function_name]()

    
            key_name =  str(i + 1)
            
            spec = importlib.util.spec_from_file_location("my_module", calc_info[calc_id]["file path"])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            function = getattr(module, calc_info[calc_id]["explanation"])

            gt_result = function(input_parameters)

            data[calc_id][key_name] = {}
            data[calc_id][key_name]["explanation"] = gt_result["Explanation"]
            data[calc_id][key_name]["Ground Truth Answer"] = gt_result["Answer"]
            data[calc_id][key_name]["calculator name"] = calc_info[calc_id]["calculator name"]
            data[calc_id][key_name]["Patient Note"] = note
            data[calc_id][key_name]["input_parameters"] = input_parameters

with open("synthetic_instances.json") as file:
    json.dump(data, file, indent=4)



