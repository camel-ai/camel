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
import time
from unittest import TestCase
from unittest.mock import patch

import pytest

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import (
    BatchProcessor,
    api_keys_required,
    dependencies_required,
    get_system_information,
    get_task_list,
    is_docker_running,
    retry_on_error,
    to_pascal,
    with_timeout,
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


class TestRetryOnError(TestCase):
    def test_successful_execution(self):
        @retry_on_error()
        def successful_func():
            return "success"

        result = successful_func()
        self.assertEqual(result, "success")

    def test_retry_on_failure(self):
        attempts = []

        @retry_on_error(max_retries=2, initial_delay=0.1)
        def failing_func():
            attempts.append(1)
            if len(attempts) < 2:
                raise ValueError("Test error")
            return "success"

        result = failing_func()
        self.assertEqual(result, "success")
        self.assertEqual(len(attempts), 2)

    def test_max_retries_exceeded(self):
        attempts = []

        @retry_on_error(max_retries=2, initial_delay=0.1)
        def always_failing_func():
            attempts.append(1)
            raise ValueError("Test error")

        with self.assertRaises(ValueError):
            always_failing_func()
        self.assertEqual(len(attempts), 3)  # Initial attempt + 2 retries


class TestBatchProcessor(TestCase):
    def setUp(self):
        self.processor = BatchProcessor(
            max_workers=2,
            initial_batch_size=5,
            monitoring_interval=0.0,  # Set to 0 to force resource check
            cpu_threshold=90.0,
            memory_threshold=90.0,
        )

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_resource_based_adjustment(self, mock_memory, mock_cpu):
        mock_cpu.return_value = 95.0
        mock_memory.return_value.percent = 95.0

        self.assertEqual(self.processor.batch_size, 5)

        self.processor.last_check_time = 0

        self.processor.adjust_batch_size(True)

        expected_size = int(5 * self.processor.backoff_factor)
        self.assertEqual(self.processor.batch_size, expected_size)
        self.assertEqual(self.processor.max_workers, 1)

    def test_success_based_adjustment(self):
        initial_size = self.processor.batch_size

        self.processor.adjust_batch_size(True)
        self.assertGreater(self.processor.batch_size, initial_size)

        self.processor.adjust_batch_size(False)
        self.assertLess(
            self.processor.batch_size, self.processor.batch_size * 1.2
        )

    def test_performance_metrics(self):
        self.processor.adjust_batch_size(True, 1.0)
        self.processor.adjust_batch_size(False, 2.0)
        self.processor.adjust_batch_size(True, 1.5)

        metrics = self.processor.get_performance_metrics()

        self.assertEqual(metrics['total_processed'], 3)
        self.assertAlmostEqual(metrics['error_rate'], 33.33333333333333)
        self.assertAlmostEqual(metrics['avg_processing_time'], 1.5)
        self.assertEqual(metrics['current_workers'], 2)


def test_tool_function():
    return "test result"


class MockToolkit(BaseToolkit):
    def __init__(self, delay_seconds=0, timeout=None):
        super().__init__(timeout=timeout)
        self.delay_seconds = delay_seconds
        self.tools = [FunctionTool(func=test_tool_function)]

    def run(self):
        time.sleep(self.delay_seconds)
        return "run success"


def test_toolkit_custom_timeout():
    r"""Test that toolkit accepts custom timeout."""
    custom_timeout = 300
    toolkit = MockToolkit(timeout=custom_timeout)
    assert toolkit.timeout == custom_timeout


def test_toolkit_within_timeout():
    r"""Test toolkit operation completes within timeout period."""
    toolkit = MockToolkit(delay_seconds=1, timeout=2)
    assert toolkit.run() == "run success"


def test_toolkit_timeout_exceeded():
    r"""Test that operation times out when exceeding timeout period."""
    toolkit = MockToolkit(delay_seconds=2, timeout=1)
    result = toolkit.run()
    assert result == "Function `run` execution timed out, exceeded 1 seconds."


def test_direct_timeout_decorator():
    r"""Test direct use of timeout decorator with explicit value."""

    @with_timeout(1)
    def slow_function():
        time.sleep(2)
        return "success"

    result = slow_function()
    assert (
        result
        == "Function `slow_function` execution timed out, exceeded 1 seconds."
    )


def test_direct_timeout_no_delay():
    r"""Test direct use of timeout decorator with no delay."""

    @with_timeout(2)
    def fast_function():
        return "success"

    result = fast_function()
    assert result == "success"


def test_timeout_with_exception():
    @with_timeout(2)
    def function_that_raises():
        raise ValueError("Test exception")

    with pytest.raises(ValueError) as exc_info:
        function_that_raises()

    assert "Test exception" in str(exc_info.value)


def test_timeout_with_exception_type_preserved():
    r"""Test that exception type is preserved when re-raised."""

    class CustomException(Exception):
        pass

    @with_timeout(2)
    def function_with_custom_exception():
        raise CustomException("Custom error message")

    with pytest.raises(CustomException) as exc_info:
        function_with_custom_exception()

    assert "Custom error message" in str(exc_info.value)


def test_timeout_preserves_traceback():
    r"""Test that the original traceback is preserved when exception is
    re-raised.
    """

    @with_timeout(2)
    def function_with_nested_calls():
        def inner_function():
            def deepest_function():
                raise ValueError("Error from deepest function")

            return deepest_function()

        return inner_function()

    with pytest.raises(ValueError) as exc_info:
        function_with_nested_calls()

    # Check that the traceback contains the function names from the original
    # call stack
    import traceback

    tb_str = ''.join(traceback.format_tb(exc_info.tb))
    # The traceback should contain references to our nested functions
    assert "deepest_function" in tb_str
    assert "inner_function" in tb_str
    assert "Error from deepest function" in str(exc_info.value)
