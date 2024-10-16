# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from pydantic import BaseModel

from camel.structured_outputs import OpenAIStructure
from camel.types.enums import ModelType


class Temperature(BaseModel):
    location: str
    date: str
    temperature: float


def get_temperature(location: str, date: str, temperature: float):
    print(f"Temperature in {location} on {date} is {temperature} degrees.")


def test_openaistructure_with_str_template():
    temperature_template = (
        '{"location": "Beijing", "date": "2023-09-01", "temperature": 30.0}'
    )
    target_format_from_str = OpenAIStructure.get_format(temperature_template)

    model = OpenAIStructure(
        model_type=ModelType.GPT_4O,
        model_config_dict={},
        target=target_format_from_str,
    )

    structured_output = model.structure(
        "Today is 2023-09-01, the temperature in Beijing is 30 degrees."
    )

    assert structured_output.model_dump() == {
        "location": "Beijing",
        "date": "2023-09-01",
        "temperature": 30.0,
    }


def test_openaistructure_with_function():
    target_format_from_function = OpenAIStructure.get_format(get_temperature)

    model = OpenAIStructure(
        model_type=ModelType.GPT_4O,
        model_config_dict={},
        target=target_format_from_function,
    )

    structured_output = model.structure(
        "Today is 2023-09-01, the temperature in Beijing is 30 degrees."
    )

    assert structured_output.model_dump() == {
        "location": "Beijing",
        "date": "2023-09-01",
        "temperature": 30.0,
    }


def test_openaistructure_with_model():
    target_format_from_model = Temperature

    model = OpenAIStructure(
        model_type=ModelType.GPT_4O,
        model_config_dict={},
        target=target_format_from_model,
    )

    structured_output = model.structure(
        "Today is 2023-09-01, the temperature in Beijing is 30 degrees."
    )

    assert structured_output.model_dump() == {
        "location": "Beijing",
        "date": "2023-09-01",
        "temperature": 30.0,
    }
