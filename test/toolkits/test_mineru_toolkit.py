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

from unittest.mock import MagicMock, patch

import pytest

from camel.loaders.mineru_extractor import MinerU
from camel.toolkits import MinerUToolkit


@pytest.fixture
def mineru_toolkit():
    # Create a mock MinerU class
    mock_mineru = MagicMock()

    # Mock single URL extraction
    mock_mineru.extract_url.return_value = {'task_id': 'test_task'}

    # Mock batch URL extraction
    mock_mineru.batch_extract_urls.return_value = 'batch_123'

    # Mock wait_for_completion with different responses for single and batch
    def wait_for_completion_side_effect(task_id, is_batch=False, timeout=None):
        if is_batch:
            return {
                'status': 'completed',
                'extract_result': [
                    {'url': 'https://test.com/doc1.pdf', 'status': 'success'},
                    {'url': 'https://test.com/doc2.pdf', 'status': 'success'},
                ],
            }
        else:
            return {
                'status': 'success',
                'full_zip_url': 'https://example.com/test.zip',
            }

    mock_mineru.wait_for_completion.side_effect = (
        wait_for_completion_side_effect
    )

    # Mock status checks
    mock_mineru.get_task_status.return_value = {
        'status': 'processing',
        'progress': 50,
    }

    mock_mineru.get_batch_status.return_value = {
        'status': 'processing',
        'files_completed': 1,
        'files_total': 2,
    }

    # Create toolkit with mocked MinerU
    with patch.dict('os.environ', {'MINERU_API_KEY': 'fake_api_key'}):
        with patch(
            'camel.toolkits.mineru_toolkit.MinerU', return_value=mock_mineru
        ):
            toolkit = MinerUToolkit()
            return toolkit


def test_initialization():
    # Test initialization with API key from environment
    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        toolkit = MinerUToolkit()
        assert isinstance(toolkit.client, MinerU)

    # Test initialization with custom API URL
    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        custom_url = "https://custom.mineru.net/api/v4"
        toolkit = MinerUToolkit(api_url=custom_url)
        assert isinstance(toolkit.client, MinerU)

    # Test initialization without API key
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError):
            MinerUToolkit()


def test_extract_from_urls_single(mineru_toolkit):
    result = mineru_toolkit.extract_from_urls(
        urls="https://test.com/doc.pdf",
        enable_formula=True,
        enable_table=True,
        language="en",
    )

    assert result['status'] == 'success'
    assert result['full_zip_url'] == 'https://example.com/test.zip'

    mineru_toolkit.client.extract_url.assert_called_once()
    mineru_toolkit.client.wait_for_completion.assert_called_once_with(
        'test_task', timeout=300
    )


def test_extract_from_urls_batch(mineru_toolkit):
    urls = ["https://test.com/doc1.pdf", "https://test.com/doc2.pdf"]
    result = mineru_toolkit.extract_from_urls(urls=urls)

    assert result['status'] == 'completed'
    assert len(result['extract_result']) == 2
    assert all(
        item['status'] == 'success' for item in result['extract_result']
    )

    # Verify the batch extraction was called with correct parameters
    mineru_toolkit.client.batch_extract_urls.assert_called_once()
    mineru_toolkit.client.wait_for_completion.assert_called_once_with(
        'batch_123', is_batch=True, timeout=600
    )


def test_extract_from_urls_no_wait(mineru_toolkit):
    # Test single URL without waiting
    single_result = mineru_toolkit.extract_from_urls(
        urls="https://test.com/doc.pdf", wait=False
    )
    assert 'task_id' in single_result
    # Verify extract_url was called but wait_for_completion was not
    mineru_toolkit.client.extract_url.assert_called_once()
    mineru_toolkit.client.wait_for_completion.assert_not_called()

    # Reset mock counters
    mineru_toolkit.client.reset_mock()

    # Test multiple URLs without waiting
    batch_result = mineru_toolkit.extract_from_urls(
        urls=["https://test.com/doc1.pdf", "https://test.com/doc2.pdf"],
        wait=False,
    )
    assert 'batch_id' in batch_result
    # Verify batch_extract_urls was called but wait_for_completion was not
    mineru_toolkit.client.batch_extract_urls.assert_called_once()
    mineru_toolkit.client.wait_for_completion.assert_not_called()


def test_get_task_status(mineru_toolkit):
    result = mineru_toolkit.get_task_status('task_123')

    assert result['status'] == 'processing'
    assert result['progress'] == 50
    mineru_toolkit.client.get_task_status.assert_called_once_with('task_123')


def test_get_batch_status(mineru_toolkit):
    result = mineru_toolkit.get_batch_status('batch_123')

    assert result['status'] == 'processing'
    assert result['files_completed'] == 1
    assert result['files_total'] == 2
    mineru_toolkit.client.get_batch_status.assert_called_once_with('batch_123')
