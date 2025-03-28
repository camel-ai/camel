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
This code is borrowed and modified based on the source code from the
    'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- None

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number


def fahrenheit_to_celsius_explanation(temperature, units):
    if units == "degrees celsius":
        return (
            f"The patient's temperature is {temperature} "
            f"degrees celsius. ",
            temperature,
        )

    celsius = round_number((temperature - 32) * 5 / 9)

    explanation = (
        f"The patient's temperature is {temperature} degrees " f"fahrenheit. "
    )
    explanation += (
        "To convert to degrees celsius, apply the formula 5/9 * "
        "[temperature (degrees fahrenheit) - 32]. "
    )
    explanation += (
        f"This means that the patient's temperature is 5/9 * "
        f"{temperature - 32} = {celsius} degrees celsius. "
    )

    return explanation, celsius
