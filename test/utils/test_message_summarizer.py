"""Test cases for the MessageSummarizer class."""

import unittest
from unittest.mock import Mock, patch
from camel.messages import BaseMessage
from camel.types import RoleType, ModelType
from camel.utils.message_summarizer import MessageSummarizer, SummarySchema


class TestMessageSummarizer(unittest.TestCase):
    """Test cases for MessageSummarizer."""

    @patch('camel.agents.ChatAgent')
    def test_summarize(self, mock_chat_agent_class):
        """Test the summarize method."""
        # Mock the ChatAgent response
        mock_response = Mock()
        mock_response.content = {
            "roles": ["USER", "ASSISTANT"],
            "key_entities": ["web application", "React", "Node.js", "task management", "Create React App"],
            "decisions": ["Use React for frontend", "Use Node.js for backend"],
            "task_progress": "Setting up the initial project structure",
            "context": "Planning a web application development project"
        }
        mock_agent = Mock()
        mock_agent.step.return_value = mock_response
        mock_chat_agent_class.return_value = mock_agent

        # Create test messages
        messages = [
            BaseMessage(
                role_name="USER",
                role_type=RoleType.USER,
                meta_dict={},
                content="I want to build a web application for task management."
            ),
            BaseMessage(
                role_name="ASSISTANT",
                role_type=RoleType.ASSISTANT,
                meta_dict={},
                content="I'll help you create a task management web app. We should use React for the frontend and Node.js for the backend."
            ),
            BaseMessage(
                role_name="USER",
                role_type=RoleType.USER,
                meta_dict={},
                content="Great! Let's start with setting up the React project."
            ),
            BaseMessage(
                role_name="ASSISTANT",
                role_type=RoleType.ASSISTANT,
                meta_dict={},
                content="We can use Create React App to set up the project. First, we'll need to install Node.js and npm."
            )
        ]

        # Initialize summarizer
        summarizer = MessageSummarizer(model=ModelType.DEFAULT)

        # Generate summary
        summary = summarizer.summarize(messages)

        # Verify ChatAgent was called correctly
        mock_agent.step.assert_called_once()
        call_args = mock_agent.step.call_args[0]
        self.assertIn("Please analyze these messages", call_args[0])  # Check prompt
        self.assertIn("task management", call_args[0])  # Check message content
        
        # Verify summary structure
        self.assertIsInstance(summary, SummarySchema)
        self.assertIsInstance(summary.roles, list)
        self.assertIsInstance(summary.key_entities, list)
        self.assertIsInstance(summary.decisions, list)
        self.assertIsInstance(summary.task_progress, str)
        self.assertIsInstance(summary.context, str)

        # Verify content
        self.assertIn("USER", summary.roles)
        self.assertIn("ASSISTANT", summary.roles)
        self.assertIn("web application", summary.key_entities)
        self.assertIn("React", summary.key_entities)
        self.assertIn("Node.js", summary.key_entities)
        self.assertIn("task management", summary.key_entities)
        self.assertIn("Create React App", summary.key_entities)
        self.assertIn("setting up", summary.task_progress.lower())
        self.assertGreater(len(summary.decisions), 0)

    @patch('camel.agents.ChatAgent')
    def test_summarize_invalid_response(self, mock_chat_agent_class):
        """Test the summarize method with invalid response."""
        # Mock the ChatAgent with invalid response
        mock_response = Mock()
        mock_response.content = {
            "invalid": "response"
        }
        mock_agent = Mock()
        mock_agent.step.return_value = mock_response
        mock_chat_agent_class.return_value = mock_agent

        # Create test message
        messages = [
            BaseMessage(
                role_name="USER",
                role_type=RoleType.USER,
                meta_dict={},
                content="Test message"
            )
        ]

        # Initialize summarizer
        summarizer = MessageSummarizer(model=ModelType.DEFAULT)

        # Verify that invalid response raises ValueError
        with self.assertRaises(ValueError):
            summarizer.summarize(messages)


if __name__ == '__main__':
    unittest.main()