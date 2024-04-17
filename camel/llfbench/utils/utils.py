from itertools import product

def generate_combinations_dict(input_dict):
    """ Turn a dict of lists into a list of dicts. """
    keys = list(input_dict.keys())
    value_combinations = product(*(input_dict[key] for key in keys))

    result = []
    for combination in value_combinations:
        new_dict = {keys[i]: combination[i] for i in range(len(keys))}
        result.append(new_dict)
    return result