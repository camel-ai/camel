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

import tempfile
from pathlib import Path

import pytest

from camel.toolkits import SkillToolkit


@pytest.fixture
def temp_skill_dir():
    r"""Create a temporary directory with skills for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create first skill
        skill_dir = Path(temp_dir) / ".camel" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-skill
description: A test skill for unit testing.
---

# Test Skill

This is a test skill body content.
"""
        )

        # Create second skill for multi-skill testing
        skill_dir2 = Path(temp_dir) / ".camel" / "skills" / "another-skill"
        skill_dir2.mkdir(parents=True)
        skill_file2 = skill_dir2 / "SKILL.md"
        skill_file2.write_text(
            """---
name: another-skill
description: Another test skill.
---

# Another Skill

This is another skill body.
"""
        )
        yield temp_dir


@pytest.fixture
def skill_toolkit(temp_skill_dir):
    r"""Create a SkillToolkit instance for testing."""
    return SkillToolkit(working_directory=temp_skill_dir)


def test_initialization():
    r"""Test the initialization of SkillToolkit."""
    toolkit = SkillToolkit()
    assert toolkit.working_directory == Path.cwd().resolve()
    assert toolkit._skills_cache is None


def test_list_skills(skill_toolkit):
    r"""Test listing available skills."""
    skills = skill_toolkit.list_skills()
    assert len(skills) == 2
    names = {s["name"] for s in skills}
    assert "test-skill" in names
    assert "another-skill" in names


def test_load_skill(skill_toolkit):
    r"""Test loading a skill by name."""
    skill_content = skill_toolkit.load_skill("test-skill")
    assert "## Skill: test-skill" in skill_content
    assert "**Base directory**:" in skill_content
    assert "This is a test skill body content." in skill_content


def test_load_skill_not_found(skill_toolkit):
    r"""Test loading a non-existent skill returns error message."""
    result = skill_toolkit.load_skill("non-existent-skill")
    assert "Error:" in result
    assert "not found" in result


def test_load_multiple_skills(skill_toolkit):
    r"""Test loading multiple skills at once."""
    result = skill_toolkit.load_skill(["test-skill", "another-skill"])
    assert "## Skill: test-skill" in result
    assert "## Skill: another-skill" in result
    assert "This is a test skill body content." in result
    assert "This is another skill body." in result
    # Check separator between skills
    assert "---" in result


def test_get_tools(skill_toolkit):
    r"""Test getting the tools from the toolkit."""
    tools = skill_toolkit.get_tools()
    assert len(tools) == 2
    tool_names = [t.func.__name__ for t in tools]
    assert "list_skills" in tool_names
    assert "load_skill" in tool_names


def test_caching(skill_toolkit):
    r"""Test that skills are cached after first access."""
    assert skill_toolkit._skills_cache is None
    skill_toolkit.list_skills()
    assert skill_toolkit._skills_cache is not None
    cached_skills = skill_toolkit._skills_cache
    skill_toolkit.list_skills()
    assert skill_toolkit._skills_cache is cached_skills


def test_clear_cache(skill_toolkit):
    r"""Test that clear_cache resets the skills cache."""
    # Populate the cache
    skill_toolkit.list_skills()
    assert skill_toolkit._skills_cache is not None

    # Clear the cache
    skill_toolkit.clear_cache()
    assert skill_toolkit._skills_cache is None

    # Cache should be repopulated on next access
    skill_toolkit.list_skills()
    assert skill_toolkit._skills_cache is not None
