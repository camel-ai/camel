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
This code is borrowed and modified based on the source code from
    the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- None

Date: March 2025
"""


def age_conversion(input):
    count = 0
    while count < len(input):
        if "year" in input[count + 1]:
            return input[count]
        elif "months" in input[count + 1]:
            return input[count] // 12
        elif "weeks" in input[count + 1]:
            return input[count] // 52
        elif "days" in input[count + 1]:
            return 0
        count += 2


def age_conversion_explanation(input):
    count = 0
    text = "The patient is "

    if len(input) == 2 and input[1] == "months":
        if input[0] // 12 >= 1:
            years = input[0] // 12
            months = input[0] % 12

            add_s = "s"
            if years == 1:
                add_s = ""

            return (
                f"This means that the patient is {years} year{add_s} and {months} old",
                input[0] // 12,
            )

    while count < len(input):
        text += f"{input[count]} {input[count + 1]}"
        if len(input) - count - 2 == 0:
            text += " old. "
        elif len(input) - count - 2 > 2:
            text += ", "
        elif len(input) - count - 2 == 2:
            text += ", and "
        count += 2

    if "year" not in text:
        text += "This means the patient is 0 years old.\n"

    return text, age_conversion(input)
