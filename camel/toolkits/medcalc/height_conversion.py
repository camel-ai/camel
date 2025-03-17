from rounding import round_number

def height_conversion_explanation(height_info):

    if len(height_info) == 4:
        inches = height_info[0] * 12 + height_info[2]
        meters = round_number(inches * 0.0254)

        return f"The patient's height is {height_info[0]} ft {height_info[2]} in which converts to {height_info[0]} ft * 12 in/ft + {height_info[2]} in = {inches} in. Hence, the patient's height is {inches} in * 0.0254 m/in = {meters} m. ", meters
    
    elif height_info[-1] == "m":
        return f"The patient's height is {height_info[0]} m. ", height_info[0]
    elif height_info[-1] == "cm":
        height = round_number(height_info[0] / 100)
        return f"The patient's height is {height_info[0]} cm, which is {height_info[0]} cm * 1 m / 100 cm = {height} m. ", height
    elif height_info[-1] == "ft":
        height = round_number(height_info[0] * 0.3048)
        return f"The patient's height is {height_info[0]} ft, which is {height_info[0]} ft * 0.3048 m / ft = {height} m. ", height
    elif height_info[-1] == "in":
        height = round_number(height_info[0] * 0.0254)
        return f"The patient's height is {height_info[0]} in, which is {height_info[0]} in * 0.0254 m / in = {height} m. ", height

def height_conversion_explanation_cm(height_info):
    if len(height_info) == 4:
        feet = height_info[0]
        inches = height_info[2]
        total_inches = feet * 12 + inches
        centimeters = round_number(total_inches * 2.54)
        explanation = (f"The patient's height is {feet} ft {inches} in which converts to "
                       f"{feet} ft * 12 in/ft + {inches} in = {total_inches} in. "
                       f"Hence, the patient's height is {total_inches} in * 2.54 cm/in = {centimeters} cm. ")
        return explanation, centimeters
    
    elif height_info[-1] == "m":
        height_meters = height_info[0]
        centimeters = round_number(height_meters * 100)
        explanation = f"The patient's height is {height_meters} m, which is {height_meters} m * 100 cm/m = {centimeters} cm. "
        return explanation, centimeters
    
    elif height_info[-1] == "cm":
        height_cm = height_info[0]
        explanation = f"The patient's height is {height_cm} cm. "
        return explanation, height_cm
    
    elif height_info[-1] == "ft":
        height_ft = height_info[0]
        centimeters = round_number(height_ft * 30.48)
        explanation = f"The patient's height is {height_ft} ft, which is {height_ft} ft * 30.48 cm/ft = {centimeters} cm. "
        return explanation, centimeters
    
    elif height_info[-1] == "in":
        height_in = height_info[0]
        centimeters = round_number(height_in * 2.54)
        explanation = f"The patient's height is {height_in} in, which is {height_in} in * 2.54 cm/in = {centimeters} cm. "
        return explanation, centimeters


def height_conversion_explanation_in(height_info):
    if len(height_info) == 4:
        feet = height_info[0]
        inches = height_info[2]
        total_inches = round_number(feet * 12 + inches)
        explanation = (f"The patient's height is {feet} ft {inches} in which converts to "
                       f"{feet} ft * 12 in/ft + {inches} in = {total_inches} in. "
                       f"Hence, the patient's height is {total_inches} in. ")
        return explanation, total_inches
    
    elif height_info[-1] == "m":
        height_meters = height_info[0]
        inches = round_number(height_meters * 39.3701)
        explanation = f"The patient's height is {height_meters} m, which is {height_meters} m * 39.3701 in/m = {inches} in. "
        return explanation, inches
    
    elif height_info[-1] == "cm":
        height_cm = height_info[0]
        inches = round_number(height_cm * 0.393701)
        explanation = f"The patient's height is {height_cm} cm, which is {height_cm} cm * 0.393701 in/cm = {inches} in. "
        return explanation, inches
    
    elif height_info[-1] == "ft":
        height_ft = height_info[0]
        inches = round_number(height_ft * 12)
        explanation = f"The patient's height is {height_ft} ft, which is {height_ft} ft * 12 in/ft = {inches} in. "
        return explanation, inches
    
    elif height_info[-1] == "in":
        height_in = height_info[0]
        explanation = f"The patient's height is {height_in} in. "
        return explanation, height_in
