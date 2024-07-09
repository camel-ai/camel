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
from .persona_to_persona import persona_to_persona
from .text_to_persona import text_to_persona

# Example usage
if __name__ == "__main__":
    example_text = """Clinical Guideline: Administration of Injections in 
    Pediatric Patients Purpose: To provide standardized care for pediatric 
    patients requiring injections, ensuring safety, ..."""

    inferred_persona = text_to_persona(example_text, action="read")
    print(f"Inferred Persona:\n{inferred_persona}\n")

    related_personas = persona_to_persona(inferred_persona)
    print(f"Related Personas:\n{related_personas}")
