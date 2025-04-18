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
def mock_mineru():
    """Create a mock MinerU client with all required responses."""
    mock = MagicMock(spec=MinerU)

    # Mock single URL extraction
    mock.extract_url.return_value = {'task_id': 'test_task'}

    # Mock batch URL extraction
    mock.batch_extract_urls.return_value = 'batch_123'

    # Mock task status
    mock.get_task_status.return_value = {
        'status': 'processing',
        'progress': 50,
    }

    # Mock batch status
    mock.get_batch_status.return_value = {
        'status': 'processing',
        'files_completed': 1,
        'files_total': 2,
    }

    # Mock wait_for_completion with different responses
    def wait_for_completion_side_effect(task_id, is_batch=False, timeout=None):
        if is_batch:
            return {
                'status': 'completed',
                'extract_result': [
                    {'url': 'https://test.com/doc1.pdf', 'status': 'success'},
                    {'url': 'https://test.com/doc2.pdf', 'status': 'success'},
                ],
            }
        return {
            'status': 'success',
            'full_zip_url': 'https://example.com/test.zip',
        }

    mock.wait_for_completion.side_effect = wait_for_completion_side_effect
    return mock


@pytest.fixture
def mineru_toolkit(mock_mineru):
    """Create a MinerUToolkit instance with mocked client."""
    with patch.dict('os.environ', {'MINERU_API_KEY': 'fake_api_key'}):
        with patch(
            'camel.toolkits.mineru_toolkit.MinerU', return_value=mock_mineru
        ):
            toolkit = MinerUToolkit()
            toolkit.client = mock_mineru
            return toolkit


def test_extract_from_urls_single(mineru_toolkit):
    """Test single URL extraction."""
    result = mineru_toolkit.extract_from_urls("https://test.com/doc.pdf")
    assert result['status'] == 'success'
    assert result['full_zip_url'] == 'https://example.com/test.zip'
    mineru_toolkit.client.extract_url.assert_called_once()


def test_extract_from_urls_batch(mineru_toolkit):
    """Test batch URL extraction."""
    urls = ["https://test.com/doc1.pdf", "https://test.com/doc2.pdf"]
    result = mineru_toolkit.extract_from_urls(urls)
    assert result['status'] == 'completed'
    assert len(result['extract_result']) == 2
    mineru_toolkit.client.batch_extract_urls.assert_called_once()


def test_extract_from_urls_batch_no_wait(mineru_toolkit):
    """Test batch URL extraction without waiting."""
    mineru_toolkit.wait = False
    urls = ["https://test.com/doc1.pdf", "https://test.com/doc2.pdf"]
    result = mineru_toolkit.extract_from_urls(urls)
    assert 'batch_id' in result
    assert result['batch_id'] == 'batch_123'
    mineru_toolkit.client.batch_extract_urls.assert_called_once()


def test_get_task_status(mineru_toolkit):
    """Test getting task status."""
    result = mineru_toolkit.get_task_status('test_task')
    assert result['status'] == 'processing'
    assert result['progress'] == 50
    mineru_toolkit.client.get_task_status.assert_called_once_with('test_task')


def test_get_batch_status(mineru_toolkit):
    """Test getting batch status."""
    result = mineru_toolkit.get_batch_status('batch_123')
    assert result['status'] == 'processing'
    assert result['files_completed'] == 1
    assert result['files_total'] == 2
    mineru_toolkit.client.get_batch_status.assert_called_once_with('batch_123')


def test_get_tools(mineru_toolkit):
    """Test getting available tools."""
    tools = mineru_toolkit.get_tools()
    assert len(tools) == 3
    tool_names = {tool.get_function_name() for tool in tools}
    expected_names = {
        'extract_from_urls',
        'get_task_status',
        'get_batch_status',
    }
    assert tool_names == expected_names


def test_error_handling(mineru_toolkit):
    """Test error handling when API calls fail."""
    # Test single URL extraction error
    mineru_toolkit.client.extract_url.side_effect = Exception("API Error")
    mineru_toolkit.client.wait_for_completion.side_effect = (
        None  # Reset any side effects
    )
    mineru_toolkit.timeout = None  # Disable timeout to avoid threading issues
    with pytest.raises(Exception) as exc_info:
        mineru_toolkit.extract_from_urls("https://test.com/doc.pdf")
    assert "API Error" in str(exc_info.value)

    # Test batch URL extraction error
    mineru_toolkit.client.batch_extract_urls.side_effect = Exception(
        "Batch API Error"
    )
    with pytest.raises(Exception) as exc_info:
        mineru_toolkit.extract_from_urls(
            ["https://test.com/doc1.pdf", "https://test.com/doc2.pdf"]
        )
    assert "Batch API Error" in str(exc_info.value)

    # Test status check errors
    mineru_toolkit.client.get_task_status.side_effect = Exception(
        "Status API Error"
    )
    with pytest.raises(Exception) as exc_info:
        mineru_toolkit.get_task_status("test_task")
    assert "Status API Error" in str(exc_info.value)

    mineru_toolkit.client.get_batch_status.side_effect = Exception(
        "Batch Status Error"
    )
    with pytest.raises(Exception) as exc_info:
        mineru_toolkit.get_batch_status("batch_123")
    assert "Batch Status Error" in str(exc_info.value)
