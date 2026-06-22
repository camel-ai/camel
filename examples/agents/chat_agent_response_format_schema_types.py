# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""Demonstrates the unified ``response_format`` handling of ``ChatAgent``.

In addition to a Pydantic ``BaseModel`` class, ``ChatAgent.step`` now accepts
a JSON-encoded string template or a callable as ``response_format`` and
converts it into a ``BaseModel`` via the shared ``get_pydantic_model``
utility. This unifies structured output with ``OpenAISchemaConverter.convert``
(see issue #1242).

Required environment variable:
    export OPENAI_API_KEY="<your-openai-api-key>"

Run:
    python examples/agents/chat_agent_response_format_schema_types.py
"""

from pydantic import BaseModel

from camel.agents import ChatAgent


# 1. A Pydantic model class.
class Temperature(BaseModel):
    location: str
    date: str
    temperature: float


# 2. A callable whose signature defines the expected fields.
def get_temperature(location: str, date: str, temperature: float):
    pass


# 3. A JSON-encoded string template.
temperature_template = (
    '{"location": "Beijing", "date": "2023-09-01", "temperature": 30.0}'
)


agent = ChatAgent("Extract structured data from the user's text.")

content = "Today is 2023-09-01, the temperature in Beijing is 30 degrees."

for response_format in (Temperature, get_temperature, temperature_template):
    response = agent.step(content, response_format=response_format)
    print(response.msgs[0].parsed)

"""
===============================================================================
location='Beijing' date='2023-09-01' temperature=30.0
location='Beijing' date='2023-09-01' temperature=30.0
location='Beijing' date='2023-09-01' temperature=30.0
===============================================================================
"""
