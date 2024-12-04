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
from unittest.mock import MagicMock, patch

from camel.toolkits import MeshyToolkit


class TestMeshyToolkit(unittest.TestCase):
    @patch("requests.post")
    def test_generate_3d_preview(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "task_id_123"}
        mock_post.return_value = mock_response

        toolkit = MeshyToolkit()
        prompt = "A 3D model of a cat"
        art_style = "cartoon"
        negative_prompt = "No dogs"

        # Act
        result = toolkit.generate_3d_preview(
            prompt, art_style, negative_prompt
        )

        # Assert
        mock_post.assert_called_once_with(
            "https://api.meshy.ai/v2/text-to-3d",
            headers={"Authorization": f"Bearer {toolkit.api_key}"},
            json={
                "mode": "preview",
                "prompt": prompt,
                "art_style": art_style,
                "negative_prompt": negative_prompt,
            },
        )
        self.assertEqual(result, {"result": "task_id_123"})

    @patch("requests.post")
    def test_refine_3d_model(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "task_id_456"}
        mock_post.return_value = mock_response

        toolkit = MeshyToolkit()
        preview_task_id = "task_id_123"

        # Act
        result = toolkit.refine_3d_model(preview_task_id)

        # Assert
        mock_post.assert_called_once_with(
            "https://api.meshy.ai/v2/text-to-3d",
            headers={"Authorization": f"Bearer {toolkit.api_key}"},
            json={"mode": "refine", "preview_task_id": preview_task_id},
        )
        self.assertEqual(result, {"result": "task_id_456"})

    @patch("requests.get")
    def test_get_task_status(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "SUCCEEDED",
            "result": "final_task_id",
        }
        mock_get.return_value = mock_response

        toolkit = MeshyToolkit()
        task_id = "task_id_123"

        # Act
        result = toolkit.get_task_status(task_id)

        # Assert
        mock_get.assert_called_once_with(
            f"https://api.meshy.ai/v2/text-to-3d/{task_id}",
            headers={"Authorization": f"Bearer {toolkit.api_key}"},
        )
        self.assertEqual(
            result, {"status": "SUCCEEDED", "result": "final_task_id"}
        )

    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    def test_wait_for_task_completion_success(self, mock_sleep, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "SUCCEEDED",
            "result": "final_task_id",
        }
        mock_get.return_value = mock_response

        toolkit = MeshyToolkit()
        task_id = "task_id_123"

        # Act
        result = toolkit.wait_for_task_completion(task_id)

        # Assert
        mock_get.assert_called()
        self.assertEqual(
            result, {"status": "SUCCEEDED", "result": "final_task_id"}
        )

    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    def test_wait_for_task_completion_timeout(self, mock_sleep, mock_get):
        # Arrange
        toolkit = MeshyToolkit()
        task_id = "task_id_123"
        mock_get.return_value.json.return_value = {
            "status": "PENDING"
        }  # Simulate pending status

        # Act & Assert
        with self.assertRaises(TimeoutError):
            toolkit.wait_for_task_completion(
                task_id, timeout=1
            )  # Timeout after 1 second

    @patch("requests.post")
    @patch("requests.get")
    @patch("time.sleep", return_value=None)
    def test_generate_3d_model_complete(self, mock_sleep, mock_get, mock_post):
        # Arrange
        mock_preview_response = MagicMock()
        mock_preview_response.raise_for_status = MagicMock()
        mock_preview_response.json.return_value = {"result": "preview_task_id"}
        mock_post.return_value = mock_preview_response

        mock_refine_response = MagicMock()
        mock_refine_response.raise_for_status = MagicMock()
        mock_refine_response.json.return_value = {"result": "refine_task_id"}
        mock_post.return_value = mock_refine_response

        mock_status_response = MagicMock()
        mock_status_response.raise_for_status = MagicMock()
        mock_status_response.json.return_value = {
            "status": "SUCCEEDED",
            "result": "final_task_id",
        }
        mock_get.return_value = mock_status_response

        toolkit = MeshyToolkit()
        prompt = "A 3D model of a cat"
        art_style = "cartoon"
        negative_prompt = "No dogs"

        # Act
        result = toolkit.generate_3d_model_complete(
            prompt, art_style, negative_prompt
        )

        # Assert
        self.assertEqual(
            result, {"status": "SUCCEEDED", "result": "final_task_id"}
        )
