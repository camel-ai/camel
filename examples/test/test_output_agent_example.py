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
import unittest
from unittest.mock import MagicMock, mock_open, patch

from examples.output_agent.get_instruction import main


class TestMainFunction(unittest.TestCase):

    # Patch the required methods and set default return values
    def setUp(self):
        self.mock_open_patcher = patch(
            'examples.output_agent.get_instruction.open',
            mock_open(read_data=b"<html>Test Content</html>"))
        self.mock_html_patcher = patch(
            'examples.output_agent.get_instruction.HtmlFile.from_bytes',
            return_value=MagicMock(docs=[{
                'page_content': 'Test Content'
            }]))
        self.mock_output_agent_patcher = patch(
            'examples.output_agent.get_instruction.OutputAgent')

        self.mock_file_open = self.mock_open_patcher.start()
        self.mock_html_file_from_bytes = self.mock_html_patcher.start()
        self.mock_output_agent = self.mock_output_agent_patcher.start()
        self.mock_output_agent_instance = self.mock_output_agent.return_value
        (self.mock_output_agent_instance.generate_detailed_instruction.
         return_value) = 'Mock Instruction'

    def tearDown(self):
        # Stop the patchers
        self.mock_open_patcher.stop()
        self.mock_html_patcher.stop()
        self.mock_output_agent_patcher.stop()

    def test_main(self):

        # Patch print within the test
        with patch('builtins.print') as mock_print:
            main()

            # Ensure the file was read and converted to BytesIO
            self.mock_file_open.assert_called_with(
                "examples/output_agent/"
                "multi_agent_output_Supply_Chain_en.html", "rb")

            # Get the actual BytesIO object passed to the mock method
            actual_bytes_io = self.mock_html_file_from_bytes.call_args[0][0]

            # Ensure the contents of the BytesIO object match expected contents
            self.assertEqual(actual_bytes_io.getvalue(),
                             b"<html>Test Content</html>")

            # Ensure OutputAgent was called with the correct content
            self.mock_output_agent.assert_called_with('Test Content')

            # Ensure generate_detailed_instruction was called on
            # the OutputAgent instance
            (self.mock_output_agent_instance.generate_detailed_instruction.
             assert_called_once)()

            # Ensure the instruction was printed
            mock_print.assert_called_once_with('Mock Instruction')


if __name__ == '__main__':
    unittest.main()
