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

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import camel
from camel.toolkits import MathToolkit, SkillGenerator


class TestSkillGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.toolkit = MathToolkit()
        self.generator = SkillGenerator(self.toolkit)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test SkillGenerator initialization."""
        self.assertEqual(self.generator.toolkit, self.toolkit)
        self.assertEqual(self.generator.toolkit_class, MathToolkit)

    def test_tools_property(self):
        """Test that tools are properly retrieved."""
        tools = self.generator.tools
        self.assertIsInstance(tools, list)
        self.assertTrue(len(tools) > 0)

        tool_names = [t.get_function_name() for t in tools]
        self.assertIn("math_add", tool_names)
        self.assertIn("math_subtract", tool_names)

    def test_resolve_name_default(self):
        """Test default name resolution from class name."""
        name = self.generator._resolve_name(None)
        self.assertEqual(name, "math")

    def test_resolve_name_custom(self):
        """Test custom name validation."""
        name = self.generator._resolve_name("My Custom Skill!")
        self.assertEqual(name, "my-custom-skill")

    def test_resolve_name_length_limit(self):
        """Test name length enforcement."""
        long_name = "a" * 100
        name = self.generator._resolve_name(long_name)
        self.assertLessEqual(len(name), SkillGenerator.MAX_NAME_LENGTH)

    def test_resolve_description_default(self):
        """Test default description from docstring."""
        description = self.generator._resolve_description(None)
        self.assertIn("mathematical", description.lower())
        self.assertIn("Use when:", description)

    def test_resolve_description_custom(self):
        """Test custom description."""
        custom = "My custom description."
        description = self.generator._resolve_description(custom)
        self.assertIn("My custom description", description)

    def test_get_init_info(self):
        """Test initialization info extraction."""
        info = self.generator._get_init_info()
        self.assertEqual(info["class_name"], "MathToolkit")
        self.assertEqual(info["module"], "camel.toolkits.math_toolkit")
        self.assertIn("params", info)
        self.assertIn("current_values", info)

    def test_generate_creates_directory_structure(self):
        """Test that generate creates proper directory structure."""
        skill_path = self.generator.generate(self.temp_dir)

        self.assertTrue(skill_path.exists())
        self.assertTrue((skill_path / "SKILL.md").exists())
        self.assertTrue((skill_path / "scripts").exists())
        self.assertTrue((skill_path / "requirements.txt").exists())

    def test_generate_skill_md_content(self):
        """Test SKILL.md content format."""
        skill_path = self.generator.generate(self.temp_dir)
        skill_md = (skill_path / "SKILL.md").read_text()

        # Check YAML frontmatter
        self.assertIn("---", skill_md)
        self.assertIn("name:", skill_md)
        self.assertIn("description:", skill_md)

        # Check sections
        self.assertIn("## Overview", skill_md)
        self.assertIn("## Requirements", skill_md)
        self.assertIn("## Available Tools", skill_md)
        self.assertIn("## Usage", skill_md)

    def test_generate_scripts(self):
        """Test that scripts are generated for each tool."""
        skill_path = self.generator.generate(self.temp_dir)
        scripts_dir = skill_path / "scripts"

        tool_names = [t.get_function_name() for t in self.generator.tools]
        for tool_name in tool_names:
            script_path = scripts_dir / f"{tool_name}.py"
            self.assertTrue(
                script_path.exists(), f"Missing script: {tool_name}.py"
            )

    def test_generate_requirements(self):
        """Test requirements.txt content."""
        skill_path = self.generator.generate(self.temp_dir)
        requirements = (skill_path / "requirements.txt").read_text()

        self.assertIn("camel-ai==", requirements)
        self.assertIn(camel.__version__, requirements)

    def test_script_execution(self):
        """Test that generated scripts are executable."""
        skill_path = self.generator.generate(self.temp_dir)
        script_path = skill_path / "scripts" / "math_add.py"

        params = json.dumps({"a": 10, "b": 5})
        result = subprocess.run(
            [sys.executable, str(script_path), params],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["result"], 15)

    def test_script_state_management(self):
        """Test that scripts save and load state."""
        skill_path = self.generator.generate(self.temp_dir)
        state_file = skill_path / "state.json"

        # Run a script to create state
        script_path = skill_path / "scripts" / "math_add.py"
        params = json.dumps({"a": 1, "b": 2})
        subprocess.run(
            [sys.executable, str(script_path), params],
            capture_output=True,
            text=True,
        )

        # Check state file was created
        self.assertTrue(state_file.exists())
        state = json.loads(state_file.read_text())
        self.assertIn("init_params", state)
        self.assertIn("toolkit_state", state)

    def test_custom_name(self):
        """Test generating skill with custom name."""
        skill_path = self.generator.generate(self.temp_dir, name="calculator")
        self.assertEqual(skill_path.name, "calculator")

        skill_md = (skill_path / "SKILL.md").read_text()
        self.assertIn("name: calculator", skill_md)

    def test_custom_description(self):
        """Test generating skill with custom description."""
        custom_desc = "A custom calculator for testing."
        skill_path = self.generator.generate(
            self.temp_dir, description=custom_desc
        )

        skill_md = (skill_path / "SKILL.md").read_text()
        self.assertIn(custom_desc, skill_md)

    def test_custom_instructions(self):
        """Test generating skill with custom instructions."""
        custom_instructions = "These are custom instructions for the skill."
        skill_path = self.generator.generate(
            self.temp_dir, instructions=custom_instructions
        )

        skill_md = (skill_path / "SKILL.md").read_text()
        self.assertIn(custom_instructions, skill_md)


class TestBaseToolkitToSkill(unittest.TestCase):
    """Test the to_skill method on BaseToolkit."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.toolkit = MathToolkit()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_to_skill_method_exists(self):
        """Test that to_skill method exists on toolkit."""
        self.assertTrue(hasattr(self.toolkit, "to_skill"))
        self.assertTrue(callable(self.toolkit.to_skill))

    def test_to_skill_returns_path(self):
        """Test that to_skill returns a Path object."""
        result = self.toolkit.to_skill(self.temp_dir)
        self.assertIsInstance(result, Path)
        self.assertTrue(result.exists())

    def test_to_skill_creates_skill(self):
        """Test that to_skill creates a valid skill."""
        skill_path = self.toolkit.to_skill(self.temp_dir)

        self.assertTrue((skill_path / "SKILL.md").exists())
        self.assertTrue((skill_path / "scripts").exists())
        self.assertTrue((skill_path / "requirements.txt").exists())

    def test_to_skill_with_custom_params(self):
        """Test to_skill with custom parameters."""
        skill_path = self.toolkit.to_skill(
            self.temp_dir,
            name="my-math",
            description="Custom math toolkit.",
        )

        self.assertEqual(skill_path.name, "my-math")


class TestSkillGeneratorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_special_characters_in_name(self):
        """Test handling special characters in skill name."""
        toolkit = MathToolkit()
        generator = SkillGenerator(toolkit)

        name = generator._resolve_name("Test@#$%Skill!")
        self.assertNotIn("@", name)
        self.assertNotIn("#", name)
        self.assertNotIn("$", name)
        self.assertNotIn("%", name)
        self.assertNotIn("!", name)

    def test_empty_description(self):
        """Test handling empty description."""
        toolkit = MathToolkit()
        generator = SkillGenerator(toolkit)

        description = generator._resolve_description("")
        self.assertTrue(len(description) > 0)

    def test_format_type_annotation(self):
        """Test type annotation formatting."""
        toolkit = MathToolkit()
        generator = SkillGenerator(toolkit)

        from typing import List, Optional

        self.assertEqual(generator._format_type_annotation(str), "str")
        self.assertEqual(generator._format_type_annotation(int), "int")
        # Optional[str] expands to Union[str, None]
        optional_result = generator._format_type_annotation(Optional[str])
        self.assertTrue(
            "Union" in optional_result or "Optional" in optional_result
        )
        list_result = generator._format_type_annotation(List[int])
        self.assertTrue("list" in list_result.lower())


if __name__ == "__main__":
    unittest.main()
