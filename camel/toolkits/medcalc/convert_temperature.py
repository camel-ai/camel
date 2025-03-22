from rounding import round_number

def fahrenheit_to_celsius_explanation(temperature, units):

    if units == "degrees celsius":
        return f"The patient's temperature is {temperature} degrees celsius. ", temperature
    
    celsius = round_number((temperature - 32) * 5/9)

    explanation = f"The patient's temperature is {temperature} degrees fahrenheit. "
    explanation += f"To convert to degrees celsius, apply the formula 5/9 * [temperature (degrees fahrenheit) - 32]. "
    explanation += f"This means that the patient's temperature is 5/9 * {temperature - 32} = {celsius} degrees celsius. "

  
    return explanation, celsius
