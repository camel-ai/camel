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

"""Unit tests for file reporting in workforce prompts."""

import pytest

from camel.societies.workforce.prompts import (
    PROCESS_TASK_PROMPT,
    ROLEPLAY_PROCESS_TASK_PROMPT,
)


class TestPromptFileReporting:
    """Test file reporting instructions in workforce prompts."""

    def test_process_task_prompt_has_file_reporting(self):
        """Test that PROCESS_TASK_PROMPT includes file reporting instructions."""
        prompt_str = str(PROCESS_TASK_PROMPT)
        
        # Check for file reporting section
        assert "File Reporting" in prompt_str, \
            "PROCESS_TASK_PROMPT should contain 'File Reporting' section"
        
        # Check for key instructions
        assert "generated, modified, or accessed any files" in prompt_str, \
            "Prompt should instruct to report generated/modified/accessed files"
        
        # Check for examples
        assert "Example valid response WITH files" in prompt_str, \
            "Prompt should include example with files"
        assert "Example valid response WITHOUT files" in prompt_str, \
            "Prompt should include example without files"

    def test_process_task_prompt_mentions_toolkits(self):
        """Test that prompt mentions various toolkits."""
        prompt_str = str(PROCESS_TASK_PROMPT)
        
        # Should mention FileToolkit
        assert "FileToolkit" in prompt_str, \
            "Prompt should mention FileToolkit"
        
        # Should mention TerminalToolkit or other tools
        assert "TerminalToolkit" in prompt_str or "any tools" in prompt_str, \
            "Prompt should mention that it applies to various tools"

    def test_process_task_prompt_file_report_format(self):
        """Test that prompt specifies correct file report format."""
        prompt_str = str(PROCESS_TASK_PROMPT)
        
        # Should ask for file paths
        assert "paths" in prompt_str.lower() or "file" in prompt_str.lower(), \
            "Prompt should ask for file information"
        
        # Should ask for description
        assert "description" in prompt_str.lower(), \
            "Prompt should ask for file description"

    def test_roleplay_process_task_prompt_has_file_reporting(self):
        """Test that ROLEPLAY_PROCESS_TASK_PROMPT includes file reporting."""
        prompt_str = str(ROLEPLAY_PROCESS_TASK_PROMPT)
        
        # Check for file reporting section
        assert "File Reporting" in prompt_str, \
            "ROLEPLAY_PROCESS_TASK_PROMPT should contain 'File Reporting' section"
        
        # Check for key instructions
        assert "generated, modified, or accessed any files" in prompt_str, \
            "Prompt should instruct to report generated/modified/accessed files"
        
        # Check for examples
        assert "Example valid response WITH files" in prompt_str, \
            "Prompt should include example with files"

    def test_roleplay_prompt_mentions_file_operations(self):
        """Test that roleplay prompt mentions file operations."""
        prompt_str = str(ROLEPLAY_PROCESS_TASK_PROMPT)
        
        # Should mention file operations
        assert "files" in prompt_str.lower(), \
            "Roleplay prompt should mention files"
        
        # Should include roleplay-specific example
        assert "report.md" in prompt_str or "roleplay" in prompt_str.lower(), \
            "Roleplay prompt should have roleplay-specific example"

    def test_process_task_prompt_preserves_json_format(self):
        """Test that prompt still requires JSON response format."""
        prompt_str = str(PROCESS_TASK_PROMPT)
        
        # Should still require JSON
        assert "JSON object" in prompt_str or "json" in prompt_str.lower(), \
            "Prompt should still require JSON format"
        
        # Should have content and failed fields
        assert "'content'" in prompt_str or '"content"' in prompt_str, \
            "Prompt should specify 'content' field"
        assert "'failed'" in prompt_str or '"failed"' in prompt_str, \
            "Prompt should specify 'failed' field"

    def test_roleplay_prompt_preserves_json_format(self):
        """Test that roleplay prompt still requires JSON response format."""
        prompt_str = str(ROLEPLAY_PROCESS_TASK_PROMPT)
        
        # Should still require JSON
        assert "JSON object" in prompt_str or "json" in prompt_str.lower(), \
            "Roleplay prompt should still require JSON format"
        
        # Should have content and failed fields
        assert "'content'" in prompt_str or '"content"' in prompt_str, \
            "Prompt should specify 'content' field"
        assert "'failed'" in prompt_str or '"failed"' in prompt_str, \
            "Prompt should specify 'failed' field"

    def test_process_task_prompt_has_proper_examples(self):
        """Test that PROCESS_TASK_PROMPT has proper example format."""
        prompt_str = str(PROCESS_TASK_PROMPT)
        
        # Should have proper JSON example with files
        assert '"content":' in prompt_str, \
            "Prompt should show content field in examples"
        assert '"failed": false' in prompt_str or '"failed":' in prompt_str, \
            "Prompt should show failed field in examples"
        
        # File example should be realistic
        assert "README.md" in prompt_str, \
            "Prompt should have realistic file example"

    def test_both_prompts_consistent(self):
        """Test that both prompts have consistent file reporting."""
        process_prompt = str(PROCESS_TASK_PROMPT)
        roleplay_prompt = str(ROLEPLAY_PROCESS_TASK_PROMPT)
        
        # Both should have file reporting
        assert "File Reporting" in process_prompt, \
            "PROCESS_TASK_PROMPT should have file reporting"
        assert "File Reporting" in roleplay_prompt, \
            "ROLEPLAY_PROCESS_TASK_PROMPT should have file reporting"
        
        # Both should mention file operations
        assert "files" in process_prompt.lower(), \
            "PROCESS_TASK_PROMPT should mention files"
        assert "files" in roleplay_prompt.lower(), \
            "ROLEPLAY_PROCESS_TASK_PROMPT should mention files"
