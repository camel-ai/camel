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
This example demonstrates how to use the to_skill() method to convert
CAMEL toolkits into Claude Agent Skills format.

Claude Agent Skills are self-contained skill packages that can be loaded
by Claude Code to provide specialized capabilities.
"""

import json
import shutil
import subprocess
import sys
import tempfile

from camel.toolkits import MathToolkit

# Create a temporary directory for the skill output
output_dir = tempfile.mkdtemp(prefix="camel_skill_example_")
print(f"Generating skill to: {output_dir}\n")

# Example 1: Basic usage with MathToolkit
# Creates a skill with auto-generated name and description
math_toolkit = MathToolkit()
skill_path = math_toolkit.to_skill(output_dir)

print(f"Generated skill at: {skill_path}")
print("\nGenerated files:")
for file_path in sorted(skill_path.rglob("*")):
    if file_path.is_file():
        rel_path = file_path.relative_to(skill_path)
        print(f"  - {rel_path}")

# Display SKILL.md content
skill_md = skill_path / "SKILL.md"
print(f"\n{'=' * 60}")
print("SKILL.md content:")
print("=" * 60)
print(skill_md.read_text())

# Example 2: Custom name and description
custom_skill_path = math_toolkit.to_skill(
    path=output_dir,
    name="calculator",
    description="A simple calculator for basic arithmetic operations.",
    instructions="Use this skill for any mathematical calculations.",
)
print(f"\n{'=' * 60}")
print(f"Custom skill generated at: {custom_skill_path}")
print("=" * 60)

# Example 3: Test running a generated script
print(f"\n{'=' * 60}")
print("Testing generated script execution:")
print("=" * 60)

script_path = skill_path / "scripts" / "math_add.py"
params = json.dumps({"a": 5, "b": 3})
result = subprocess.run(
    [sys.executable, str(script_path), params],
    capture_output=True,
    text=True,
)

print(f"Running: python math_add.py '{params}'")
print(f"Output: {result.stdout}")

if result.returncode == 0:
    output = json.loads(result.stdout)
    print(f"Result: {output.get('result')}")

# Clean up
print(f"\n{'=' * 60}")
print(f"Cleaning up temporary directory: {output_dir}")
shutil.rmtree(output_dir)
print("Done!")

"""
Expected Output:
===============================================================================
Generating skill to: /tmp/camel_skill_example_xxxxx

Generated skill at: /tmp/camel_skill_example_xxxxx/math
Generated files:
  - SKILL.md
  - requirements.txt
  - scripts/math_add.py
  - scripts/math_divide.py
  - scripts/math_multiply.py
  - scripts/math_round.py
  - scripts/math_subtract.py

============================================================
SKILL.md content:
============================================================
---
name: math
description: A class representing a toolkit for mathematical operations...
---

# Math

## Overview
...

============================================================
Testing generated script execution:
============================================================
Running: python math_add.py '{"a": 5, "b": 3}'
Output: {"result": 8}
Result: 8

============================================================
Cleaning up temporary directory: /tmp/camel_skill_example_xxxxx
Done!
===============================================================================
"""
