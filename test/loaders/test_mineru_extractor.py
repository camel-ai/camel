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

from unittest.mock import Mock, patch

import pytest

from camel.loaders import MinerU


@pytest.fixture
def mock_response():
    return {
        'data': {
            'task_id': '12345',
            'state': 'done',
            'full_zip_url': 'https://cdn-mineru.openxlab.org.cn/pdf/test.zip',
        }
    }


@pytest.fixture
def mock_batch_response():
    return {
        'data': {
            'batch_id': 'batch_123',
            'extract_result': [
                {
                    'data_id': 'doc1',
                    'file_name': '2311.10993.pdf',
                    'state': 'done',
                    'full_zip_url': 'https://cdn-mineru.openxlab.org.cn/pdf/1.zip',
                },
                {
                    'data_id': 'doc2',
                    'file_name': '2310.07298.pdf',
                    'state': 'done',
                    'full_zip_url': 'https://cdn-mineru.openxlab.org.cn/pdf/2.zip',
                },
            ],
        }
    }


def test_initialization():
    # Test initialization with API key from environment
    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        mineru = MinerU(
            is_ocr=False,
            enable_formula=True,
            enable_table=False,
            layout_model='layoutlmv3',
            language='zh',
        )
        assert mineru._api_key == 'test_key'
        assert mineru._api_url == 'https://mineru.net/api/v4'
        assert mineru.is_ocr is False
        assert mineru.enable_formula is True
        assert mineru.enable_table is False
        assert mineru.layout_model == 'layoutlmv3'
        assert mineru.language == 'zh'

    # Test initialization with custom API URL
    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        custom_url = 'https://custom.mineru.net/api/v4'
        mineru = MinerU(api_url=custom_url)
        assert mineru._api_url == custom_url

    # Test initialization without API key
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError):
            MinerU()


@patch('requests.post')
def test_extract_url(mock_post, mock_response):
    mock_post.return_value.json.return_value = mock_response
    mock_post.return_value.raise_for_status = Mock()

    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        mineru = MinerU(
            is_ocr=False,
            enable_formula=False,
            enable_table=False,
            layout_model='layoutlmv3',
            language='zh',
        )
        result = mineru.extract_url(
            url='https://arxiv.org/pdf/2311.10993.pdf',
        )

    assert result == mock_response['data']
    mock_post.assert_called_once()

    # Get the actual payload sent to the API
    called_args = mock_post.call_args
    assert called_args is not None
    called_payload = called_args[1]['json']

    assert called_payload['url'] == 'https://arxiv.org/pdf/2311.10993.pdf'
    # Remove assertions for payload parameters that aren't being sent


@patch('requests.post')
def test_batch_extract_urls(mock_post, mock_batch_response):
    mock_post.return_value.json.return_value = mock_batch_response
    mock_post.return_value.raise_for_status = Mock()

    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        mineru = MinerU(
            is_ocr=False,
            enable_formula=False,
            enable_table=False,
            layout_model='layoutlmv3',
            language='zh',
        )
        files = [
            {
                'url': 'https://arxiv.org/pdf/2311.10993.pdf',
                'is_ocr': False,
                'data_id': 'doc1',
            },
            {
                'url': 'https://arxiv.org/pdf/2310.07298.pdf',
                'is_ocr': False,
                'data_id': 'doc2',
            },
        ]
        result = mineru.batch_extract_urls(
            files=files,
        )

    assert result == mock_batch_response['data']['batch_id']
    mock_post.assert_called_once()

    # Get the actual payload sent to the API
    called_args = mock_post.call_args
    assert called_args is not None
    called_payload = called_args[1]['json']

    assert called_payload['files'] == files
    # Remove assertions for payload parameters that aren't being sent


@patch('requests.get')
def test_get_task_status(mock_get, mock_response):
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status = Mock()

    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        mineru = MinerU()
        result = mineru.get_task_status('12345')

    assert result == mock_response['data']
    mock_get.assert_called_once()


@patch('requests.get')
def test_get_batch_status(mock_get, mock_batch_response):
    mock_get.return_value.json.return_value = mock_batch_response
    mock_get.return_value.raise_for_status = Mock()

    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        mineru = MinerU()
        result = mineru.get_batch_status('batch_123')

    assert result == mock_batch_response['data']
    mock_get.assert_called_once()


@patch('time.sleep', return_value=None)
def test_wait_for_completion(mock_sleep, mock_response):
    with patch.dict('os.environ', {'MINERU_API_KEY': 'test_key'}):
        mineru = MinerU()

        # Mock get_task_status for single task
        mineru.get_task_status = Mock(return_value={'state': 'done'})
        result = mineru.wait_for_completion('12345')
        assert result['state'] == 'done'

        # Mock get_batch_status for batch task
        mineru.get_batch_status = Mock(
            return_value={'extract_result': [{'state': 'done'}]}
        )
        result = mineru.wait_for_completion('batch_123', is_batch=True)
        assert result['extract_result'][0]['state'] == 'done'

        # Test timeout
        mineru.get_task_status = Mock(return_value={'state': 'processing'})
        with pytest.raises(TimeoutError):
            mineru.wait_for_completion('12345', timeout=0)

        # Test task failure
        mineru.get_task_status = Mock(
            return_value={'state': 'failed', 'err_msg': 'Error'}
        )
        with pytest.raises(RuntimeError):
            mineru.wait_for_completion('12345')
