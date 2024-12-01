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

from camel.schemas import OpenAISchemaConverter


def get_temperature(location: str, date: str, temperature: float):
    print(f"Temperature in {location} on {date} is {temperature} degrees.")


class Temperature(BaseModel):
    location: str
    date: str
    temperature: float


temperature_template = (
    '{"location": "Beijing", "date": "2023-09-01", "temperature": 30.0}'
)


model = OpenAISchemaConverter()

print(
    model.convert(
        "Today is 2023-09-01, the temperature in Beijing is 30 degrees.",
        output_schema=temperature_template,
    )
)

print(
    model.convert(
        "Today is 2023-09-01, the temperature in Beijing is 30 degrees.",
        output_schema=get_temperature,
    )
)

print(
    model.convert(
        "Today is 2023-09-01, the temperature in Beijing is 30 degrees.",
        output_schema=Temperature,
    )
)
"""
location='Beijing' date='2023-09-01' temperature=30.0
location='Beijing' date='2023-09-01' temperature=30.0
location='Beijing' date='2023-09-01' temperature=30.0
"""
