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
Basic SkillToolkit Example

This example shows basic usage of SkillToolkit.
For a more complete example with multiple skills, see:
    examples/toolkits/skill_toolkit_example/

Skills are SKILL.md files discovered from:
    - .camel/skills/ (repo scope)
    - ~/.camel/skills/ (user scope)
"""

from camel.toolkits import SkillToolkit

# Create toolkit - discovers skills from standard locations
skill_toolkit = SkillToolkit()

# List available skills
skills = skill_toolkit.list_skills()
print(f"Found {len(skills)} skills:")
for skill in skills:
    print(f"  - {skill['name']}: {skill['description']}")

# Get tools for use with ChatAgent
tools = skill_toolkit.get_tools()
print(f"\nTools available: {[t.func.__name__ for t in tools]}")

# Load a specific skill (if available)
if skills:
    skill_name = skills[0]["name"]
    content = skill_toolkit.get_skill(skill_name)
    print(f"\nLoaded skill '{skill_name}':")
    print(content[:200] + "...")
