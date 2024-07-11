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

from camel.personas.persona_generator import PersonaGenerator


def generate_personas():
    persona_group = PersonaGenerator()

    # Use the text_to_persona method
    example_text = """Clinical Guideline: Administration of Injections in 
    Pediatric Patients Purpose: To provide standardized care for pediatric 
    patients requiring injections, ensuring safety, ..."""

    inferred_persona = persona_group.text_to_persona(
        example_text, action="read"
    )
    print(
        f"Inferred Persona:\n{inferred_persona.name}"
        f"\n{inferred_persona.description}\n"
    )

    # Use the persona_to_persona method
    related_personas = persona_group.persona_to_persona(
        persona=inferred_persona
    )
    print("Related Personas:\n")
    for persona in related_personas:
        print(persona.name)
        print(persona.description)
        print()

    # Example output:
    """
Inferred Persona:
Pediatric Nurse
A healthcare professional specializing in the care of children, with expertise in administering medications and following clinical guidelines for pediatric patients.

Related Personas:

Pediatrician
A medical doctor who specializes in the care of infants, children, and adolescents. They work closely with pediatric nurses to ensure proper treatment and medication administration for young patients.

Child Life Specialist
A professional who helps children and families cope with the challenges of hospitalization, illness, and disability. They often collaborate with medical staff to make medical procedures less stressful for pediatric patients.

Pediatric Pharmacist
A pharmacist who specializes in medications for children, ensuring proper dosing and formulations. They work with the medical team to optimize medication regimens for pediatric patients.

Parent or Guardian
The primary caregiver of a pediatric patient, who needs to understand and consent to medical procedures, including injections. They often have concerns and questions about their child's treatment.

Pediatric Hospital Administrator
A healthcare manager responsible for overseeing pediatric departments or hospitals. They ensure that clinical guidelines are implemented and followed to maintain high standards of care for young patients.
    """  # noqa: E501


if __name__ == "__main__":
    generate_personas()
