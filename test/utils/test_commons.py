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

import pytest

from camel.utils import api_keys_required, dependencies_required, get_task_list


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


def test_api_keys_required():
    os.environ['API_KEY_1'] = 'API_KEY_1_VALUE'
    os.environ['API_KEY_2'] = 'API_KEY_2_VALUE'

    @api_keys_required('API_KEY_1', 'API_KEY_2')
    def mock_api_keys_exist():
        return True

    assert True if mock_api_keys_exist() else False

    @api_keys_required('API_KEY_1', 'API_KEY_2', 'API_KEY_3')
    def mock_api_keys_not_exist():
        return True

    with pytest.raises(ValueError) as exc:
        mock_api_keys_not_exist()

    assert "Missing API keys: API_KEY_3" in str(exc.value)
