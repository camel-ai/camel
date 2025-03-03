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

import unittest
from unittest.mock import mock_open, patch

from camel.loaders import ChunkrLoader


class TestChunkrReader(unittest.TestCase):
    @patch('requests.post')
    @patch(
        'builtins.open', new_callable=mock_open, read_data='fake file content'
    )
    def test_submit_task_success(self, mock_file, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {'task_id': '12345'}

        reader = ChunkrLoader(api_key='test_api_key')
        task_id = reader.submit_task('fake_path.txt')

        self.assertEqual(task_id, '12345')
        mock_post.assert_called_once()
        mock_file.assert_called_once_with('fake_path.txt', 'rb')

    @patch('requests.post')
    @patch(
        'builtins.open', new_callable=mock_open, read_data='fake file content'
    )
    def test_submit_task_no_task_id(self, mock_file, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {}

        reader = ChunkrLoader(api_key='test_api_key')

        with self.assertRaises(ValueError) as context:
            reader.submit_task('fake_path.txt')

        self.assertEqual(
            str(context.exception),
            "Failed to submit task: Task ID not returned in the response.",
        )

    @patch('requests.get')
    def test_get_task_output_success(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            'status': 'Succeeded',
            'result': 'Some result',
        }

        reader = ChunkrLoader(api_key='test_api_key')
        result = reader.get_task_output('12345')

        self.assertIn('result', result)
        mock_get.assert_called_once_with(
            'https://api.chunkr.ai/api/v1/task/12345',
            headers=reader._headers,
            timeout=reader.timeout,
        )

    @patch('requests.get')
    def test_get_task_output_max_retries(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {'status': 'Pending'}

        reader = ChunkrLoader(api_key='test_api_key')

        with self.assertRaises(RuntimeError) as context:
            reader.get_task_output('12345', max_retries=2)

        self.assertEqual(
            str(context.exception), "Max retries reached for task 12345."
        )
        self.assertEqual(mock_get.call_count, 2)
