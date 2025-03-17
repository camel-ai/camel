from math import log10, floor

def round_number(num):
    if num > 0.001:
        # Round to the nearest thousandth
        return round(num, 3)
    else:
        # Round to three significant digits
        if num == 0:
            return 0
        return round(num, -int(floor(log10(abs(num)))) + 2)
