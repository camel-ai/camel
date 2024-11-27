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
from unittest.mock import Mock, patch

import pytest

from camel.loaders.apify_reader import Apify


@pytest.fixture
def apify_client_mock():
    with patch('apify_client.ApifyClient', autospec=True) as mock:
        yield mock


@pytest.fixture(autouse=True)
def set_env_vars():
    with patch.dict(os.environ, {"APIFY_API_KEY": "test_api_key"}):
        yield


def test_init(apify_client_mock):
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    assert apify._api_key == api_key
    apify_client_mock.assert_called_once_with(token=api_key)


def test_run_actor():
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    actor_id = "test_actor_id"
    run_input = {"key": "value"}
    mock_actor = Mock()
    mock_actor.call.return_value = {"result": "success"}
    apify.client.actor = Mock(return_value=mock_actor)
    result = apify.run_actor(actor_id, run_input=run_input)
    apify.client.actor.assert_called_once_with(actor_id)
    apify.client.actor.return_value.call.assert_called_once_with(
        run_input=run_input,
        content_type=None,
        build=None,
        max_items=None,
        memory_mbytes=None,
        timeout_secs=None,
        webhooks=None,
        wait_secs=None,
    )
    assert result == {"result": "success"}


def test_get_dataset_client():
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    dataset_id = "test_dataset_id"
    mock_dataset = Mock()
    apify.client.dataset = Mock(return_value=mock_dataset)
    result = apify.get_dataset_client(dataset_id)
    apify.client.dataset.assert_called_once_with(dataset_id)
    assert result == mock_dataset


def test_get_dataset():
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    dataset_id = "test_dataset_id"
    mock_client = Mock()
    mock_client.get.return_value = {"data": "dataset"}
    apify.get_dataset_client = lambda x: mock_client

    result = apify.get_dataset(dataset_id)
    assert result == {"data": "dataset"}


def test_update_dataset():
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    dataset_id = "test_dataset_id"
    name = "new_name"
    mock_client = Mock()
    mock_client.update.return_value = {"name": name}
    apify.get_dataset_client = lambda x: mock_client

    result = apify.update_dataset(dataset_id, name)
    assert result == {"name": name}


def test_get_dataset_items():
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    dataset_id = "test_dataset_id"
    mock_client = Mock()
    mock_client.list_items.return_value.items = ["item1", "item2"]
    apify.get_dataset_client = lambda x: mock_client

    result = apify.get_dataset_items(dataset_id)
    assert result == ["item1", "item2"]


def test_get_datasets():
    api_key = "test_api_key"
    apify = Apify(api_key=api_key)
    mock_client = Mock()
    mock_client.datasets.return_value.list.return_value.items = [
        {"name": "dataset1"},
        {"name": "dataset2"},
    ]
    apify.client = mock_client

    result = apify.get_datasets()
    apify.client.datasets.return_value.list.assert_called_once_with(
        unnamed=None, limit=None, offset=None, desc=None
    )
    assert result == [{"name": "dataset1"}, {"name": "dataset2"}]
