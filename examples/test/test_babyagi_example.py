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
import pytest
from mock import MagicMock, patch

import examples.ai_society.babyagi_playing
from camel.models import ModelFactory
from camel.societies.babyagi_playing import BabyAGI
from camel.types import ModelPlatformType, ModelType

parametrize = pytest.mark.parametrize(
    'model',
    [
        ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        ),
        pytest.param(None, marks=pytest.mark.model_backend),
    ],
)


@parametrize
def test_ai_society_babyagi_playing_example(model):
    r"""Test that the BabyAGI example structure works without actually running
    the resource-intensive parts.
    """
    # Mock BabyAGI to avoid actual instantiation and execution
    with patch(
        'examples.ai_society.babyagi_playing.BabyAGI'
    ) as mock_babyagi_class:
        mock_babyagi_instance = MagicMock()
        mock_babyagi_class.return_value = mock_babyagi_instance
        mock_response = MagicMock()
        mock_response.terminated = True
        mock_response.info = {
            'termination_reasons': 'Test completed',
            'task_name': 'Test',
            'subtasks': [],
        }
        mock_response.msg = MagicMock()
        mock_babyagi_instance.step.return_value = mock_response

        # Mock print functions to avoid console output
        with patch('examples.ai_society.babyagi_playing.print_text_animated'):
            with patch('examples.ai_society.babyagi_playing.print'):
                # Run the main function with our mocks
                examples.ai_society.babyagi_playing.main(
                    model=model, chat_turn_limit=2
                )

        mock_babyagi_class.assert_called_once()
        assert mock_babyagi_instance.step.called


@parametrize
def test_babyagi_initialization(model):
    r"""Test that BabyAGI initializes with correct parameters."""
    task_prompt = "Test task prompt"
    assistant_role = "Test Assistant"
    user_role = "Test User"

    # Mock the TaskSpecifyAgent to avoid actual API calls
    with patch(
        'camel.societies.babyagi_playing.TaskSpecifyAgent'
    ) as mock_task_specify_agent_class:
        # Create a mock instance and mock the run method
        mock_task_specify_agent = MagicMock()
        mock_task_specify_agent_class.return_value = mock_task_specify_agent
        mock_task_specify_agent.run.return_value = "Specified test task"

        # Mock the SystemMessageGenerator to avoid actual API calls
        with patch(
            'camel.societies.babyagi_playing.SystemMessageGenerator'
        ) as mock_sys_msg_generator_class:
            # Create a mock instance and mock the from_dicts method
            mock_sys_msg_generator = MagicMock()
            mock_sys_msg_generator_class.return_value = mock_sys_msg_generator
            mock_sys_msg = [MagicMock()]
            mock_sys_msg_generator.from_dicts.return_value = mock_sys_msg

            # Mock ChatAgent to avoid actual API calls
            with patch(
                'camel.societies.babyagi_playing.ChatAgent'
            ) as mock_chat_agent_class:
                mock_chat_agent = MagicMock()
                mock_chat_agent.model = model
                mock_chat_agent_class.return_value = mock_chat_agent

                babyagi = BabyAGI(
                    assistant_role_name=assistant_role,
                    assistant_agent_kwargs=dict(model=model),
                    user_role_name=user_role,
                    task_prompt=task_prompt,
                    task_specify_agent_kwargs=dict(model=model),
                )

                assert babyagi.task_prompt == task_prompt
                assert mock_task_specify_agent.run.called
                assert mock_sys_msg_generator.from_dicts.called


@parametrize
def test_babyagi_step_functionality(model):
    r"""Test that BabyAGI step method works as expected."""
    with patch(
        'examples.ai_society.babyagi_playing.BabyAGI'
    ) as mock_babyagi_class:
        mock_babyagi = MagicMock()
        mock_babyagi_class.return_value = mock_babyagi

        # Create a mock response for the step method
        mock_response = MagicMock()
        mock_response.terminated = False
        mock_response.msg = MagicMock()
        mock_response.msg.content = "Test response content"
        mock_response.info = {
            'task_name': 'Test Task',
            'subtasks': ['Subtask 1', 'Subtask 2'],
        }
        mock_babyagi.step.return_value = mock_response

        # Mock print functions to avoid console output
        with patch('examples.ai_society.babyagi_playing.print_text_animated'):
            with patch('examples.ai_society.babyagi_playing.print'):
                # Run the main function with our mocks
                examples.ai_society.babyagi_playing.main(
                    model=model, chat_turn_limit=1
                )

        # Verify BabyAGI was instantiated with expected parameters
        mock_babyagi_class.assert_called_once_with(
            assistant_role_name="Python Programmer",
            assistant_agent_kwargs=dict(model=model),
            user_role_name="Stock Trader",
            task_prompt="Develop a trading bot for the stock market",
            task_specify_agent_kwargs=dict(model=model),
        )

        assert mock_babyagi.step.called


@parametrize
def test_babyagi_termination(model):
    r"""Test that BabyAGI terminates correctly when response indicates
    termination.
    """
    with patch(
        'examples.ai_society.babyagi_playing.BabyAGI'
    ) as mock_babyagi_class:
        mock_babyagi = MagicMock()
        mock_babyagi_class.return_value = mock_babyagi

        # Create a mock response that indicates termination
        mock_response = MagicMock()
        mock_response.terminated = True
        mock_response.msg = MagicMock()
        mock_response.msg.content = "Final task completed"
        mock_response.info = {
            'termination_reasons': 'Task completed',
            'task_name': 'Final Task',
            'subtasks': [],
        }
        mock_babyagi.step.return_value = mock_response

        # Mock print functions to avoid console output
        with patch('examples.ai_society.babyagi_playing.print_text_animated'):
            with patch('examples.ai_society.babyagi_playing.print'):
                # Run the main function with our mocks
                # Set a high chat_turn_limit to verify early termination
                examples.ai_society.babyagi_playing.main(
                    model=model, chat_turn_limit=10
                )

        # Verify BabyAGI was instantiated with expected parameters
        mock_babyagi_class.assert_called_once()

        # Verify step was called exactly once (since it should terminate after
        # first step)
        mock_babyagi.step.assert_called_once()

        # Test the termination condition
        response = mock_babyagi.step.return_value
        assert response.terminated
        assert 'termination_reasons' in response.info
