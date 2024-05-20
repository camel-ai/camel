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
    input_str = input_str.replace('\\', '\\\\')

    in_quotes = False
    escaped = False
    depth = 0
    start_index = -1
    clean_input = []  # to build the cleaned input string

    for i, char in enumerate(input_str):
        if char == '"' and not escaped:  # toggle the in_quotes status
            in_quotes = not in_quotes

        # Track whether the current character is escaped
        if in_quotes and char == '\\' and not escaped:
            escaped = True
        elif escaped:
            escaped = False
        else:
            if (
                in_quotes and char == '\n'
            ):  # replace newline inside quotes with space
                clean_input.append(' ')
            else:
                clean_input.append(char)  # append current character as it is

        if char == '{' and not in_quotes:
            depth += 1
            if depth == 1:
                start_index = i  # mark the start of a JSON object
        elif char == '}' and not in_quotes:
            depth -= 1
            if depth == 0 and start_index != -1:
                # when it reaches a closing bracket that matches the first
                # opening bracket
                cleaned_str = ''.join(clean_input[start_index : i + 1])
                try:
                    return json.loads(cleaned_str)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        "Failed to decode JSON object:\n"
                        + cleaned_str
                        + "\n"
                        + str(e)
                    ) from e
    raise ValueError("No complete JSON object found:\n" + ''.join(clean_input))
