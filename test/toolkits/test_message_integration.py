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
from typing import List
from unittest.mock import Mock, patch

from camel.toolkits import BaseToolkit, FunctionTool
from camel.toolkits.message_integration import ToolkitMessageIntegration


class MockToolkit(BaseToolkit):
    r"""Mock toolkit for testing."""

    def search_web(self, query: str) -> List[str]:
        r"""Search the web for information.

        Args:
            query: Search query string

        Returns:
            List of search results
        """
        return [f"Result 1 for {query}", f"Result 2 for {query}"]

    def analyze_data(self, data: str, format: str = "json") -> dict:
        r"""Analyze data in specified format.

        Args:
            data: Data to analyze
            format: Output format

        Returns:
            Analysis results
        """
        return {"status": "analyzed", "data": data, "format": format}

    def get_tools(self) -> List[FunctionTool]:
        return [FunctionTool(self.search_web), FunctionTool(self.analyze_data)]


class TestToolkitMessageIntegration(unittest.TestCase):
    r"""Test cases for ToolkitMessageIntegration."""

    def setUp(self):
        r"""Set up test fixtures."""
        self.toolkit = MockToolkit()
        self.message_integration = ToolkitMessageIntegration()

    def test_default_message_handler(self):
        r"""Test the built-in send_message_to_user function."""
        with patch('builtins.print') as mock_print:
            result = self.message_integration.send_message_to_user(
                "Test Title", "Test Description", "test.pdf"
            )

            # Check print was called
            mock_print.assert_called()

            # Check return value
            self.assertIn("Message successfully sent", result)
            self.assertIn("Test Title", result)

    def test_register_all_tools(self):
        r"""Test adding messaging to all tools in a toolkit."""
        enhanced_toolkit = self.message_integration.register_toolkits(
            self.toolkit
        )

        tools = enhanced_toolkit.get_tools()
        self.assertEqual(len(tools), 2)

        # Check that tools have message parameters
        for tool in tools:
            schema = tool.get_openai_tool_schema()
            params = schema['function']['parameters']['properties']
            self.assertIn('message_title', params)
            self.assertIn('message_description', params)
            self.assertIn('message_attachment', params)

    def test_register_specific_tools(self):
        r"""Test adding messaging to specific tools only using
        register_functions."""
        # Use register_functions to enhance only one method
        enhanced_tools = self.message_integration.register_functions(
            [self.toolkit.search_web]
        )

        # Should get one enhanced tool
        self.assertEqual(len(enhanced_tools), 1)
        search_tool = enhanced_tools[0]

        # Check search_web has message parameters
        search_schema = search_tool.get_openai_tool_schema()
        self.assertIn(
            'message_title',
            search_schema['function']['parameters']['properties'],
        )

        # Check the original toolkit's analyze_data doesn't have message
        # parameters
        original_tools = self.toolkit.get_tools()
        analyze_tool = next(
            t for t in original_tools if t.func.__name__ == 'analyze_data'
        )
        analyze_schema = analyze_tool.get_openai_tool_schema()
        self.assertNotIn(
            'message_title',
            analyze_schema['function']['parameters']['properties'],
        )

    def test_enhanced_tool_execution_with_message(self):
        r"""Test that enhanced tools send messages when parameters are
        provided."""
        # Patch at the instance level by replacing the message_handler
        mock_send = Mock(return_value="Message sent")
        self.message_integration.message_handler = mock_send

        enhanced_toolkit = self.message_integration.register_toolkits(
            self.toolkit
        )

        tools = enhanced_toolkit.get_tools()
        search_tool = next(t for t in tools if t.func.__name__ == 'search_web')

        # Call with message parameters
        result = search_tool.func(
            query="AI research",
            message_title="Starting Search",
            message_description="Searching for AI research papers",
        )

        # Check message was sent
        mock_send.assert_called_once_with(
            "Starting Search", "Searching for AI research papers", ''
        )

        # Check original function still works
        self.assertEqual(len(result), 2)
        self.assertIn("AI research", result[0])

    def test_enhanced_tool_execution_without_message(self):
        r"""Test enhanced tools work normally without message parameters."""
        # Patch at the instance level by replacing the message_handler
        mock_send = Mock(return_value="Message sent")
        self.message_integration.message_handler = mock_send

        enhanced_toolkit = self.message_integration.register_toolkits(
            self.toolkit
        )

        tools = enhanced_toolkit.get_tools()
        search_tool = next(t for t in tools if t.func.__name__ == 'search_web')

        # Call without message parameters
        result = search_tool.func(query="AI research")

        # Check no message was sent
        mock_send.assert_not_called()

        # Check original function still works
        self.assertEqual(len(result), 2)

    def test_register_functions_with_callables(self):
        r"""Test adding messaging to a list of callable functions."""

        def process_text(text: str) -> str:
            r"""Process text.

            Args:
                text: Input text

            Returns:
                Processed text
            """
            return text.upper()

        def calculate_sum(a: int, b: int) -> int:
            r"""Calculate sum.

            Args:
                a: First number
                b: Second number

            Returns:
                Sum of a and b
            """
            return a + b

        enhanced_tools = self.message_integration.register_functions(
            [process_text, calculate_sum], function_names=['process_text']
        )

        self.assertEqual(len(enhanced_tools), 2)

        # Check process_text has message parameters
        process_tool = enhanced_tools[0]
        process_schema = process_tool.get_openai_tool_schema()
        self.assertIn(
            'message_title',
            process_schema['function']['parameters']['properties'],
        )

        # Check calculate_sum doesn't have message parameters
        calc_tool = enhanced_tools[1]
        calc_schema = calc_tool.get_openai_tool_schema()
        self.assertNotIn(
            'message_title',
            calc_schema['function']['parameters']['properties'],
        )

    def test_custom_message_handler(self):
        r"""Test using a custom message handler."""
        mock_handler = Mock(return_value="Custom message sent")
        mock_handler.__name__ = 'custom_notify'
        mock_handler.__doc__ = """Send custom notification.
        
        Args:
            level: Notification level
            action: Action being performed
            details: Additional details
        """

        custom_integration = ToolkitMessageIntegration(
            message_handler=mock_handler,
            extract_params_callback=lambda kwargs: (
                kwargs.pop('level', 'info'),
                kwargs.pop('action', 'executing'),
                kwargs.pop('details', ''),
            ),
        )

        enhanced_toolkit = custom_integration.register_toolkits(self.toolkit)

        tools = enhanced_toolkit.get_tools()
        search_tool = next(t for t in tools if t.func.__name__ == 'search_web')

        # Call with custom parameters
        search_tool.func(
            query="test",
            level="warning",
            action="searching",
            details="for test data",
        )

        # Check custom handler was called
        mock_handler.assert_called_once_with(
            "warning", "searching", "for test data"
        )

    def test_docstring_enhancement(self):
        r"""Test that docstrings are properly enhanced."""

        def simple_func():
            r"""Simple function without parameters."""
            pass

        def func_with_args(x: int, y: int) -> int:
            r"""Function with arguments.

            Args:
                x: First number
                y: Second number

            Returns:
                Sum of x and y
            """
            return x + y

        enhanced_tools = self.message_integration.register_functions(
            [simple_func, func_with_args]
        )

        # Check simple_func docstring
        simple_enhanced = enhanced_tools[0]
        self.assertIn("Args:", simple_enhanced.func.__doc__)
        self.assertIn("message_title", simple_enhanced.func.__doc__)

        # Check func_with_args docstring
        args_enhanced = enhanced_tools[1]
        self.assertIn("x: First number", args_enhanced.func.__doc__)
        self.assertIn("message_title", args_enhanced.func.__doc__)

    def test_get_message_tool(self):
        r"""Test getting the message tool as a standalone FunctionTool."""
        message_tool = self.message_integration.get_message_tool()

        self.assertIsInstance(message_tool, FunctionTool)
        self.assertEqual(message_tool.func.__name__, 'send_message_to_user')

        # Test it can be called
        with patch('builtins.print'):
            result = message_tool.func("Title", "Description")
            self.assertIn("Message successfully sent", result)


if __name__ == "__main__":
    unittest.main()
