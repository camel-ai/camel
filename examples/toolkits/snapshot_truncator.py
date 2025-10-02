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

from typing import Any, Dict, Optional, Set
import re


class SnapshotTruncator:
    """Utility class to truncate browser snapshots in tool results."""
    
    def __init__(
        self, 
        max_snapshot_lines: int = 10,
        truncation_message: str = "... [snapshot truncated for context management]",
        truncate_tools: Optional[Set[str]] = None,
        keep_recent_full: int = 3
    ):
        self.max_snapshot_lines = max_snapshot_lines
        self.truncation_message = truncation_message
        self.keep_recent_full = keep_recent_full  # Number of recent snapshots to keep full
        self.snapshot_history = []  # Track snapshot history
        # If no specific tools specified, truncate all browser tools
        self.truncate_tools = truncate_tools or {
            'browser_open', 'browser_visit_page', 'browser_click',
            'browser_type', 'browser_switch_tab', 'browser_enter',
            'browser_get_som_screenshot', 'browser_back', 'browser_forward',
            'browser_refresh', 'browser_scroll', 'browser_wait'
        }
        
    def should_truncate(self, func_name: str) -> bool:
        """Determine if this snapshot should be truncated based on history."""
        if func_name not in self.truncate_tools:
            return False
            
        # Add this tool call to history
        self.snapshot_history.append(func_name)
        
        # Keep only the snapshots we need to track
        if len(self.snapshot_history) > self.keep_recent_full + 1:
            self.snapshot_history.pop(0)
        
        # Don't truncate if this is one of the recent snapshots
        return len(self.snapshot_history) > self.keep_recent_full + 1
        
    def truncate_snapshot(self, result: Any, should_truncate: bool = True) -> Any:
        """Truncate snapshot in the result while preserving other data."""
        if not should_truncate:
            return result
            
        if isinstance(result, str):
            # Direct string result, check if it contains snapshot
            if "'snapshot':" in result or '"snapshot":' in result:
                # It's likely a string representation of a dict with snapshot
                return self._truncate_string_snapshot(result)
            return result
        elif isinstance(result, dict) and 'snapshot' in result:
            # Dictionary result with snapshot field
            result_copy = result.copy()
            result_copy['snapshot'] = self._truncate_multiline_string(
                result_copy['snapshot']
            )
            return result_copy
        return result
        
    def _truncate_string_snapshot(self, text: str) -> str:
        """Truncate snapshot within a string representation."""
        # Find snapshot field
        pattern = r"('snapshot':|\"snapshot\":)\s*['\"]([^'\"]*)['\"]"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            snapshot_content = match.group(2)
            truncated = self._truncate_multiline_string(snapshot_content)
            # Replace the snapshot content
            return text.replace(snapshot_content, truncated)
        return text
        
    def _truncate_multiline_string(self, text: str) -> str:
        """Truncate a multi-line string to max_snapshot_lines."""
        lines = text.split('\\n') if '\\n' in text else text.split('\n')
        if len(lines) > self.max_snapshot_lines:
            truncated_lines = lines[:self.max_snapshot_lines]
            truncated_lines.append(self.truncation_message)
            delimiter = '\\n' if '\\n' in text else '\n'
            return delimiter.join(truncated_lines)
        return text
        
    def wrap_agent_record_tool_calling(self, agent):
        """Wrap an agent's _record_tool_calling method to add truncation."""
        original_method = agent._record_tool_calling
        truncator = self
        
        def truncated_record_tool_calling(
            func_name: str,
            args: Dict[str, Any],
            result: Any,
            tool_call_id: str,
            mask_output: bool = False,
        ):
            # Check if we should truncate this snapshot
            should_truncate = truncator.should_truncate(func_name)
            
            # Only truncate if it's an old browser tool result
            if func_name in truncator.truncate_tools and should_truncate:
                result = truncator.truncate_snapshot(result, should_truncate=True)
            
            # Call original implementation with potentially truncated result
            return original_method(
                func_name, args, result, tool_call_id, mask_output
            )
        
        # Replace the method
        agent._record_tool_calling = truncated_record_tool_calling
        return agent


def add_snapshot_truncation(agent, max_snapshot_lines: int = 10, keep_recent_full: int = 3):
    """Add snapshot truncation to an existing ChatAgent instance.
    
    Args:
        agent: The ChatAgent instance to enhance
        max_snapshot_lines: Maximum lines to keep in truncated snapshots
        keep_recent_full: Number of recent snapshots to keep complete (default: 3)
    """
    truncator = SnapshotTruncator(max_snapshot_lines, keep_recent_full=keep_recent_full)
    return truncator.wrap_agent_record_tool_calling(agent)