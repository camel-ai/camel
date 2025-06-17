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
import uuid
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

from camel.embeddings import OpenAIEmbedding
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.personas import Persona, PersonaHub
from camel.types import (
    EmbeddingModelType,
    ModelType,
    RoleType,
)

# Mock responses
MOCK_TEXT_TO_PERSONA_RESPONSE = """
{
  "persona_name": "Data Scientist",
  "persona_description": "A professional with expertise in statistical analysis, machine learning, and data visualization. They have strong programming skills, particularly in Python and R, and are experienced in working with large datasets to extract meaningful insights."
}
"""  # noqa: E501

MOCK_PERSONA_TO_PERSONA_RESPONSE = """
1. persona_name: Machine Learning Engineer
persona_description: A professional who specializes in developing and implementing machine learning models. They work closely with Data Scientists to turn data insights into practical applications.
2. persona_name: Business Analyst
persona_description: A professional who bridges the gap between data insights and business strategy. They collaborate with Data Scientists to translate complex analytical findings into actionable business recommendations.
3. persona_name: Data Engineer
persona_description: A professional who designs and maintains the data infrastructure that supports the work of Data Scientists. They ensure that data is collected, stored, and processed efficiently to enable data-driven decision-making.
"""  # noqa: E501


@pytest.fixture
def persona_generator():
    return PersonaHub(model=MagicMock())


@pytest.fixture(autouse=True)
def mock_model_factory():
    r"""Mock ModelFactory"""
    # Create a mock that is recognized as a BaseModelBackend instance
    mock_backend = MagicMock(spec=BaseModelBackend)
    # Set necessary attributes that might be accessed
    mock_backend.model_type = ModelType.DEFAULT
    mock_backend.token_limit = 4096
    mock_backend.token_counter = MagicMock()

    # Patch both ModelFactory.create and the _resolve_models method
    with (
        patch('camel.models.ModelFactory.create', return_value=mock_backend),
        patch(
            'camel.agents.ChatAgent._resolve_models', return_value=mock_backend
        ),
    ):
        yield


def test_init(persona_generator: PersonaHub):
    assert isinstance(persona_generator, PersonaHub)
    assert isinstance(persona_generator.personas, Dict)
    assert len(persona_generator.personas) == 0


def test___setitem__(persona_generator: PersonaHub):
    persona = Persona(
        name="Test Persona",
        description="Test Description",
    )
    persona_generator.__setitem__(persona)
    assert persona_generator.__len__() == 1
    assert persona_generator.personas[persona.id] == persona


def test_remove_persona(persona_generator: PersonaHub):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.__setitem__(persona1)
    persona_generator.__setitem__(persona2)

    persona_generator.__delitem__(persona1.id)
    assert persona_generator.__len__() == 1
    assert persona_generator.personas[persona2.id] == persona2

    with pytest.raises(KeyError):
        persona_generator.__delitem__(uuid.uuid4())


def test_get_persona(persona_generator: PersonaHub):
    persona = Persona(
        name="Test Persona",
        description="Test Description",
    )
    persona_generator.__setitem__(persona)

    assert persona_generator.__getitem__(persona.id) == persona

    with pytest.raises(KeyError):
        persona_generator.__getitem__(uuid.uuid4())


def test_text_to_persona(persona_generator: PersonaHub):
    mock_response = MagicMock()
    mock_response.terminated = False
    mock_response.msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        content=MOCK_TEXT_TO_PERSONA_RESPONSE,
        meta_dict={},
    )

    with patch('camel.agents.ChatAgent.step', return_value=mock_response):
        persona = persona_generator.text_to_persona(text="Test text")

    assert isinstance(persona, Persona)
    assert persona.name == "Data Scientist"
    assert (
        persona.description
        and "expertise in statistical analysis" in persona.description
    )


def test_persona_to_persona(persona_generator: PersonaHub):
    mock_response = MagicMock()
    mock_response.terminated = False
    mock_response.msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        content=MOCK_PERSONA_TO_PERSONA_RESPONSE,
        meta_dict={},
    )

    with patch('camel.agents.ChatAgent.step', return_value=mock_response):
        base_persona = Persona(
            name="Data Scientist", description="A data expert"
        )
        related_personas = persona_generator.persona_to_persona(base_persona)

    assert isinstance(related_personas, dict)
    assert len(related_personas) == 3
    assert any(
        p.name == "Machine Learning Engineer"
        for p in related_personas.values()
    )
    assert any(p.name == "Business Analyst" for p in related_personas.values())
    assert any(p.name == "Data Engineer" for p in related_personas.values())


def test_deduplicate(persona_generator: PersonaHub):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.__setitem__(persona1)
    persona_generator.__setitem__(persona2)

    persona_generator.deduplicate(
        embedding_model=OpenAIEmbedding(
            model_type=EmbeddingModelType.TEXT_EMBEDDING_3_SMALL
        )
    )

    assert (
        len(persona_generator.personas) == 1
    )  # Only one persona left as the persona descriptions are very similar


def test_is_similar(persona_generator: PersonaHub):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    assert persona_generator._is_similar(
        persona1=persona1,
        persona2=persona2,
        similarity_threshold=0.85,
        embedding_model=OpenAIEmbedding(
            model_type=EmbeddingModelType.TEXT_EMBEDDING_3_SMALL
        ),
    )


def test_len(persona_generator: PersonaHub):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.__setitem__(persona1)
    persona_generator.__setitem__(persona2)

    assert persona_generator.__len__() == 2


def test_iter(persona_generator: PersonaHub):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.__setitem__(persona1)
    persona_generator.__setitem__(persona2)

    personas = list(persona_generator)
    assert len(personas) == 2
    assert persona1 in personas
    assert persona2 in personas


def test_get_all_personas(persona_generator: PersonaHub):
    persona1 = Persona(
        name="Test Persona 1",
        description="Test Description 1",
    )
    persona2 = Persona(
        name="Test Persona 2",
        description="Test Description 2",
    )
    persona_generator.__setitem__(persona1)
    persona_generator.__setitem__(persona2)

    all_personas = persona_generator.get_all_personas()
    assert isinstance(all_personas, list)
    assert len(all_personas) == 2
    assert persona1 in all_personas
    assert persona2 in all_personas
