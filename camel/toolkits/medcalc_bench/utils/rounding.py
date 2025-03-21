"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- None

Date: March 2025
"""

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
