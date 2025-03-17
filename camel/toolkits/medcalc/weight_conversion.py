from rounding import round_number

def weight_conversion_explanation(weight_info):

    weight = weight_info[0]
    weight_label = weight_info[1]

    answer = round_number(weight * 0.453592)

    if weight_label == "lbs":
        return f"The patient's weight is {weight} lbs so this converts to {weight} lbs * 0.453592 kg/lbs = {answer} kg. ", answer
    elif weight_label == "g":
        return f"The patient's weight is {weight} g so this converts to {weight} lbs * kg/1000 g = {round_number(weight/1000)} kg. ", weight/1000
    else:
        return f"The patient's weight is {weight} kg. ", weight
    
