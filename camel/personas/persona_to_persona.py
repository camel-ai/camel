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
import os

from openai import OpenAI

# Set up your OpenAI API key from environment variable
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def persona_to_persona(persona):
    """
    Derives additional personas based on interpersonal relationships from an
    initial persona.

    Args:
    persona (str): The initial persona description.

    Returns:
    dict: A dictionary of related personas with their relationship types.
    """
    system_prompt = "You are a helpful assistant."
    user_prompt = (
        f"Given the following persona: \"{persona}\", who is likely to be in "
        f"a close relationship with this"
        f"persona? Describe the related personas and their relationships."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    related_personas = response.choices[0].message.content
    return related_personas


# Example usage
if __name__ == "__main__":
    inferred_persona = """A pediatric nurse, who is responsible for 
    administering injections to children and ensuring their safety and 
    comfort during the procedure."""
    related_personas = persona_to_persona(inferred_persona)
    print(f"Related Personas:\n{related_personas}")
