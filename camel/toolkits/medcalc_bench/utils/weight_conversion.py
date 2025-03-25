# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
r"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function weight_conversion_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number


def weight_conversion_explanation(weight_info):
    r"""
    Converts a patient's weight from different units (pounds, grams, or kilograms) to kilograms
    and generates an explanatory text.

    Parameters:
        weight_info (tuple): A tuple containing two elements:
            - First element (float): The patient's weight value.
            - Second element (str): The unit of weight, which can be one of the following:
                - "lbs" for pounds.
                - "g" for grams.
                - "kg" for kilograms.

    Returns:
        tuple: Contains two elements:
            - First element (str): An explanatory text describing the conversion process and result.
            - Second element (float): The converted weight value (in kilograms).

    Notes:
        - Uses the `round_number` function to round the result.
        - If the input unit is not "lbs," "g," or "kg," the function defaults to returning the input value as kilograms.

    Example:
        convert_weight((150, "lbs"))
        output: "The patient's weight is 150 lbs so this converts to 150 lbs * 0.453592 kg/lbs = 68.04 kg."
    """
    assert len(weight_info) == 2
    weight = weight_info[0]
    weight_label = weight_info[1]

    answer = round_number(weight * 0.453592)

    if weight_label == "lbs":
        return (
            f"The patient's weight is {weight} lbs so this converts to {weight} lbs * 0.453592 kg/lbs = {answer} kg. ",
            answer,
        )
    elif weight_label == "g":
        return (
            f"The patient's weight is {weight} g so this converts to {weight} lbs * kg/1000 g = "
            f"{round_number(weight / 1000)} kg. ",
            weight / 1000,
        )
    else:
        return f"The patient's weight is {weight} kg. ", weight
