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

from pydantic import BaseModel

from camel.schemas import OutlinesConverter

# Define the model using OutlinesConverter
model = OutlinesConverter(
    model_type="microsoft/Phi-3-mini-4k-instruct", platform="transformers"
)

######## Regex conversion #########

time_regex_pattern = r"(0?[1-9]|1[0-2]):[0-5]\d\s?(am|pm)?"
output = model.convert_regex(
    "The the best time to visit a dentist is at ", time_regex_pattern
)

print(output)
"""
===============================================================================
6:00 pm
===============================================================================
"""


######## Pydantic conversion #########


# Using a Pydantic model
class Temperature(BaseModel):
    location: str
    date: str
    temperature: float


output = model.convert_pydantic(
    "Today is 2023-09-01, the temperature in Beijing is 30 degrees.",
    output_schema=Temperature,
)

print(type(output))
"""
===============================================================================
<class '__main__.Temperature'>
===============================================================================
"""
print(output)
"""
===============================================================================
location='Beijing' date='2023-09-01' temperature=30.0
===============================================================================
"""


######## JSON conversion #########

# 1. Using a JSON schema

schema = """
{
  "title": "User",
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "last_name": {"type": "string"},
    "id": {"type": "integer"}
  },
  "required": ["name", "last_name", "id"]
}
"""

output = model.convert_json(
    "Create a user profile with the fields name, last_name and id",
    output_schema=schema,
)
print(type(output))
"""
===============================================================================
<class 'dict'>
===============================================================================
"""
print(output)
"""
===============================================================================
{'name': 'John', 'last_name': 'Doe', 'id': 123456}
===============================================================================
"""

# 2. Using a function (Callable)


def get_temperature(location: str, date: str, temperature: float):
    print(f"Temperature in {location} on {date} is {temperature} degrees.")


output = model.convert_json(
    "Today is 2023-09-01, the temperature in Beijing is 30 degrees.",
    output_schema=get_temperature,
)

print(type(output))
"""
===============================================================================
<class 'dict'>
===============================================================================
"""
print(output)
"""
===============================================================================
{'location': 'Beijing', 'date': '2023-09-01', 'temperature': 30}
===============================================================================
"""


######## Type constraints #########

output = model.convert_type(
    "When I was 6 my sister was half my age. Now I'm 70 how old is my sister?",
    int,
)

print(output)
"""
===============================================================================
35
===============================================================================
"""


######## Multiple choices #########

output = model.convert_choice(
    "What is the capital of Spain?",
    ["Paris", "London", "Berlin", "Madrid"],
)

print(output)
"""
===============================================================================
Madrid
===============================================================================
"""


######## Grammar #########

arithmetic_grammar = """
    ?start: expression

    ?expression: term (("+" | "-") term)*

    ?term: factor (("*" | "/") factor)*

    ?factor: NUMBER
           | "-" factor
           | "(" expression ")"

    %import common.NUMBER
"""

output = model.convert_grammar(
    "Alice had 4 apples and Bob ate 2. "
    + "Write an expression for Alice's apples:",
    arithmetic_grammar,
)

print(output)
"""
===============================================================================
(8-2)
===============================================================================
"""
