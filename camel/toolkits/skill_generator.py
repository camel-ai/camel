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

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type

from docstring_parser import parse as parse_docstring

import camel

if TYPE_CHECKING:
    from camel.toolkits.base import BaseToolkit
    from camel.toolkits.function_tool import FunctionTool


class SkillGenerator:
    r"""Generates Claude Agent Skills from CAMEL toolkits.

    This class handles the conversion of CAMEL toolkit instances to the
    Claude Agent Skills format, generating SKILL.md and executable Python
    scripts.

    Args:
        toolkit_instance (BaseToolkit): The toolkit instance to convert.
    """

    MAX_NAME_LENGTH = 64
    MAX_DESCRIPTION_LENGTH = 1024

    def __init__(self, toolkit_instance: "BaseToolkit"):
        self.toolkit = toolkit_instance
        self.toolkit_class: Type["BaseToolkit"] = toolkit_instance.__class__
        self._tools: Optional[List["FunctionTool"]] = None

    @property
    def tools(self) -> List["FunctionTool"]:
        r"""Get FunctionTool objects from toolkit instance."""
        if self._tools is None:
            self._tools = self.toolkit.get_tools()
        return self._tools

    def generate(
        self,
        path: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> Path:
        r"""Generate the skill directory structure.

        Args:
            path (str): Base directory for the skill.
            name (Optional[str]): Skill name override.
            description (Optional[str]): Skill description override.
            instructions (Optional[str]): Custom instructions.

        Returns:
            Path: Path to the created skill directory.
        """
        # Resolve skill name
        skill_name = self._resolve_name(name)

        # Create skill directory
        skill_dir = Path(path) / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Get initialization info
        init_info = self._get_init_info()

        # Generate SKILL.md
        skill_md_content = self._generate_skill_md(
            name=skill_name,
            description=description,
            instructions=instructions,
            init_info=init_info,
        )
        (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

        # Generate scripts
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        self._generate_scripts(scripts_dir, init_info)

        # Generate requirements.txt
        self._generate_requirements(skill_dir)

        return skill_dir

    def _resolve_name(self, name: Optional[str]) -> str:
        r"""Resolve and validate the skill name."""
        if name is None:
            # Derive from class name: TerminalToolkit -> terminal
            class_name = self.toolkit_class.__name__
            name = re.sub(r'([A-Z])', r'-\1', class_name).lower().lstrip('-')
            name = name.replace('-toolkit', '').replace('toolkit', '')
            name = name.strip('-') or 'skill'

        # Validate and fix name format (lowercase, numbers, hyphens only)
        name = re.sub(r'[^a-z0-9-]', '-', name.lower())
        name = re.sub(r'-+', '-', name).strip('-')
        if not name:
            name = 'skill'

        # Enforce length limit
        if len(name) > self.MAX_NAME_LENGTH:
            name = name[: self.MAX_NAME_LENGTH].rstrip('-')

        return name

    def _find_real_init(self) -> Optional[Callable]:
        r"""Find the real __init__ method, bypassing decorators.

        Some toolkits are decorated with @MCPServer() which wraps __init__.
        This method traverses the MRO to find the actual __init__ with
        proper signature, or parses source code if necessary.
        """
        # First, try the class's own __init__
        init_method = self.toolkit_class.__init__

        # Check if it has a valid signature (not wrapped)
        try:
            sig = inspect.signature(init_method)
            params = list(sig.parameters.keys())
            # If the signature looks like a wrapper (instance, *args, **kwargs)
            # we need to find the real one
            if params == ['instance', 'args', 'kwargs'] or params == [
                'self',
                'args',
                'kwargs',
            ]:
                # Try to get the unwrapped function
                unwrapped = inspect.unwrap(init_method)
                if unwrapped is not init_method:
                    try:
                        unwrapped_sig = inspect.signature(unwrapped)
                        unwrapped_params = list(
                            unwrapped_sig.parameters.keys()
                        )
                        if unwrapped_params not in [
                            ['instance', 'args', 'kwargs'],
                            ['self', 'args', 'kwargs'],
                        ]:
                            return unwrapped
                    except (ValueError, TypeError):
                        pass

                # Try to parse source code to get the real signature
                real_init = self._get_init_from_source()
                if real_init is not None:
                    return real_init

                # Look in the MRO for the real __init__
                for cls in self.toolkit_class.__mro__[1:]:
                    if cls is object:
                        continue
                    if '__init__' in cls.__dict__:
                        parent_init = cls.__dict__['__init__']
                        try:
                            parent_sig = inspect.signature(parent_init)
                            parent_params = list(parent_sig.parameters.keys())
                            if parent_params not in [
                                ['instance', 'args', 'kwargs'],
                                ['self', 'args', 'kwargs'],
                            ]:
                                return parent_init
                        except (ValueError, TypeError):
                            continue

                # Fallback to BaseToolkit's __init__ if nothing found
                from camel.toolkits.base import BaseToolkit

                return BaseToolkit.__init__
            return init_method
        except (ValueError, TypeError):
            return None

    def _get_init_from_source(self) -> Optional[Callable]:
        r"""Parse source code to create a callable with proper signature.

        When __init__ is wrapped by decorators, we can parse the source
        to extract parameter information.
        """
        import ast

        try:
            source_file = inspect.getsourcefile(self.toolkit_class)
            if source_file is None:
                return None

            with open(source_file) as f:
                tree = ast.parse(f.read())

            # Find the class definition
            class_name = self.toolkit_class.__name__
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Find __init__ method
                    for item in node.body:
                        if (
                            isinstance(item, ast.FunctionDef)
                            and item.name == '__init__'
                        ):
                            # Create a dummy function with the same signature
                            return self._create_dummy_init_from_ast(item)
            return None
        except Exception:
            return None

    def _create_dummy_init_from_ast(
        self, func_node: Any
    ) -> Optional[Callable]:
        r"""Create a dummy function from AST node to extract signature."""
        import ast

        # Build parameter info
        params = []
        defaults = func_node.args.defaults
        args = func_node.args.args

        # Calculate offset for defaults (defaults align with the end of args)
        num_defaults = len(defaults)
        num_args = len(args)
        default_offset = num_args - num_defaults

        for i, arg in enumerate(args):
            if arg.arg == 'self':
                continue

            # Get type annotation
            annotation: Any = inspect.Parameter.empty
            if arg.annotation:
                try:
                    annotation = ast.unparse(arg.annotation)
                except Exception:
                    pass

            # Get default value
            default: Any = inspect.Parameter.empty
            default_index = i - default_offset
            if default_index >= 0 and default_index < len(defaults):
                try:
                    # Try to evaluate the default value
                    default_node = defaults[default_index]
                    default = ast.literal_eval(ast.unparse(default_node))
                except Exception:
                    # Can't evaluate, mark as having a default
                    default = None

            param = inspect.Parameter(
                name=arg.arg,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=annotation,
            )
            params.append(param)

        # Create a dummy function with this signature
        sig = inspect.Signature(params)

        def dummy_init(self, **kwargs):
            pass

        dummy_init.__signature__ = sig  # type: ignore[attr-defined]

        # Extract docstring from the original class's __init__ or class doc
        if func_node.body:
            first_stmt = func_node.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Constant
            ):
                docstring_value = first_stmt.value.value
                if isinstance(docstring_value, str):
                    dummy_init.__doc__ = docstring_value
        if not dummy_init.__doc__:
            dummy_init.__doc__ = self.toolkit_class.__doc__

        return dummy_init

    def _resolve_description(self, description: Optional[str]) -> str:
        r"""Resolve and validate the skill description."""
        if description is None:
            # Extract from toolkit class docstring
            doc = self.toolkit_class.__doc__ or ""
            # Get first paragraph
            first_para = doc.strip().split('\n\n')[0].strip()
            # Clean up reST formatting
            description = re.sub(r':obj:`([^`]+)`', r'\1', first_para)
            description = re.sub(r'\s+', ' ', description)

        if not description:
            description = f"Tools from {self.toolkit_class.__name__}"

        # Add tool trigger hints
        tool_names = [t.get_function_name() for t in self.tools]
        if tool_names:
            keywords = ', '.join(tool_names[:3])
            hint = f" Use when: {keywords}."
            if len(description) + len(hint) <= self.MAX_DESCRIPTION_LENGTH:
                description += hint

        # Enforce length limit
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            max_len = self.MAX_DESCRIPTION_LENGTH - 3
            description = description[:max_len] + "..."

        return description

    def _get_init_info(self) -> Dict[str, Any]:
        r"""Get initialization parameter information from the toolkit."""
        info: Dict[str, Any] = {
            'class_name': self.toolkit_class.__name__,
            'module': self.toolkit_class.__module__,
            'params': [],
            'current_values': {},
        }

        # Find the real __init__ method (may be wrapped by decorators)
        init_method = self._find_real_init()
        if init_method is None:
            return info

        sig = inspect.signature(init_method)
        docstring = parse_docstring(init_method.__doc__ or "")

        # Build param descriptions from docstring
        param_docs = {p.arg_name: p.description for p in docstring.params}

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Get current value from instance
            current_value = getattr(self.toolkit, param_name, None)

            param_info = {
                'name': param_name,
                'type': self._format_type_annotation(param.annotation),
                'default': param.default
                if param.default != inspect.Parameter.empty
                else None,
                'has_default': param.default != inspect.Parameter.empty,
                'description': param_docs.get(param_name, ''),
                'current_value': current_value,
            }
            info['params'].append(param_info)

            # Store serializable current values
            if current_value is not None:
                try:
                    # Test if value is JSON serializable
                    json.dumps(current_value)
                    info['current_values'][param_name] = current_value
                except (TypeError, ValueError):
                    # Not serializable, store string representation
                    info['current_values'][param_name] = str(current_value)

        return info

    def _format_type_annotation(self, annotation: Any) -> str:
        r"""Format a type annotation to a readable string."""
        if annotation == inspect.Parameter.empty:
            return 'Any'

        if hasattr(annotation, '__origin__'):
            # Handle generic types like Optional[str], List[int]
            origin = getattr(annotation, '__origin__', None)
            args = getattr(annotation, '__args__', ())

            if origin is type(None):
                return 'None'

            origin_name = getattr(origin, '__name__', str(origin))

            if args:
                args_str = ', '.join(
                    self._format_type_annotation(arg) for arg in args
                )
                return f"{origin_name}[{args_str}]"
            return origin_name

        if hasattr(annotation, '__name__'):
            return annotation.__name__

        return str(annotation).replace('typing.', '')

    def _generate_skill_md(
        self,
        name: str,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        init_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        r"""Generate the SKILL.md content."""
        description = self._resolve_description(description)

        # Build YAML frontmatter
        frontmatter = f"""---
name: {name}
description: {description}
---"""

        # Build instructions
        if instructions is None:
            instructions = self._generate_instructions(init_info)

        # Combine all sections
        title = name.replace('-', ' ').title()
        content = f"""{frontmatter}

# {title}

{instructions}
"""
        return content

    def _generate_instructions(
        self,
        init_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        r"""Auto-generate instructions from tool docstrings."""
        sections = []

        # Overview section
        toolkit_doc = self.toolkit_class.__doc__ or ""
        if toolkit_doc:
            overview = toolkit_doc.strip()
            # Clean up reST formatting
            overview = re.sub(r':obj:`([^`]+)`', r'`\1`', overview)
            sections.append(f"## Overview\n\n{overview}")

        # Requirements section
        requirements_section = self._generate_requirements_section()
        sections.append(requirements_section)

        # Initialization section (for toolkits with init params)
        if init_info and init_info['params']:
            init_section = self._generate_init_section(init_info)
            sections.append(init_section)

        # Available tools section
        tools_section = self._generate_tools_section()
        sections.append(tools_section)

        # Usage section
        usage_section = self._generate_usage_section(init_info)
        sections.append(usage_section)

        return '\n\n'.join(sections)

    def _generate_requirements_section(self) -> str:
        r"""Generate requirements section."""
        version = camel.__version__
        lines = ["## Requirements\n"]
        lines.append(
            f"This skill requires CAMEL-AI version `{version}` "
            "or compatible.\n"
        )
        lines.append("```bash")
        lines.append(f"pip install camel-ai=={version}")
        lines.append("```")
        return '\n'.join(lines)

    def _generate_init_section(self, init_info: Dict[str, Any]) -> str:
        r"""Generate initialization parameters documentation."""
        lines = ["## Initialization\n"]
        lines.append(
            f"The `{init_info['class_name']}` accepts the following "
            "initialization parameters:\n"
        )

        lines.append("| Parameter | Type | Default | Description |")
        lines.append("|-----------|------|---------|-------------|")

        for param in init_info['params']:
            default_str = (
                f"`{param['default']!r}`"
                if param['has_default']
                else "Required"
            )
            type_str = param['type']
            desc = param['description']
            # Truncate long descriptions
            if len(desc) > 60:
                desc = desc[:57] + "..."
            # Escape pipe characters in markdown table
            desc = desc.replace('|', '\\|')
            lines.append(
                f"| `{param['name']}` | {type_str} | {default_str} | {desc} |"
            )

        # Show current instance values
        if init_info['current_values']:
            lines.append("\n**Current instance configuration:**\n")
            lines.append("```json")
            lines.append(json.dumps(init_info['current_values'], indent=2))
            lines.append("```")

        return '\n'.join(lines)

    def _generate_tools_section(self) -> str:
        r"""Generate available tools documentation."""
        lines = ["## Available Tools\n"]

        for tool in self.tools:
            tool_name = tool.get_function_name()
            tool_desc = tool.get_function_description()
            params = tool.parameters

            lines.append(f"### `{tool_name}`\n")
            lines.append(f"{tool_desc}\n")

            if params:
                lines.append("**Parameters:**\n")
                for param_name, param_info in params.items():
                    param_type = param_info.get('type', 'any')
                    if isinstance(param_type, list):
                        param_type = ' | '.join(str(t) for t in param_type)
                    param_desc = param_info.get('description', '')
                    lines.append(
                        f"- `{param_name}` ({param_type}): {param_desc}"
                    )
                lines.append("")

        return '\n'.join(lines)

    def _generate_usage_section(
        self, init_info: Optional[Dict[str, Any]] = None
    ) -> str:
        r"""Generate usage section with script examples."""
        lines = ["## Usage\n"]

        lines.append(
            "Execute toolkit methods using the provided Python scripts. "
            "Each script handles toolkit initialization and state management "
            "automatically.\n"
        )

        lines.append("### Running a Tool\n")
        lines.append("```bash")

        # Get first tool as example
        if self.tools:
            tool = self.tools[0]
            tool_name = tool.get_function_name()
            example_params = self._build_example_params(tool)
            params_json = json.dumps(example_params)
            lines.append(f"python scripts/{tool_name}.py '{params_json}'")

        lines.append("```\n")

        # Add note about state management
        lines.append("### State Management\n")
        lines.append(
            "State is automatically saved to `state.json` in the skill "
            "directory after each tool execution and loaded on startup."
        )

        return '\n'.join(lines)

    def _build_example_params(self, tool: "FunctionTool") -> Dict[str, Any]:
        r"""Build example parameters for a tool."""
        example_params: Dict[str, Any] = {}
        for param_name, param_info in tool.parameters.items():
            param_type = param_info.get('type', 'string')
            if isinstance(param_type, list):
                param_type = param_type[0] if param_type else 'string'

            if param_type == 'number':
                example_params[param_name] = 1.0
            elif param_type == 'integer':
                example_params[param_name] = 1
            elif param_type == 'boolean':
                example_params[param_name] = True
            elif param_type == 'array':
                example_params[param_name] = []
            elif param_type == 'object':
                example_params[param_name] = {}
            else:
                example_params[param_name] = "example"

        return example_params

    def _generate_scripts(
        self,
        scripts_dir: Path,
        init_info: Dict[str, Any],
    ) -> None:
        r"""Generate Python scripts for each tool."""
        for tool in self.tools:
            script_content = self._generate_tool_script(tool, init_info)
            script_name = f"{tool.get_function_name()}.py"
            script_path = scripts_dir / script_name
            script_path.write_text(script_content, encoding="utf-8")
            # Make executable on Unix systems
            script_path.chmod(script_path.stat().st_mode | 0o111)

    def _generate_tool_script(
        self,
        tool: "FunctionTool",
        init_info: Dict[str, Any],
    ) -> str:
        r"""Generate a standalone script for a single tool."""
        func_name = tool.get_function_name()
        func_desc = tool.get_function_description()
        class_name = init_info['class_name']
        module_name = init_info['module']

        # Build init params as Python code
        init_params_code = self._build_init_params_code(init_info)

        script = f'''#!/usr/bin/env python3
"""
{func_name}: {func_desc}

Auto-generated script for Claude Agent Skills.
Requires: camel-ai=={camel.__version__}
"""

import json
import sys
from pathlib import Path

# State file path (relative to script location)
STATE_FILE = Path(__file__).parent.parent / "state.json"

# Default initialization parameters
INIT_PARAMS = {init_params_code}


def load_state() -> dict:
    """Load toolkit state from file if exists."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {{}}


def save_state(state: dict) -> None:
    """Save toolkit state to file."""
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except IOError as e:
        print(f"Warning: Failed to save state: {{e}}", file=sys.stderr)


def main():
    """Execute the {func_name} tool."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print(json.dumps({{"error": "Usage: {func_name}.py '<json_params>'"}}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({{"error": f"Invalid JSON: {{e}}"}}))
        sys.exit(1)

    try:
        from {module_name} import {class_name}

        # Load previous state
        state = load_state()

        # Merge saved init params with defaults
        init_params = {{**INIT_PARAMS}}
        if "init_params" in state:
            init_params.update(state["init_params"])

        # Initialize toolkit
        toolkit = {class_name}(**init_params)

        # Restore toolkit state if available
        if "toolkit_state" in state:
            for key, value in state["toolkit_state"].items():
                if hasattr(toolkit, key):
                    try:
                        setattr(toolkit, key, value)
                    except AttributeError:
                        pass  # Read-only attribute

        # Call the method
        method = getattr(toolkit, "{func_name}")
        result = method(**params)

        # Save state after execution
        new_state = {{
            "init_params": init_params,
            "toolkit_state": {{}},
        }}
        # Save serializable attributes
        for attr_name in dir(toolkit):
            if attr_name.startswith("_"):
                continue
            try:
                attr_value = getattr(toolkit, attr_name)
                if callable(attr_value):
                    continue
                # Test if serializable
                json.dumps(attr_value)
                new_state["toolkit_state"][attr_name] = attr_value
            except (TypeError, ValueError):
                pass
        save_state(new_state)

        # Output result
        if result is None:
            print(json.dumps({{"result": None, "success": True}}))
        else:
            try:
                print(json.dumps({{"result": result}}))
            except (TypeError, ValueError):
                print(json.dumps({{"result": str(result)}}))

    except Exception as e:
        import traceback
        print(json.dumps({{
            "error": str(e),
            "traceback": traceback.format_exc()
        }}))
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        return script

    def _build_init_params_code(self, init_info: Dict[str, Any]) -> str:
        r"""Build initialization parameters as Python dict literal."""
        if not init_info['current_values']:
            return "{}"

        lines = ["{"]
        for key, value in init_info['current_values'].items():
            lines.append(f"    {key!r}: {value!r},")
        lines.append("}")
        return '\n'.join(lines)

    def _generate_requirements(self, skill_dir: Path) -> None:
        r"""Generate requirements.txt for the skill."""
        version = camel.__version__
        requirements = [
            "# Auto-generated requirements for this skill",
            f"# CAMEL-AI version: {version}",
            f"camel-ai=={version}",
        ]

        (skill_dir / "requirements.txt").write_text(
            '\n'.join(requirements), encoding="utf-8"
        )
