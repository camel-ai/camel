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
import os
from unittest import TestCase
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


class TestApiKeysRequired(TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_keys(self):
        @api_keys_required([('api_key_arg', 'API_KEY')])
        def some_function(api_key_arg=None):
            return "Function called"

        with self.assertRaises(ValueError) as context:
            some_function()

        assert (
            "Missing or empty required API keys in environment variables"
            ": API_KEY" in str(context.exception)
        )

    @patch.dict(os.environ, {'API_KEY': 'secret_environment_key'}, clear=True)
    def test_keys_in_environment(self):
        @api_keys_required([('api_key_arg', 'API_KEY')])
        def some_function(api_key_arg=None):
            return f"Function called with api_key_arg={api_key_arg}"

        result = some_function()
        assert result == "Function called with api_key_arg=None"

    def test_keys_in_arguments(self):
        @api_keys_required([('api_key_arg', 'API_KEY')])
        def some_function(api_key_arg=None):
            return f"Function called with api_key_arg={api_key_arg}"

        result = some_function(api_key_arg='secret_argument_key')
        assert result == "Function called with api_key_arg=secret_argument_key"

    @patch.dict(os.environ, {'API_KEY': 'secret_environment_key'}, clear=True)
    def test_keys_in_both(self):
        @api_keys_required([('api_key_arg', 'API_KEY')])
        def some_function(api_key_arg=None):
            return f"Function called with api_key_arg={api_key_arg}"

        result = some_function(api_key_arg='secret_argument_key')
        assert result == "Function called with api_key_arg=secret_argument_key"

    def test_invalid_env_var_name_type(self):
        with self.assertRaises(TypeError) as context:

            @api_keys_required(
                [('api_key_arg', 123)]
            )  # Non-string environment variable name
            def some_function(api_key_arg=None):
                return "Function called"

            # Call the function to trigger the validation
            some_function()

        self.assertIn(
            "Environment variable name must be a string",
            str(context.exception),
        )

    def test_invalid_param_name_type(self):
        with self.assertRaises(TypeError) as context:

            @api_keys_required([(123, 'API_KEY')])  # Non-string parameter name
            def some_function(api_key_arg=None):
                return "Function called"

            # Call the function to trigger the validation
            some_function()

        self.assertIn(
            "Parameter name must be a string", str(context.exception)
        )

    @patch.dict(os.environ, {'API_KEY': ' '}, clear=True)
    def test_empty_env_var(self):
        @api_keys_required([('api_key_arg', 'API_KEY')])
        def some_function(api_key_arg=None):
            return "Function called"

        with self.assertRaises(ValueError) as context:
            some_function()

        assert (
            "Missing or empty required API keys in environment "
            "variables: API_KEY" in str(context.exception)
        )
