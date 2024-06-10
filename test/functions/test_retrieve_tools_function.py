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

from camel.functions import (
    MATH_FUNCS,
    SEARCH_FUNCS,
    WEATHER_FUNCS,
)
from camel.functions.retrieve_tools_function import (
    retrieve_tools,
)


def test_retrieve_tools_normal():
    retrieve_output = retrieve_tools(
        'how is the weather today',
        tools=[*SEARCH_FUNCS, *WEATHER_FUNCS],
        k=2,
    )
    expected_output = [WEATHER_FUNCS[0], SEARCH_FUNCS[1]]

    assert retrieve_output == expected_output


def test_retrieve_tools_not_found():
    retrieve_output = retrieve_tools(
        "South Africa Women Football", tools=[*MATH_FUNCS, *WEATHER_FUNCS], k=1
    )
    assert retrieve_output is None
