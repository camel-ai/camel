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

"""
Tests for MCPCodeAgent
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.agents import MCPCodeAgent
from camel.toolkits.mcp_toolkit import MCPToolkit
from camel.utils.mcp_code_executor import MCPCodeExecutor
from camel.utils.mcp_code_generator import MCPCodeGenerator
from camel.utils.mcp_skills import Skill, SkillManager


class TestMCPCodeGenerator:
    def test_init(self):
        """Test MCPCodeGenerator initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MCPCodeGenerator(tmpdir)
            assert generator.workspace_dir.exists()
            assert generator.servers_dir.exists()

    def test_sanitize_name(self):
        """Test name sanitization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MCPCodeGenerator(tmpdir)
            assert generator._sanitize_name("my-tool") == "my_tool"
            assert generator._sanitize_name("123tool") == "tool_123tool"
            assert generator._sanitize_name("valid_name") == "valid_name"

    def test_schema_type_to_python(self):
        """Test schema type conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MCPCodeGenerator(tmpdir)

            assert (
                generator._schema_type_to_python({"type": "string"}) == "str"
            )
            assert (
                generator._schema_type_to_python({"type": "integer"}) == "int"
            )
            assert (
                generator._schema_type_to_python({"type": "array"})
                == "List[Any]"
            )


class TestSkillManager:
    def test_init(self):
        """Test SkillManager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)
            assert manager.skills_dir.exists()
            assert isinstance(manager.skills, dict)

    def test_save_and_load_skill(self):
        """Test saving and loading skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)

            skill = Skill(
                name="test_skill",
                description="Test skill",
                code="def test(): return 42",
                tags=["test"],
            )

            # Save skill
            assert manager.save_skill(skill)

            # Load skill
            loaded = manager.load_skill("test_skill")
            assert loaded is not None
            assert loaded.name == "test_skill"
            assert loaded.usage_count == 1  # Incremented on load

    def test_search_skills(self):
        """Test skill search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)

            skill1 = Skill(
                name="file_reader",
                description="Read files",
                code="def read(): pass",
                tags=["file", "io"],
            )
            skill2 = Skill(
                name="csv_processor",
                description="Process CSV",
                code="def process(): pass",
                tags=["csv", "data"],
            )

            manager.save_skill(skill1)
            manager.save_skill(skill2)

            # Search by query
            results = manager.search_skills(query="file")
            assert len(results) == 1
            assert results[0].name == "file_reader"

            # Search by tags
            results = manager.search_skills(tags=["csv"])
            assert len(results) == 1
            assert results[0].name == "csv_processor"

    def test_delete_skill(self):
        """Test skill deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(tmpdir)

            skill = Skill(
                name="temp_skill", description="Temporary", code="pass"
            )

            manager.save_skill(skill)
            assert "temp_skill" in manager.list_skills()

            manager.delete_skill("temp_skill")
            assert "temp_skill" not in manager.list_skills()


class TestMCPCodeExecutor:
    @pytest.mark.asyncio
    async def test_init(self):
        """Test MCPCodeExecutor initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock toolkit
            mock_toolkit = MagicMock(spec=MCPToolkit)
            mock_toolkit.is_connected = False

            executor = MCPCodeExecutor(mock_toolkit, tmpdir)
            assert executor.workspace_dir.exists()
            assert executor.mcp_toolkit == mock_toolkit

    @pytest.mark.asyncio
    async def test_get_instance(self):
        """Test singleton instance access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_toolkit = MagicMock(spec=MCPToolkit)
            executor = MCPCodeExecutor(mock_toolkit, tmpdir)

            # Should return the instance
            assert MCPCodeExecutor.get_instance() == executor


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="API key not available",
)
class TestMCPCodeAgentIntegration:
    """Integration tests for MCPCodeAgent (requires API keys)."""

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test agent creation and connection."""
        config = {
            "mcpServers": {
                "test_server": {
                    "command": "echo",
                    "args": ["test"],
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(MCPToolkit, "connect", new_callable=AsyncMock):
                with patch.object(
                    MCPToolkit, "disconnect", new_callable=AsyncMock
                ):
                    agent = await MCPCodeAgent.create(
                        config_dict=config,
                        workspace_dir=tmpdir,
                    )

                    assert agent is not None
                    assert agent.workspace_dir == tmpdir

                    await agent.disconnect()

    @pytest.mark.asyncio
    async def test_skill_management(self):
        """Test skill management in agent."""
        config = {
            "mcpServers": {
                "test_server": {
                    "command": "echo",
                    "args": ["test"],
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(MCPToolkit, "connect", new_callable=AsyncMock):
                with patch.object(
                    MCPToolkit, "disconnect", new_callable=AsyncMock
                ):
                    agent = await MCPCodeAgent.create(
                        config_dict=config,
                        workspace_dir=tmpdir,
                        enable_skills=True,
                    )

                    # Save a skill
                    success = agent.save_skill(
                        name="test_skill",
                        description="Test skill",
                        code="def test(): return 42",
                        tags=["test"],
                    )

                    assert success
                    assert "test_skill" in agent.list_skills()

                    # Get skill code
                    code = agent.get_skill("test_skill")
                    assert code is not None
                    assert "def test()" in code

                    await agent.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
