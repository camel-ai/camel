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

from camel.toolkits import MathToolkit


class TestToSkill:
    def test_to_skill_default_name(self):
        """Test skill generation with default name from class."""
        toolkit = MathToolkit()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = toolkit.to_skill(output_dir=tmpdir)

            assert skill_path.exists()
            assert skill_path.name == "math.md"

    def test_to_skill_custom_name(self):
        """Test skill generation with custom name."""
        toolkit = MathToolkit()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = toolkit.to_skill(output_dir=tmpdir, name="calculator")

            assert skill_path.exists()
            assert skill_path.name == "calculator.md"

    def test_to_skill_custom_description(self):
        """Test skill generation with custom description."""
        toolkit = MathToolkit()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = toolkit.to_skill(
                output_dir=tmpdir,
                description="Custom math description",
            )

            content = skill_path.read_text()
            assert "Custom math description" in content

    def test_to_skill_custom_content(self):
        """Test skill generation with fully custom content."""
        toolkit = MathToolkit()
        custom = "# My Custom Skill\n\nCustom content here."

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = toolkit.to_skill(output_dir=tmpdir, content=custom)

            content = skill_path.read_text()
            assert content == custom

    def test_to_skill_contains_tools(self):
        """Test that generated skill contains tool documentation."""
        toolkit = MathToolkit()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = toolkit.to_skill(output_dir=tmpdir)

            content = skill_path.read_text()
            assert "## Available Tools" in content
            assert "math_add" in content
            assert "math_subtract" in content
            assert "**Parameters:**" in content
            assert "**Returns:**" in content


class TestStatePersistence:
    def test_save_and_load_state(self):
        """Test basic state save and load."""
        toolkit = MathToolkit()
        test_state = {"counter": 42, "history": ["op1", "op2"]}

        with tempfile.TemporaryDirectory() as tmpdir:
            toolkit.save_state(test_state, session_id="test", state_dir=tmpdir)
            loaded = toolkit.load_state(session_id="test", state_dir=tmpdir)

            assert loaded == test_state

    def test_load_nonexistent_state(self):
        """Test loading state that doesn't exist."""
        toolkit = MathToolkit()
        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = toolkit.load_state(
                session_id="nonexistent", state_dir=tmpdir
            )

            assert loaded is None

    def test_state_isolation_by_session(self):
        """Test that different sessions have isolated state."""
        toolkit = MathToolkit()
        state1 = {"value": 1}
        state2 = {"value": 2}

        with tempfile.TemporaryDirectory() as tmpdir:
            toolkit.save_state(state1, session_id="session1", state_dir=tmpdir)
            toolkit.save_state(state2, session_id="session2", state_dir=tmpdir)

            loaded1 = toolkit.load_state(
                session_id="session1", state_dir=tmpdir
            )
            loaded2 = toolkit.load_state(
                session_id="session2", state_dir=tmpdir
            )

            assert loaded1 == state1
            assert loaded2 == state2

    def test_state_overwrite(self):
        """Test that saving state overwrites previous state."""
        toolkit = MathToolkit()

        with tempfile.TemporaryDirectory() as tmpdir:
            toolkit.save_state({"v": 1}, session_id="test", state_dir=tmpdir)
            toolkit.save_state({"v": 2}, session_id="test", state_dir=tmpdir)

            loaded = toolkit.load_state(session_id="test", state_dir=tmpdir)
            assert loaded == {"v": 2}

    def test_save_state_returns_path(self):
        """Test that save_state returns the state file path."""
        toolkit = MathToolkit()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = toolkit.save_state(
                {"k": "v"}, session_id="test", state_dir=tmpdir
            )

            assert isinstance(path, Path)
            assert path.exists()
            assert "MathToolkit_test.json" in str(path)
