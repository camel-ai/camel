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
import textwrap
from typing import Optional, Type

from pydantic import BaseModel


def get_prompt_with_response_format(
    response_format: Optional[Type[BaseModel]],
    user_message: str,
) -> str:
    """
    This function generates a prompt based on the provided Pydantic model and
    user message.

    Args:
        response_format (Optional[Type[BaseModel]]): The Pydantic model class.
        user_message (str): The user message to be used in the prompt.

    Returns:
        str: A prompt string for the LLM.
    """
    if response_format is None:
        return user_message

    json_schema = response_format.model_json_schema()
    updated_prompt = textwrap.dedent(
        f"""\
        Given the user message, please generate a JSON response adhering 
        to the following JSON schema:
        {json_schema}
        Make sure the JSON response is valid and matches the EXACT structure 
        defined in the schema. Your result should only be a valid json 
        object, without any other text or comments.
        
        Following is the original user message:
        {user_message}
        """
    )
    return updated_prompt
