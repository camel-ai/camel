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
from unittest.mock import patch

import pytest

from camel.utils import (
    api_keys_required,
    dependencies_required,
    get_system_information,
    get_task_list,
    is_docker_running,
    to_pascal,
)


def test_get_task_list():
    task_response = ""
    task_list = get_task_list(task_response)
    assert isinstance(task_list, list)
    assert len(task_list) == 0

    task_response = "1.Task1\n2.Task2\n3.Task3"
    task_list = get_task_list(task_response)
    assert isinstance(task_list, list)
    assert isinstance(task_list[0], str)
    assert len(task_list) == 3

    task_response = "1.Task12.Task2\n3.Task3"
    task_list = get_task_list(task_response)
    assert isinstance(task_list, list)
    assert isinstance(task_list[0], str)
    assert len(task_list) == 2

    task_response = "#.Task12.Task2\n3.Task3"
    task_list = get_task_list(task_response)
    assert isinstance(task_list, list)
    assert isinstance(task_list[0], str)
    assert len(task_list) == 1


def test_dependencies_required(monkeypatch):
    @dependencies_required('os')
    def mock_dependencies_present():
        return True

    assert True if mock_dependencies_present() else False

    @dependencies_required('some_module_not_exist')
    def mock_dependencies_not_present():
        return True

    with pytest.raises(ImportError) as exc:
        mock_dependencies_not_present()

    assert "Missing required modules: some_module_not_exist" in str(exc.value)


@pytest.fixture
def setup_env_vars():
    original_env = os.environ.copy()
    os.environ['API_KEY_1'] = 'API_KEY_1_VALUE'
    os.environ['API_KEY_2'] = 'API_KEY_2_VALUE'
    yield
    os.environ.clear()
    os.environ.update(original_env)


def test_api_keys_required(setup_env_vars):
    class MockClass:
        @api_keys_required('API_KEY_1', 'API_KEY_2')
        def mock_api_keys_exist(self):
            return True

        @api_keys_required('API_KEY_1', 'API_KEY_2', 'API_KEY_3')
        def mock_api_keys_not_exist(self):
            return True

    mock_instance = MockClass()

    # Test case where all required API keys are present
    assert mock_instance.mock_api_keys_exist() is True

    # Test case where some required API keys are missing
    with pytest.raises(ValueError) as exc:
        mock_instance.mock_api_keys_not_exist()
    assert "Missing API keys: API_KEY_3" in str(exc.value)

    # Test case with no API keys set
    os.environ.clear()
    with pytest.raises(ValueError) as exc:
        mock_instance.mock_api_keys_exist()
    assert "Missing API keys: API_KEY_1, API_KEY_2" in str(exc.value)


def test_api_keys_required_empty(setup_env_vars):
    class MockClass:
        @api_keys_required()
        def mock_no_keys_required(self):
            return True

    mock_instance = MockClass()
    assert mock_instance.mock_no_keys_required() is True


def test_api_keys_required_non_existent(setup_env_vars):
    class MockClass:
        @api_keys_required('NON_EXISTENT_KEY')
        def mock_non_existent_key(self):
            return True

    mock_instance = MockClass()
    with pytest.raises(ValueError) as exc:
        mock_instance.mock_non_existent_key()
    assert "Missing API keys: NON_EXISTENT_KEY" in str(exc.value)


def test_get_system_information():
    # Call the function
    sys_info = get_system_information()

    # Check if the result is a dictionary
    assert isinstance(sys_info, dict)

    # Define the expected keys
    expected_keys = [
        "OS Name",
        "System",
        "Release",
        "Version",
        "Machine",
        "Processor",
        "Platform",
    ]

    # Check if all expected keys are in the returned dictionary
    assert all(key in sys_info for key in expected_keys)

    # Check if all values are non-empty strings
    assert all(isinstance(value, str) and value for value in sys_info.values())


def test_to_pascal_standard_case():
    assert to_pascal("snake_case") == "SnakeCase"


def test_to_pascal_with_numbers():
    assert to_pascal("snake2_case") == "Snake2Case"


def test_to_pascal_single_word():
    assert to_pascal("snake") == "Snake"


def test_to_pascal_empty_string():
    assert to_pascal("") == ""


def test_to_pascal_already_pascal_case():
    assert to_pascal("PascalCase") == "PascalCase"


def test_to_pascal_mixed_case():
    assert to_pascal("sNake_cAse") == "SnakeCase"


def test_to_pascal_with_special_characters():
    assert (
        to_pascal("snake_case_with_special_characters!@#")
        == "SnakeCaseWithSpecialCharacters!@#"
    )


def test_to_pascal_with_multiple_underscores():
    assert to_pascal("snake__case") == "SnakeCase"


def test_to_pascal_with_trailing_underscore():
    assert to_pascal("snake_case_") == "SnakeCase"


@patch('camel.utils.commons.subprocess.run')
def test_is_docker_running(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 0
    assert is_docker_running()

    mock_subprocess_run.return_value.returncode = 1
    assert not is_docker_running()

    mock_subprocess_run.side_effect = FileNotFoundError
    assert not is_docker_running()
