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
import json


def extract_json_from_string(input_str: str) -> dict:
    r"""Extract the the first JSON from a string, and returns it as a Python
    dictionary.

    Args:
        string (str): The string to extract JSON from.

    Returns:
        dict: The first JSON object found in the string as a Python dictionary.
    """
    depth = 0
    start_index = -1
    for i, char in enumerate(input_str):
        if char == '{':
            depth += 1
            if depth == 1:
                start_index = i  # Mark the start of a JSON object
        elif char == '}':
            depth -= 1
            if depth == 0 and start_index != -1:
                # When it reachs a closing bracket that matches the first
                # opening bracket
                try:
                    # Attempt to parse the JSON
                    return json.loads(input_str[start_index:i + 1])
                except json.JSONDecodeError as e:
                    # If parsing fails, raise an error indicating the problem
                    raise ValueError("Failed to decode JSON object\n" +
                                     input_str) from e
    raise ValueError("No complete JSON object found:\n" + input_str)
