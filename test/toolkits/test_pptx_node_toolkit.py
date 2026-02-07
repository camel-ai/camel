# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import json
import unittest
from unittest.mock import MagicMock, patch

from camel.toolkits.pptx_node_toolkit import PptxNodeToolkit


@patch("shutil.which")
@patch("pathlib.Path.exists")
class TestPptxNodeToolkit(unittest.TestCase):
    def setUp(self):
        self.toolkit = PptxNodeToolkit()

    @patch("subprocess.run")
    def test_create_presentation_success(
        self, mock_subprocess_run, mock_exists, mock_which
    ):
        mock_which.return_value = "/usr/bin/node"
        mock_exists.return_value = True

        # Mock successful execution
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(
            {"success": True, "path": "/path/to/test.pptx", "slides": 5}
        )
        mock_subprocess_run.return_value = mock_result

        content = [{"title": "Test Slide"}]
        filename = "test_presentation"

        result = self.toolkit.create_presentation(content, filename)

        expected_call_args = mock_subprocess_run.call_args[0][0]
        self.assertEqual(expected_call_args[0], "node")
        self.assertTrue(
            expected_call_args[2].endswith("test_presentation.pptx")
        )

        self.assertIn("Presentation created successfully", result)
        self.assertIn("/path/to/test.pptx", result)
        self.assertIn("Slides: 5", result)

        # Verify arguments passed to node script
        args = mock_subprocess_run.call_args[0][0]
        # args[3] is the content JSON string
        content_json = json.loads(args[3])
        self.assertEqual(content_json["slides"], content)
        self.assertEqual(content_json["theme"], "default")
        self.assertEqual(content_json["layout"], "LAYOUT_16x9")

    @patch("subprocess.run")
    def test_create_presentation_with_theme(
        self, mock_subprocess_run, mock_exists, mock_which
    ):
        mock_which.return_value = "/usr/bin/node"
        mock_exists.return_value = True

        # Mock successful execution
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(
            {"success": True, "path": "/path/to/test.pptx", "slides": 5}
        )
        mock_subprocess_run.return_value = mock_result

        content = [{"title": "Test Slide"}]
        filename = "test_theme"

        self.toolkit.create_presentation(
            content, filename, theme="custom_theme", layout="LAYOUT_4x3"
        )

        args = mock_subprocess_run.call_args[0][0]
        content_json = json.loads(args[3])
        self.assertEqual(content_json["theme"], "custom_theme")
        self.assertEqual(content_json["layout"], "LAYOUT_4x3")

    @patch("subprocess.run")
    def test_create_presentation_custom_node(
        self, mock_subprocess_run, mock_exists, mock_which
    ):
        mock_which.return_value = "/custom/node"
        mock_exists.return_value = True

        toolkit = PptxNodeToolkit(node_executable="/custom/node")

        # Mock successful execution
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(
            {"success": True, "path": "/path/to/test.pptx", "slides": 5}
        )
        mock_subprocess_run.return_value = mock_result

        content = [{"title": "Test Slide"}]
        filename = "test_presentation"

        toolkit.create_presentation(content, filename)

        expected_call_args = mock_subprocess_run.call_args[0][0]
        self.assertEqual(expected_call_args[0], "/custom/node")

    @patch("subprocess.run")
    def test_create_presentation_failure(
        self, mock_subprocess_run, mock_exists, mock_which
    ):
        # Mock failed execution
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(
            {"success": False, "error": "Some error occurred"}
        )
        mock_subprocess_run.return_value = mock_result

        content = [{"title": "Test Slide"}]
        filename = "test.pptx"

        result = self.toolkit.create_presentation(content, filename)

        self.assertIn(
            "Error creating presentation: Some error occurred", result
        )

    def test_create_presentation_invalid_json(self, mock_exists, mock_which):
        content = "Invalid JSON"
        filename = "test.pptx"
        result = self.toolkit.create_presentation(content, filename)
        self.assertIn("Error: Content must be valid JSON", result)

    @patch("subprocess.run")
    def test_create_presentation_node_not_found(
        self, mock_subprocess_run, mock_exists, mock_which
    ):
        mock_subprocess_run.side_effect = FileNotFoundError

        content = [{"title": "Test Slide"}]
        filename = "test.pptx"

        result = self.toolkit.create_presentation(content, filename)
        self.assertIn("Error: Node.js executable 'node' not found", result)

    def test_create_presentation_validation(self, mock_exists, mock_which):
        # Test non-dict item in list
        content = ["Not a dict"]
        filename = "test.pptx"
        result = self.toolkit.create_presentation(content, filename)
        self.assertIn("Error: Slide content must be a dictionary", result)

    @patch("subprocess.run")
    def test_create_presentation_from_js(
        self, mock_subprocess_run, mock_exists, mock_which
    ):
        mock_which.return_value = "/usr/bin/node"
        mock_exists.return_value = True

        js_code = "console.log('Generating PPTX');"
        filename = "test.pptx"

        # Mock successful execution
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_subprocess_run.return_value = mock_result

        # Mock file existence check (since we check if file created)
        # We need to patch Path.exists but it is already patched on class level
        # We need it to return True for the .pptx file check
        mock_exists.return_value = True

        result = self.toolkit.create_presentation_from_js(js_code, filename)

        self.assertIn("Presentation created successfully", result)

        # Verify subprocess called with a temp js file
        args = mock_subprocess_run.call_args[0][0]
        self.assertEqual(args[0], "node")
        self.assertTrue(args[1].endswith(".js"))
        self.assertIn("temp_gen_", args[1])
