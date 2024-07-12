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
from unittest.mock import MagicMock, patch

import pytest

from camel.messages import BaseMessage
from camel.personas import Persona, PersonaGenerator
from camel.types import RoleType

# Mock responses
MOCK_TEXT_TO_PERSONA_RESPONSE = """
persona_name: Data Scientist
persona_description: A professional with expertise in statistical analysis, machine learning, and data visualization. They have strong programming skills, particularly in Python and R, and are experienced in working with large datasets to extract meaningful insights.
"""  # noqa: E501

MOCK_PERSONA_TO_PERSONA_RESPONSE = """
1. persona_name: Machine Learning Engineer
persona_description: A professional who specializes in developing and implementing machine learning models. They work closely with Data Scientists to turn data insights into practical applications.

2. persona_name: Business Analyst
persona_description: A professional who bridges the gap between data insights and business strategy. They collaborate with Data Scientists to translate complex analytical findings into actionable business recommendations.

3. persona_name: Data Engineer
persona_description: A professional responsible for designing, building, and maintaining the data infrastructure that Data Scientists rely on. They ensure data quality, accessibility, and scalability.
"""  # noqa: E501


@pytest.fixture
def persona_generator():
    return PersonaGenerator(model=MagicMock())


def test_init(persona_generator: PersonaGenerator):
    assert isinstance(persona_generator, PersonaGenerator)
    assert isinstance(persona_generator.personas, list)
    assert len(persona_generator.personas) == 0


def test_add_persona(persona_generator: PersonaGenerator):
    persona = Persona(
        name="Test Persona",
        description="Test Description",
    )
    persona_generator.add_persona(persona)
    assert persona_generator.__len__() == 1
    assert persona_generator.personas[0] == persona


def test_remove_persona(persona_generator: PersonaGenerator):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.add_persona(persona1)
    persona_generator.add_persona(persona2)

    persona_generator.__delitem__(0)
    assert persona_generator.__len__() == 1
    assert persona_generator.personas[0] == persona2

    with pytest.raises(IndexError):
        persona_generator.__delitem__(5)


def test_get_persona(persona_generator: PersonaGenerator):
    persona = Persona(
        name="Test Persona",
        description="Test Description",
    )
    persona_generator.add_persona(persona)

    assert persona_generator.__getitem__(0) == persona

    with pytest.raises(IndexError):
        persona_generator.__getitem__(5)


@patch.object(PersonaGenerator, 'step')
def test_text_to_persona(
    mock_step: MagicMock, persona_generator: PersonaGenerator
):
    mock_response = MagicMock()
    mock_response.terminated = False
    mock_response.msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        content=MOCK_TEXT_TO_PERSONA_RESPONSE,
        meta_dict={},
    )
    mock_step.return_value = mock_response

    persona = persona_generator.text_to_persona("Test text")

    assert isinstance(persona, Persona)
    assert persona.name == "Data Scientist"
    assert (
        persona.description
        and "expertise in statistical analysis" in persona.description
    )


@patch.object(PersonaGenerator, 'step')
def test_persona_to_persona(
    mock_step: MagicMock, persona_generator: PersonaGenerator
):
    mock_response = MagicMock()
    mock_response.terminated = False
    mock_response.msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        content=MOCK_PERSONA_TO_PERSONA_RESPONSE,
        meta_dict={},
    )
    mock_step.return_value = mock_response

    base_persona = Persona(name="Data Scientist", description="A data expert")
    related_personas = persona_generator.persona_to_persona(base_persona)

    assert isinstance(related_personas, list)
    assert len(related_personas) == 3
    assert related_personas[0].name == "Machine Learning Engineer"
    assert related_personas[1].name == "Business Analyst"
    assert related_personas[2].name == "Data Engineer"


def test_deduplicate(persona_generator: PersonaGenerator):
    # This test is a placeholder and should be expanded when the actual
    # deduplication logic is implemented
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.add_persona(persona1)
    persona_generator.add_persona(persona2)

    persona_generator.deduplicate()

    # As the current implementation always returns False for similarity, both
    # personas should remain
    assert len(persona_generator.personas) == 2


def test_len(persona_generator: PersonaGenerator):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.add_persona(persona1)
    persona_generator.add_persona(persona2)

    assert persona_generator.__len__() == 2


def test_iter(persona_generator: PersonaGenerator):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.add_persona(persona1)
    persona_generator.add_persona(persona2)

    personas = list(persona_generator)
    assert len(personas) == 2
    assert personas[0] == persona1
    assert personas[1] == persona2
