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
"""Snapshot truncation functionality for browser toolkit.

This module provides utilities to truncate browser snapshots in the agent's
context history while keeping the current snapshot intact for the LLM to use.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import asyncio

from camel.messages import BaseMessage, FunctionCallingMessage
from camel.agents import ChatAgent


class SnapshotTruncator:
    """Handles truncation of browser snapshots in agent history."""
    
    # Pattern to identify browser tool methods that return snapshots
    BROWSER_SNAPSHOT_TOOLS = {
        'browser_open',
        'browser_visit_page',
        'browser_back',
        'browser_forward',
        'browser_refresh',
        'browser_click',
        'browser_type',
        'browser_enter',
        'browser_press_key',
        'browser_get_page_snapshot',
        'browser_get_som_screenshot',
        'browser_wait',
    }
    
    # Default truncation settings
    DEFAULT_MAX_LINES = 10
    DEFAULT_TRUNCATION_MESSAGE = "\n... [snapshot truncated to {lines} lines for context history] ..."
    
    def __init__(
        self,
        max_snapshot_lines: int = DEFAULT_MAX_LINES,
        truncation_message: str = DEFAULT_TRUNCATION_MESSAGE,
        enabled_for_tools: Optional[List[str]] = None,
    ):
        """Initialize the snapshot truncator.
        
        Args:
            max_snapshot_lines: Maximum number of lines to keep in truncated snapshots
            truncation_message: Message template to insert when truncating
            enabled_for_tools: List of tool names to enable truncation for. 
                             If None, uses BROWSER_SNAPSHOT_TOOLS
        """
        self.max_snapshot_lines = max_snapshot_lines
        self.truncation_message = truncation_message
        self.enabled_for_tools = (
            set(enabled_for_tools) if enabled_for_tools 
            else self.BROWSER_SNAPSHOT_TOOLS
        )
    
    def truncate_snapshot(self, content: str, max_lines: Optional[int] = None) -> str:
        """Truncate a snapshot to the specified number of lines.
        
        Args:
            content: The snapshot content to truncate
            max_lines: Maximum lines to keep (uses default if None)
            
        Returns:
            Truncated snapshot content
        """
        if not content or not isinstance(content, str):
            return content
            
        lines = content.split('\n')
        max_lines = max_lines or self.max_snapshot_lines
        
        if len(lines) <= max_lines:
            return content
            
        # Keep first max_lines lines
        truncated_lines = lines[:max_lines]
        truncated_lines.append(
            self.truncation_message.format(lines=max_lines)
        )
        
        return '\n'.join(truncated_lines)
    
    def is_snapshot_result(self, result: Any) -> bool:
        """Check if a result contains a browser snapshot.
        
        Args:
            result: The tool execution result
            
        Returns:
            True if the result contains a snapshot
        """
        if isinstance(result, str):
            # Check if it looks like a snapshot (has ref= pattern)
            return bool(re.search(r'\[ref=\d+\]', result))
        elif isinstance(result, dict):
            # Check if it has a 'snapshot' key
            return 'snapshot' in result
        return False
    
    def truncate_result(self, result: Any, tool_name: str) -> Any:
        """Truncate snapshot in a tool result if applicable.
        
        Args:
            result: The tool execution result
            tool_name: Name of the tool that produced the result
            
        Returns:
            Result with truncated snapshot if applicable
        """
        if tool_name not in self.enabled_for_tools:
            return result
            
        if isinstance(result, str) and self.is_snapshot_result(result):
            return self.truncate_snapshot(result)
        elif isinstance(result, dict) and 'snapshot' in result:
            # Make a copy to avoid modifying the original
            truncated_result = result.copy()
            truncated_result['snapshot'] = self.truncate_snapshot(
                result['snapshot']
            )
            return truncated_result
            
        return result


class TruncatingChatAgent(ChatAgent):
    """ChatAgent wrapper that truncates browser snapshots in historical context.
    
    This wrapper extends ChatAgent to automatically truncate browser snapshots
    in the conversation history while keeping the current snapshot intact for
    the LLM to process.
    """
    
    def __init__(self, *args, snapshot_truncator: Optional[SnapshotTruncator] = None, **kwargs):
        """Initialize the truncating chat agent.
        
        Args:
            *args: Arguments passed to ChatAgent
            snapshot_truncator: Custom snapshot truncator instance. 
                              If None, uses default settings
            **kwargs: Keyword arguments passed to ChatAgent
        """
        super().__init__(*args, **kwargs)
        self.snapshot_truncator = snapshot_truncator or SnapshotTruncator()
        
        # Store the original _record_tool_calling method
        self._original_record_tool_calling = self._record_tool_calling
        
        # Override the method
        self._record_tool_calling = self._truncating_record_tool_calling
    
    def _truncating_record_tool_calling(
        self,
        func_name: str,
        args: Dict[str, Any],
        result: Any,
        tool_call_id: str,
        mask_output: bool = False,
    ):
        """Override to truncate snapshots before recording in memory.
        
        This method intercepts tool results and truncates any browser snapshots
        before they are recorded in the agent's memory, ensuring that historical
        context doesn't get bloated with full snapshots.
        """
        # Truncate the result if it contains a snapshot
        truncated_result = self.snapshot_truncator.truncate_result(
            result, func_name
        )
        
        # Call the original method with the truncated result
        return self._original_record_tool_calling(
            func_name, args, truncated_result, tool_call_id, mask_output
        )


def create_snapshot_aware_agent(
    *args,
    max_snapshot_lines: int = 10,
    truncation_message: Optional[str] = None,
    enabled_for_tools: Optional[List[str]] = None,
    **kwargs
) -> TruncatingChatAgent:
    """Create a ChatAgent that automatically truncates browser snapshots in history.
    
    This is a convenience function that creates a TruncatingChatAgent with
    customizable snapshot truncation settings.
    
    Args:
        *args: Arguments passed to ChatAgent
        max_snapshot_lines: Maximum number of lines to keep in truncated snapshots
        truncation_message: Custom message to show when truncating
        enabled_for_tools: List of tool names to enable truncation for
        **kwargs: Keyword arguments passed to ChatAgent
        
    Returns:
        TruncatingChatAgent instance
    """
    truncator = SnapshotTruncator(
        max_snapshot_lines=max_snapshot_lines,
        truncation_message=truncation_message or SnapshotTruncator.DEFAULT_TRUNCATION_MESSAGE,
        enabled_for_tools=enabled_for_tools,
    )
    
    return TruncatingChatAgent(
        *args,
        snapshot_truncator=truncator,
        **kwargs
    )


# Decorator approach for existing agents
def truncate_browser_snapshots(
    agent: ChatAgent,
    max_snapshot_lines: int = 10,
    truncation_message: Optional[str] = None,
    enabled_for_tools: Optional[List[str]] = None,
) -> ChatAgent:
    """Decorator that adds snapshot truncation to an existing ChatAgent.
    
    This function modifies an existing ChatAgent instance to truncate browser
    snapshots in its conversation history.
    
    Args:
        agent: The ChatAgent to modify
        max_snapshot_lines: Maximum number of lines to keep in truncated snapshots
        truncation_message: Custom message to show when truncating
        enabled_for_tools: List of tool names to enable truncation for
        
    Returns:
        The modified agent (same instance)
    """
    truncator = SnapshotTruncator(
        max_snapshot_lines=max_snapshot_lines,
        truncation_message=truncation_message or SnapshotTruncator.DEFAULT_TRUNCATION_MESSAGE,
        enabled_for_tools=enabled_for_tools,
    )
    
    # Store the original method
    original_record_tool_calling = agent._record_tool_calling
    
    def _truncating_record_tool_calling(
        func_name: str,
        args: Dict[str, Any],
        result: Any,
        tool_call_id: str,
        mask_output: bool = False,
    ):
        # Truncate the result if it contains a snapshot
        truncated_result = truncator.truncate_result(result, func_name)
        
        # Call the original method with the truncated result
        return original_record_tool_calling(
            func_name, args, truncated_result, tool_call_id, mask_output
        )
    
    # Replace the method
    agent._record_tool_calling = _truncating_record_tool_calling
    
    return agent