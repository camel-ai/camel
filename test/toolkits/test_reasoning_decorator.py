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

"""Tests for the reasoning decorator in the browser toolkit."""

import inspect
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits.hybrid_browser_toolkit_py.reasoning_decorator import (
    ReasoningContextManager,
    enable_reasoning_for_toolkit,
    with_reasoning,
)


class MockToolkit:
    """Mock toolkit for testing the reasoning decorator."""

    def __init__(self):
        self._agent = None

    async def browser_click(self, *, ref: str) -> Dict[str, Any]:
        """Mock click action."""
        return {"result": f"Clicked {ref}", "snapshot": "mock snapshot"}

    async def browser_type(self, *, ref: str, text: str) -> Dict[str, Any]:
        """Mock type action."""
        return {"result": f"Typed '{text}' into {ref}", "snapshot": "mock"}


class TestWithReasoningDecorator:
    """Tests for the @with_reasoning decorator."""

    def test_adds_reasoning_parameter(self):
        """Test that the decorator adds a required reasoning parameter."""

        @with_reasoning
        async def sample_action(self, *, ref: str) -> Dict[str, Any]:
            return {"ref": ref}

        sig = inspect.signature(sample_action)
        params = list(sig.parameters.keys())

        assert 'reasoning' in params
        # Reasoning should be required (no default value)
        assert sig.parameters['reasoning'].default is inspect.Parameter.empty
        assert sig.parameters['reasoning'].annotation is str

    def test_preserves_original_parameters(self):
        """Test that original parameters are preserved."""

        @with_reasoning
        async def sample_action(
            self, *, ref: str, text: str = ""
        ) -> Dict[str, Any]:
            return {"ref": ref, "text": text}

        sig = inspect.signature(sample_action)
        params = list(sig.parameters.keys())

        assert 'self' in params
        assert 'ref' in params
        assert 'text' in params
        assert 'reasoning' in params

    def test_raises_error_for_non_async_function(self):
        """Test that decorator raises TypeError for non-async functions."""

        with pytest.raises(TypeError, match="can only be applied to async"):

            @with_reasoning
            def sync_function(self, ref: str) -> Dict[str, Any]:
                return {"ref": ref}

    @pytest.mark.asyncio
    async def test_function_raises_error_without_reasoning(self):
        """Test that decorated function raises error without reasoning."""

        @with_reasoning
        async def sample_action(self, *, ref: str) -> Dict[str, Any]:
            return {"ref": ref, "success": True}

        mock_self = MockToolkit()

        with pytest.raises(TypeError, match="missing required keyword"):
            await sample_action(mock_self, ref="e1")

    @pytest.mark.asyncio
    async def test_function_raises_error_with_empty_reasoning(self):
        """Test that decorated function raises error with empty reasoning."""

        @with_reasoning
        async def sample_action(self, *, ref: str) -> Dict[str, Any]:
            return {"ref": ref, "success": True}

        mock_self = MockToolkit()

        with pytest.raises(ValueError, match="non-empty reasoning string"):
            await sample_action(mock_self, ref="e1", reasoning="")

        with pytest.raises(ValueError, match="non-empty reasoning string"):
            await sample_action(mock_self, ref="e1", reasoning="   ")

    @pytest.mark.asyncio
    async def test_function_works_with_reasoning(self):
        """Test that decorated function works when reasoning is provided."""

        @with_reasoning
        async def sample_action(self, *, ref: str) -> Dict[str, Any]:
            return {"ref": ref, "success": True}

        mock_self = MockToolkit()

        # Patch the _process_reasoning function
        with patch(
            'camel.toolkits.hybrid_browser_toolkit_py.'
            'reasoning_decorator._process_reasoning'
        ) as mock_process:
            result = await sample_action(
                mock_self, ref="e1", reasoning="Clicking submit button"
            )

            # Verify _process_reasoning was called
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            assert call_args[0] is mock_self
            assert call_args[1] == "sample_action"
            assert call_args[2] == "Clicking submit button"

        assert result["ref"] == "e1"
        assert result["success"] is True

    def test_docstring_is_enhanced(self):
        """Test that the decorator enhances the docstring."""

        @with_reasoning
        async def sample_action(self, *, ref: str) -> Dict[str, Any]:
            """Click an element.

            Args:
                ref (str): The element reference.

            Returns:
                Dict: The result.
            """
            return {"ref": ref}

        assert 'reasoning' in sample_action.__doc__
        assert 'chain of thought' in sample_action.__doc__

    def test_marks_function_as_enhanced(self):
        """Test that the decorator marks the function as enhanced."""

        @with_reasoning
        async def sample_action(self, *, ref: str) -> Dict[str, Any]:
            return {"ref": ref}

        assert getattr(sample_action, '__reasoning_enhanced__', False) is True


class TestEnableReasoningForToolkit:
    """Tests for the enable_reasoning_for_toolkit function."""

    def test_enhances_specified_tools(self):
        """Test that specified tools are enhanced with reasoning."""
        toolkit = MockToolkit()

        # Verify tools don't have reasoning initially
        original_sig = inspect.signature(toolkit.browser_click)
        assert 'reasoning' not in original_sig.parameters

        # Enable reasoning
        enable_reasoning_for_toolkit(toolkit, tool_names=["browser_click"])

        # Verify browser_click has reasoning now
        enhanced_sig = inspect.signature(toolkit.browser_click)
        assert 'reasoning' in enhanced_sig.parameters

        # Verify browser_type was not enhanced (not in tool_names)
        type_sig = inspect.signature(toolkit.browser_type)
        assert 'reasoning' not in type_sig.parameters

    def test_enhances_all_default_tools_when_no_names_specified(self):
        """Test that default tools are enhanced when no names specified."""
        toolkit = MockToolkit()

        enable_reasoning_for_toolkit(toolkit)

        # Both tools should have reasoning
        click_sig = inspect.signature(toolkit.browser_click)
        type_sig = inspect.signature(toolkit.browser_type)

        assert 'reasoning' in click_sig.parameters
        assert 'reasoning' in type_sig.parameters

    def test_marks_toolkit_as_enhanced(self):
        """Test that the toolkit is marked as having reasoning enabled."""
        toolkit = MockToolkit()

        assert not hasattr(toolkit, '_reasoning_enabled')

        enable_reasoning_for_toolkit(toolkit)

        assert toolkit._reasoning_enabled is True

    def test_does_not_double_enhance(self):
        """Test that tools are not enhanced twice."""
        toolkit = MockToolkit()

        # Enhance once
        enable_reasoning_for_toolkit(toolkit)
        sig1 = inspect.signature(toolkit.browser_click)

        # Enhance again
        enable_reasoning_for_toolkit(toolkit)
        sig2 = inspect.signature(toolkit.browser_click)

        # Signatures should be the same
        assert list(sig1.parameters.keys()) == list(sig2.parameters.keys())


class TestReasoningContextManager:
    """Tests for the ReasoningContextManager class."""

    def test_context_manager_entry_exit(self):
        """Test context manager enter and exit."""
        with ReasoningContextManager() as ctx:
            assert ctx is not None
            assert isinstance(ctx.get_all_reasoning(), list)
            assert len(ctx.get_all_reasoning()) == 0

    def test_add_reasoning(self):
        """Test adding reasoning entries."""
        ctx = ReasoningContextManager()

        ctx.add_reasoning("browser_click", "Clicking submit button")
        ctx.add_reasoning("browser_type", "Entering username")

        reasoning_log = ctx.get_all_reasoning()

        assert len(reasoning_log) == 2
        assert reasoning_log[0]["action"] == "browser_click"
        assert reasoning_log[0]["reasoning"] == "Clicking submit button"
        assert "timestamp" in reasoning_log[0]
        assert reasoning_log[1]["action"] == "browser_type"

    def test_clear_reasoning(self):
        """Test clearing reasoning entries."""
        ctx = ReasoningContextManager()

        ctx.add_reasoning("browser_click", "Test reasoning")
        assert len(ctx.get_all_reasoning()) == 1

        ctx.clear()
        assert len(ctx.get_all_reasoning()) == 0

    def test_get_all_reasoning_returns_copy(self):
        """Test that get_all_reasoning returns a copy, not the original."""
        ctx = ReasoningContextManager()

        ctx.add_reasoning("browser_click", "Test")
        log1 = ctx.get_all_reasoning()
        log2 = ctx.get_all_reasoning()

        assert log1 is not log2
        assert log1 == log2


class TestReasoningInjection:
    """Tests for reasoning injection into agent context."""

    @pytest.mark.asyncio
    async def test_reasoning_injected_into_agent_memory(self):
        """Test that reasoning is injected into agent memory."""

        # Create a mock agent with memory
        mock_agent = MagicMock()
        mock_agent.memory = MagicMock()
        mock_agent.agent_id = "test_agent"

        toolkit = MockToolkit()
        toolkit._agent = mock_agent

        enable_reasoning_for_toolkit(toolkit)

        # Call with required reasoning
        # Note: "submit" triggers wait suggestion, so we expect 2 write_record
        # calls - one for reasoning, one for wait suggestion
        await toolkit.browser_click(
            ref="e1", reasoning="Clicking the submit button"
        )

        # Verify memory.write_record was called (at least once for reasoning,
        # possibly twice with wait suggestion)
        assert mock_agent.memory.write_record.call_count >= 1

        # Get the first record (reasoning) that was written
        first_call_args = mock_agent.memory.write_record.call_args_list[0][0]
        record = first_call_args[0]

        # Verify the record contains the reasoning
        assert "Clicking the submit button" in record.message.content
        assert "browser_click" in record.message.content

    @pytest.mark.asyncio
    async def test_wait_suggestion_injected_for_submit_actions(self):
        """Test that wait suggestion is injected when reasoning suggests
        page updates."""

        # Create a mock agent with memory
        mock_agent = MagicMock()
        mock_agent.memory = MagicMock()
        mock_agent.agent_id = "test_agent"

        toolkit = MockToolkit()
        toolkit._agent = mock_agent

        enable_reasoning_for_toolkit(toolkit)

        # Call with reasoning that triggers wait suggestion
        result = await toolkit.browser_click(
            ref="e1", reasoning="Clicking submit to login"
        )

        # Should be called twice: once for reasoning, once for wait suggestion
        assert mock_agent.memory.write_record.call_count == 2

        # Check the wait suggestion was added to result
        assert "wait_suggestion" in result
        assert "WAIT SUGGESTION" in result["wait_suggestion"]

        # Get the second record (wait suggestion)
        second_call_args = mock_agent.memory.write_record.call_args_list[1][0]
        wait_record = second_call_args[0]

        # Verify it contains the wait suggestion
        assert "WAIT SUGGESTION" in wait_record.message.content

    @pytest.mark.asyncio
    async def test_no_wait_suggestion_for_simple_reasoning(self):
        """Test that no wait suggestion is added for simple actions."""

        # Create a mock agent with memory
        mock_agent = MagicMock()
        mock_agent.memory = MagicMock()
        mock_agent.agent_id = "test_agent"

        toolkit = MockToolkit()
        toolkit._agent = mock_agent

        enable_reasoning_for_toolkit(toolkit)

        # Call with reasoning that doesn't trigger wait suggestion
        result = await toolkit.browser_click(
            ref="e1", reasoning="Clicking the menu item to expand it"
        )

        # Should only be called once (just reasoning, no wait suggestion)
        assert mock_agent.memory.write_record.call_count == 1

        # No wait suggestion in result
        assert "wait_suggestion" not in result

    @pytest.mark.asyncio
    async def test_no_injection_when_no_agent(self):
        """Test that no error occurs when no agent is registered."""
        toolkit = MockToolkit()
        toolkit._agent = None

        enable_reasoning_for_toolkit(toolkit)

        # Reasoning is required but injection is optional when no agent
        result = await toolkit.browser_click(
            ref="e1", reasoning="Clicking element to test without agent"
        )

        assert result["result"] == "Clicked e1"

    @pytest.mark.asyncio
    async def test_reasoning_required_after_enabling(self):
        """Test that reasoning becomes required after enabling."""
        toolkit = MockToolkit()
        enable_reasoning_for_toolkit(toolkit)

        # Should raise error when reasoning is not provided
        with pytest.raises(TypeError, match="missing required keyword"):
            await toolkit.browser_click(ref="e1")


class TestToolkitIntegration:
    """Integration tests with the actual HybridBrowserToolkit."""

    def test_enable_reasoning_parameter_exists(self):
        """Test that enable_reasoning parameter exists in toolkit init."""
        from camel.toolkits.hybrid_browser_toolkit_py import (
            HybridBrowserToolkit,
        )

        sig = inspect.signature(HybridBrowserToolkit.__init__)
        assert 'enable_reasoning' in sig.parameters

    @pytest.mark.asyncio
    async def test_toolkit_with_reasoning_enabled(self):
        """Test creating toolkit with reasoning enabled."""
        from camel.toolkits.hybrid_browser_toolkit_py import (
            HybridBrowserToolkit,
        )

        toolkit = HybridBrowserToolkit(enable_reasoning=True)

        # Verify reasoning is enabled
        assert toolkit._enable_reasoning is True
        assert hasattr(toolkit, '_reasoning_enabled')
        assert toolkit._reasoning_enabled is True

        # Verify browser_click has reasoning parameter
        sig = inspect.signature(toolkit.browser_click)
        assert 'reasoning' in sig.parameters

        # Clean up
        try:
            await toolkit.browser_close()
        except Exception:
            pass  # Browser may not be open
