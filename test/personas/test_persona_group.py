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
from camel.personas.persona import Persona
from camel.personas.persona_group import PersonaGroup
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
def persona_group():
    return PersonaGroup(model=MagicMock())


def test_init(persona_group):
    assert isinstance(persona_group, PersonaGroup)
    assert persona_group.group_name == "Persona Group"
    assert persona_group.group_description == ""
    assert isinstance(persona_group.personas, list)
    assert len(persona_group.personas) == 0


def test_add_persona(persona_group):
    persona = Persona(
        index=1,
        name="Test Persona",
        description="Test Description",
        model=None,
    )
    persona_group.add_persona(persona)
    assert len(persona_group.personas) == 1
    assert persona_group.personas[0] == persona


def test_remove_persona(persona_group):
    persona1 = Persona(
        index=1,
        name="Test Persona 1",
        description="Test Description 1",
        model=None,
    )
    persona2 = Persona(
        index=2,
        name="Test Persona 2",
        description="Test Description 2",
        model=None,
    )
    persona_group.add_persona(persona1)
    persona_group.add_persona(persona2)

    persona_group.remove_persona(0)
    assert len(persona_group.personas) == 1
    assert persona_group.personas[0] == persona2

    with pytest.raises(IndexError):
        persona_group.remove_persona(5)


def test_get_persona(persona_group):
    persona = Persona(
        index=1,
        name="Test Persona",
        description="Test Description",
        model=None,
    )
    persona_group.add_persona(persona)

    assert persona_group.get_persona(0) == persona

    with pytest.raises(IndexError):
        persona_group.get_persona(5)


@patch.object(PersonaGroup, 'step')
def test_text_to_persona(mock_step, persona_group):
    mock_response = MagicMock()
    mock_response.terminated = False
    mock_response.msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        content=MOCK_TEXT_TO_PERSONA_RESPONSE,
        meta_dict={},
    )
    mock_step.return_value = mock_response

    persona = persona_group.text_to_persona("Test text")

    assert isinstance(persona, Persona)
    assert persona.name == "Data Scientist"
    assert "expertise in statistical analysis" in persona.description


@patch.object(PersonaGroup, 'step')
def test_persona_to_persona(mock_step, persona_group):
    mock_response = MagicMock()
    mock_response.terminated = False
    mock_response.msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        content=MOCK_PERSONA_TO_PERSONA_RESPONSE,
        meta_dict={},
    )
    mock_step.return_value = mock_response

    base_persona = Persona(
        index=1, name="Data Scientist", description="A data expert", model=None
    )
    related_personas = persona_group.persona_to_persona(base_persona)

    assert isinstance(related_personas, list)
    assert len(related_personas) == 3
    assert related_personas[0].name == "Machine Learning Engineer"
    assert related_personas[1].name == "Business Analyst"
    assert related_personas[2].name == "Data Engineer"


def test_deduplicate(persona_group):
    # This test is a placeholder and should be expanded when the actual
    # deduplication logic is implemented
    persona1 = Persona(
        index=1,
        name="Test Persona 1",
        description="Test Description 1",
        model=None,
    )
    persona2 = Persona(
        index=2,
        name="Test Persona 2",
        description="Test Description 2",
        model=None,
    )
    persona_group.add_persona(persona1)
    persona_group.add_persona(persona2)

    persona_group.deduplicate()

    # As the current implementation always returns False for similarity, both
    # personas should remain
    assert len(persona_group.personas) == 2


def test_len(persona_group):
    persona1 = Persona(
        index=1,
        name="Test Persona 1",
        description="Test Description 1",
        model=None,
    )
    persona2 = Persona(
        index=2,
        name="Test Persona 2",
        description="Test Description 2",
        model=None,
    )
    persona_group.add_persona(persona1)
    persona_group.add_persona(persona2)

    assert len(persona_group) == 2


def test_iter(persona_group):
    persona1 = Persona(
        index=1,
        name="Test Persona 1",
        description="Test Description 1",
        model=None,
    )
    persona2 = Persona(
        index=2,
        name="Test Persona 2",
        description="Test Description 2",
        model=None,
    )
    persona_group.add_persona(persona1)
    persona_group.add_persona(persona2)

    personas = list(persona_group)
    assert len(personas) == 2
    assert personas[0] == persona1
    assert personas[1] == persona2
