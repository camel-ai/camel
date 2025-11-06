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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ruff: noqa: E501

#!/usr/bin/env python3
import argparse
import ast
import glob
import importlib
import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

# Module name to display name mapping
MODULE_NAME_DISPLAY = {
    "agents": "Agents",
    "configs": "Configs",
    "datagen": "Data Generation",
    "datasets": "Datasets",
    "data_collector": "Data Collector",
    "embeddings": "Embeddings",
    "environments": "Environments",
    "interpreters": "Interpreters",
    "loaders": "Loaders",
    "memories": "Memory",
    "messages": "Messages",
    "models": "Models",
    "prompts": "Prompts",
    "responses": "Responses",
    "retrievers": "Retrievers",
    "runtime": "Runtime",
    "schemas": "Schemas",
    "societies": "Societies",
    "storages": "Storage",
    "tasks": "Tasks",
    "terminators": "Terminators",
    "toolkits": "Toolkits",
    "types": "Types",
    "utils": "Utilities",
    "verifiers": "Verifiers",
    "benchmarks": "Benchmarks",
    "bots": "Bots",
    "personas": "Personas",
    "extractors": "Extractors",
}

# Custom order, this determines the display order of top-level modules
MODULE_ORDER = [
    "agents",
    "configs",
    "datagen",
    "datasets",
    "embeddings",
    "models",
    "interpreters",
    "memories",
    "messages",
    "prompts",
    "responses",
    "retrievers",
    "societies",
    "storages",
    "tasks",
    "terminators",
    "toolkits",
    "types",
    "verifiers",
    "bots",
    "runtime",
    "utils",
    "environments",
    "extractors",
    "personas",
]


def get_module_display_name(module_name):
    """Get the beautiful display name for a module"""
    if module_name in MODULE_NAME_DISPLAY:
        return MODULE_NAME_DISPLAY[module_name]
    # If no mapping exists, convert snake_case to title case
    return module_name.replace('_', ' ').title()


def get_all_modules(package_name="camel", recursive=True):
    """Get all modules in the package"""
    modules = []

    try:
        # Import main package
        package = importlib.import_module(package_name)
        modules.append(package_name)

        # Get package path
        package_path = os.path.dirname(package.__file__)

        # Traverse all Python files in the package
        for root, dirs, files in os.walk(package_path):
            if not recursive and root != package_path:
                continue

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    # Calculate relative path of the module
                    rel_path = os.path.relpath(
                        os.path.join(root, file), os.path.dirname(package_path)
                    )
                    # Convert to module name
                    module_name = os.path.splitext(rel_path)[0].replace(
                        os.sep, "."
                    )
                    modules.append(module_name)

            # Handle subpackages
            for dir_name in dirs:
                if os.path.isfile(os.path.join(root, dir_name, "__init__.py")):
                    # Calculate relative path of the subpackage
                    rel_path = os.path.relpath(
                        os.path.join(root, dir_name),
                        os.path.dirname(package_path),
                    )
                    # Convert to package name
                    subpackage_name = rel_path.replace(os.sep, ".")
                    modules.append(subpackage_name)

    except ImportError as e:
        print(f"Error importing {package_name}: {e}")

    return sorted(modules)


def get_changed_modules(package_name="camel", since_hours=24):
    """Get recently modified modules (for incremental updates)"""
    changed_modules = []

    try:
        # Import main package
        package = importlib.import_module(package_name)
        package_path = os.path.dirname(package.__file__)

        # Calculate time threshold
        time_threshold = time.time() - (since_hours * 3600)

        # Traverse all Python files in the package
        for root, _dirs, files in os.walk(package_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)

                    # Check file modification time
                    if os.path.getmtime(file_path) > time_threshold:
                        if file == "__init__.py":
                            # Handle package
                            rel_path = os.path.relpath(
                                root, os.path.dirname(package_path)
                            )
                            module_name = rel_path.replace(os.sep, ".")
                            changed_modules.append(module_name)
                        else:
                            # Handle module
                            rel_path = os.path.relpath(
                                file_path, os.path.dirname(package_path)
                            )
                            module_name = os.path.splitext(rel_path)[
                                0
                            ].replace(os.sep, ".")
                            changed_modules.append(module_name)

    except ImportError as e:
        print(f"Error importing {package_name}: {e}")

    return sorted(set(changed_modules))


def is_content_substantial(content):
    """Check if content is substantial enough to avoid generating empty documentation"""
    if not content.strip():
        return False

    # Remove empty lines and common useless content
    lines = [line.strip() for line in content.split('\n') if line.strip()]

    # Filter out cases with only headers
    substantial_lines = []
    for line in lines:
        # Skip header lines
        if line.startswith('#'):
            continue
        # Skip lines with only module IDs
        if line.startswith('<a id='):
            continue
        # Skip empty code blocks
        if line in ['```', '```python']:
            continue
        substantial_lines.append(line)

    # If substantial content is less than 3 lines, consider it insufficient
    return len(substantial_lines) >= 3


def build_module_tree(mdx_files):
    """Build module tree based on MDX file names"""

    # Factory function to create new submodule dictionary
    def new_module_dict():
        return {"pages": [], "submodules": defaultdict(new_module_dict)}

    # Build tree structure using nested defaultdict
    module_tree = new_module_dict()

    for file in mdx_files:
        # Get module path from file name
        module_path = file.stem  # Remove .mdx suffix

        # Usually we expect file names in "camel.xxx.yyy" format
        if not module_path.startswith("camel."):
            # If not a camel module, skip
            continue

        # Split module path
        parts = module_path.split('.')

        # Build reference path
        reference_path = f"reference/{module_path}"

        # If it's just the camel module itself
        if len(parts) == 1:
            module_tree["pages"].append(reference_path)
            continue

        # Handle submodules
        current = module_tree
        for i, part in enumerate(
            parts[:-1]
        ):  # Exclude the last part, which is the file name
            if i == 0:  # camel root module
                continue

            # Navigate to submodule
            current = current["submodules"][part]

        # Ensure pages list exists
        if "pages" not in current:
            current["pages"] = []

        # Ensure directory pages (like camel.agents/camel.agents.mdx) appear before their submodules
        if parts[-1] == parts[-2]:
            current["pages"].insert(0, reference_path)
        else:
            current["pages"].append(reference_path)

    return module_tree


def convert_tree_to_navigation(module_tree):
    """Convert module tree to mint.json navigation format"""
    navigation = []

    # Add submodules in custom order
    for module_name in MODULE_ORDER:
        if module_name in module_tree["submodules"]:
            submodule = module_tree["submodules"][module_name]

            # Get pretty display name for submodule
            display_name = get_module_display_name(module_name)

            # Create navigation group
            nav_group = {"group": display_name, "pages": []}

            # Add direct pages for this module
            if "pages" in submodule:
                nav_group["pages"].extend(sorted(submodule["pages"]))

            # Recursively handle submodules
            if submodule.get("submodules"):
                for _sub_name, sub_data in sorted(
                    submodule["submodules"].items()
                ):
                    if sub_data.get("pages"):
                        # Directly flatten submodule pages
                        nav_group["pages"].extend(sorted(sub_data["pages"]))

            # Only add group if it has pages
            if nav_group["pages"]:
                navigation.append(nav_group)

    return navigation


def update_docs_json(docs_json_path, navigation):
    """Update the API Reference navigation section in docs.json file"""
    if not Path(docs_json_path).exists():
        print(f"Error: {docs_json_path} not found")
        return False

    with open(docs_json_path, "r", encoding="utf-8") as f:
        docs_data = json.load(f)

    # Find API Reference tab and update its groups
    tabs = docs_data.get("navigation", {}).get("tabs", [])
    for tab in tabs:
        if tab.get("tab") == "API Reference":
            # Preserve existing Overview group if it exists
            existing_groups = tab.get("groups", [])
            overview_group = None

            # Look for existing Overview group
            for group in existing_groups:
                if group.get("group") == "Overview":
                    overview_group = group
                    break

            # Start with Overview group if it exists, otherwise create a default one
            if overview_group:
                new_groups = [overview_group]
            else:
                new_groups = [
                    {"group": "Overview", "pages": ["reference/index"]}
                ]

            # Add the generated navigation groups
            new_groups.extend(navigation)

            # Update the tab groups
            tab["groups"] = new_groups
            break

    # Save updated docs.json
    with open(docs_json_path, "w", encoding="utf-8") as f:
        json.dump(docs_data, f, indent=2, ensure_ascii=False)

    return True


def parse_docstring(docstring):
    """Parse a docstring and extract structured information"""
    if not docstring:
        return {
            'description': '',
            'args': [],
            'returns': '',
            'raises': [],
            'examples': [],
            'notes': [],
        }

    lines = docstring.strip().split('\n')
    result = {
        'description': '',
        'args': [],
        'returns': '',
        'raises': [],
        'examples': [],
        'notes': [],
    }

    current_section = 'description'
    current_lines = []

    for line in lines:
        line = line.strip()

        # Check for section headers
        if line.lower().startswith(
            ('args:', 'arguments:', 'parameters:', 'param:', 'attributes:')
        ):
            if current_lines and current_section == 'description':
                result['description'] = '\n'.join(current_lines).strip()
            current_section = 'args'
            current_lines = []
        elif line.lower().startswith(('returns:', 'return:')):
            if current_lines and current_section == 'args':
                result['args'].extend(parse_args_section(current_lines))
            current_section = 'returns'
            current_lines = []
        elif line.lower().startswith(
            ('raises:', 'raise:', 'except:', 'exceptions:')
        ):
            if current_lines:
                if current_section == 'args':
                    result['args'].extend(parse_args_section(current_lines))
                elif current_section == 'returns':
                    result['returns'] = '\n'.join(current_lines).strip()
            current_section = 'raises'
            current_lines = []
        elif line.lower().startswith(('examples:', 'example:')):
            if current_lines:
                if current_section == 'args':
                    result['args'].extend(parse_args_section(current_lines))
                elif current_section == 'returns':
                    result['returns'] = '\n'.join(current_lines).strip()
                elif current_section == 'raises':
                    result['raises'].extend(
                        parse_raises_section(current_lines)
                    )
            current_section = 'examples'
            current_lines = []
        elif line.lower().startswith(
            ('note:', 'notes:', 'warning:', 'warnings:')
        ):
            if current_lines:
                if current_section == 'args':
                    result['args'].extend(parse_args_section(current_lines))
                elif current_section == 'returns':
                    result['returns'] = '\n'.join(current_lines).strip()
                elif current_section == 'raises':
                    result['raises'].extend(
                        parse_raises_section(current_lines)
                    )
                elif current_section == 'examples':
                    result['examples'] = current_lines
                elif current_section == 'description':
                    result['description'] = '\n'.join(current_lines).strip()
            current_section = 'notes'
            current_lines = []
        else:
            current_lines.append(line)

    # Process final section
    if current_lines:
        if current_section == 'description':
            result['description'] = '\n'.join(current_lines).strip()
        elif current_section == 'args':
            result['args'].extend(parse_args_section(current_lines))
        elif current_section == 'returns':
            result['returns'] = '\n'.join(current_lines).strip()
        elif current_section == 'raises':
            result['raises'].extend(parse_raises_section(current_lines))
        elif current_section == 'examples':
            result['examples'] = current_lines
        elif current_section == 'notes':
            result['notes'] = current_lines

    return result


def parse_args_section(lines):
    """Parse arguments section and extract parameter info"""
    args = []
    current_arg = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this line starts a new parameter (has parameter name followed by type and colon)
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*(\([^)]+\))?\s*:', line):
            # Save previous arg
            if current_arg:
                # Clean up description
                current_arg['description'] = re.sub(
                    r'\s+', ' ', current_arg['description']
                ).strip()
                args.append(current_arg)

            # Parse new arg
            parts = line.split(':', 1)
            if len(parts) == 2:
                name_type = parts[0].strip()
                description = parts[1].strip()

                # Extract name and type
                type_match = re.match(
                    r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]+)\)', name_type
                )
                if type_match:
                    name = type_match.group(1).strip()
                    type_info = type_match.group(2).strip()
                else:
                    name = name_type.strip()
                    type_info = ''

                current_arg = {
                    'name': name,
                    'type': type_info,
                    'description': description,
                    'optional': 'optional' in description.lower(),
                    'default': extract_default_value(description),
                }
        else:
            # Continuation of current arg description
            if current_arg:
                current_arg['description'] += ' ' + line

    # Add final arg
    if current_arg:
        # Clean up final description
        current_arg['description'] = re.sub(
            r'\s+', ' ', current_arg['description']
        ).strip()
        args.append(current_arg)

    return args


def parse_raises_section(lines):
    """Parse raises section"""
    raises = []
    for line in lines:
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                exception = parts[0].strip()
                description = parts[1].strip()
                raises.append(
                    {'exception': exception, 'description': description}
                )
    return raises


def extract_default_value(description):
    """Extract default value from parameter description"""
    # Look for patterns like (default: value) or (default: :obj:`value`)

    patterns = [
        r'\(default:\s*:obj:`([^`]+)`\)',
        r'\(default:\s*([^)]+)\)',
        r'defaults?\s+to\s+([^.,:;)]+)',
        r'\(default:\s*([^)]*)\)',  # More flexible pattern
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            default_val = match.group(1).strip()
            # Clean up common artifacts
            default_val = default_val.replace(':obj:', '').replace('`', '')
            # Remove trailing punctuation
            default_val = re.sub(r'[.,:;]+$', '', default_val)
            if default_val and default_val not in ['None', 'obj']:
                return default_val

    return None


def escape_mdx_content(text):
    """Escape special characters in text content for MDX compatibility"""
    if not text:
        return text

    # Store code blocks and inline code to protect them from escaping
    code_blocks = []
    inline_codes = []

    # Extract and temporarily replace code blocks (```)
    def extract_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    text = re.sub(r'```[\s\S]*?```', extract_code_block, text)

    # Extract and temporarily replace inline code (`) - including our newly created ones
    def extract_inline_code(match):
        inline_codes.append(match.group(0))
        return f"__INLINE_CODE_{len(inline_codes) - 1}__"

    # First extract existing inline code
    text = re.sub(r'`[^`\n]+`', extract_inline_code, text)

    # Handle reStructuredText-style links: `text <url>`_ -> [text](url)
    def convert_rst_links(text):
        """Convert reStructuredText links to Markdown format"""
        # Pattern for `text <url>`_ format
        rst_link_pattern = r'`([^`]+)\s+<([^>]+)>`_'

        def replace_rst_link(match):
            text_part = match.group(1).strip()
            url_part = match.group(2).strip()
            return f"[{text_part}]({url_part})"

        return re.sub(rst_link_pattern, replace_rst_link, text)

    # Apply reStructuredText link conversion
    text = convert_rst_links(text)

    # Find and wrap JSON-like structures with backticks
    def find_and_wrap_json(text):
        """Find JSON objects in text and wrap them with backticks"""
        result = ""
        i = 0
        while i < len(text):
            if text[i] == '{':
                # Found potential JSON start, try to find the matching closing brace
                brace_count = 1
                json_start = i
                i += 1
                has_quotes = False
                has_colon = False

                while i < len(text) and brace_count > 0:
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                    elif text[i] in ['"', "'"]:
                        has_quotes = True
                    elif text[i] == ':':
                        has_colon = True
                    i += 1

                if brace_count == 0 and has_quotes and has_colon:
                    # This looks like a complete JSON object
                    json_content = text[json_start:i]
                    result += f"`{json_content}`"
                else:
                    # Not a complete JSON, add the opening brace and continue
                    result += text[json_start]
                    i = json_start + 1
            else:
                result += text[i]
                i += 1

        return result

    # Apply JSON wrapping
    text = find_and_wrap_json(text)

    # Find and wrap angle bracket content that should be in code format
    def find_and_wrap_angle_brackets(text):
        """Find angle bracket content and wrap with backticks when appropriate"""

        # Use regex to find all angle bracket patterns and wrap them
        def replace_angle_brackets(match):
            full_match = match.group(0)

            # Skip if it's already a proper HTML anchor tag like <a id="...">
            if re.match(r'^<a\s+id=', full_match):
                return full_match

            # For all other angle bracket content, wrap it in backticks
            return f"`{full_match}`"

        # Pattern to match angle brackets with content inside
        # This will match <anything> where anything doesn't contain < or >
        pattern = r'<[^<>]+>'

        return re.sub(pattern, replace_angle_brackets, text)

    # Apply angle bracket wrapping
    text = find_and_wrap_angle_brackets(text)

    # Find and wrap content with >= and <= operators that should be in code format
    def find_and_wrap_comparison_operators(text):
        """Find comparison operators and wrap them with backticks when appropriate"""
        # Pattern for length constraints like "length >= 1 and <= 100"
        text = re.sub(r'(length\s*>=\s*\d+\s*and\s*<=\s*\d+)', r'`\1`', text)
        text = re.sub(r'(>=\s*\d+\s*and\s*<=\s*\d+)', r'`\1`', text)

        # Pattern for standalone comparison operators with numbers
        text = re.sub(r'(?<!\w)(>=\s*\d+)(?!\w)', r'`\1`', text)
        text = re.sub(r'(?<!\w)(<=\s*\d+)(?!\w)', r'`\1`', text)

        return text

    # Apply comparison operator wrapping
    text = find_and_wrap_comparison_operators(text)

    # Now extract ALL newly created inline code sections (including angle brackets and operators)
    text = re.sub(r'`[^`\n]+`', extract_inline_code, text)

    # Escape remaining curly braces that would be interpreted as JavaScript expressions
    # This will only affect braces that are NOT inside backticks now
    text = re.sub(r'(?<!\\)\{', r'\\{', text)
    text = re.sub(r'(?<!\\)\}', r'\\}', text)

    # Escape remaining angle brackets that could be interpreted as JSX elements
    # But be careful not to escape legitimate comparison operators or HTML tags
    text = re.sub(r'(?<![\w\s=!<>])<(?![\w\s=/])', r'&lt;', text)
    text = re.sub(r'(?<![\w\s=!<>])>(?![\w\s=])', r'&gt;', text)

    # Restore inline code
    for i, code in enumerate(inline_codes):
        text = text.replace(f"__INLINE_CODE_{i}__", code)

    # Restore code blocks
    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)

    return text


def format_code_content(content):
    """Format content as inline code if it contains special characters"""
    if not content:
        return content

    # Check if content looks like JSON/dict/object structure
    # This includes patterns like {"key": "value"} or complex nested structures
    json_like_patterns = [
        r'\{.*:.*\}',  # Basic key-value structure
        r'\{.*\{.*\}.*\}',  # Nested structures
        r'^\{.*\}$',  # Entire string is a JSON-like object
        r'\[.*\{.*\}.*\]',  # Array containing objects
    ]

    for pattern in json_like_patterns:
        if re.search(pattern, content):
            # Remove existing backticks to avoid double-escaping
            content = content.replace('`', '')
            return f"`{content}`"

    # Check if content contains other special characters that should be in code format
    special_chars = ['<', '>', '"', "'"]
    if any(char in content for char in special_chars):
        # Remove existing backticks to avoid double-escaping
        content = content.replace('`', '')
        return f"`{content}`"

    return content


def is_class_substantial(class_node):
    """Check if a class has substantial content worth documenting"""
    # Get class docstring
    class_doc = ast.get_docstring(class_node)

    # Count meaningful methods (excluding __init__ and other special methods)
    meaningful_methods = []

    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == '__init__':
                # Check if __init__ has substantial documentation
                init_doc = ast.get_docstring(node)
                if (
                    init_doc and len(init_doc.strip()) > 50
                ):  # Substantial docstring
                    meaningful_methods.append(node.name)
            elif not node.name.startswith('_'):  # Public methods
                meaningful_methods.append(node.name)
            elif node.name in [
                '__str__',
                '__repr__',
                '__call__',
            ]:  # Important special methods
                meaningful_methods.append(node.name)

    # A class is substantial if:
    # 1. It has a class docstring, OR
    # 2. It has public methods beyond __init__, OR
    # 3. It has a documented __init__ method, OR
    # 4. It has important special methods
    return (class_doc and len(class_doc.strip()) > 20) or len(
        meaningful_methods
    ) > 0


def generate_ast_docs(module_name, output_dir):
    """Generate documentation by parsing Python source code directly using AST"""
    try:
        # Import the module to get the file path
        module = importlib.import_module(module_name)
        if not hasattr(module, '__file__') or not module.__file__:
            return None

        module_file = module.__file__
        if module_file.endswith('.pyc'):
            module_file = module_file[:-1]  # Remove 'c' to get .py file

        if not os.path.exists(module_file):
            return None

        # Parse the source file
        with open(module_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        # Extract module-level docstring
        module_doc = ast.get_docstring(tree) or ""

        # Generate markdown content
        markdown_lines = []

        # Add module anchor point
        markdown_lines.append(f'<a id="{module_name}"></a>')
        markdown_lines.append("")

        if module_doc:
            escaped_module_doc = escape_mdx_content(module_doc)
            markdown_lines.append(escaped_module_doc)
            markdown_lines.append("")

        # Process classes and functions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if is_class_substantial(node):
                    class_md = generate_class_docs(node, module_name)
                    markdown_lines.extend(class_md)
            elif (
                isinstance(node, ast.FunctionDef) and node.col_offset == 0
            ):  # Top-level functions only
                func_md = generate_function_docs(node, module_name)
                markdown_lines.extend(func_md)

        # Write output
        if not is_content_substantial('\n'.join(markdown_lines)):
            return None

        output_file = os.path.join(output_dir, f"{module_name}.mdx")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_lines))

        return output_file

    except Exception as e:
        print(f"Error generating docs for {module_name}: {e}")
        return None


def generate_class_docs(class_node, module_name):
    """Generate documentation for a class"""
    lines = []

    # Class anchor point
    class_name = class_node.name
    lines.append(f'<a id="{module_name}.{class_name}"></a>')
    lines.append("")

    # Class header without backticks
    lines.append(f"## {class_name}")
    lines.append("")

    # Class signature in Python code block
    # Get class signature with base classes
    bases = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(f"{base.attr}")

    signature = f"class {class_name}"
    if bases:
        signature += f"({', '.join(bases)})"
    signature += ":"

    lines.append("```python")
    lines.append(signature)
    lines.append("```")
    lines.append("")

    # Class docstring
    class_doc = ast.get_docstring(class_node)
    if class_doc:
        doc_info = parse_docstring(class_doc)

        if doc_info['description']:
            escaped_description = escape_mdx_content(doc_info['description'])
            lines.append(escaped_description)
            lines.append("")

        if doc_info['args']:
            lines.append("**Parameters:**")
            lines.append("")
            for arg in doc_info['args']:
                type_str = (
                    f" ({format_code_content(arg['type'])})"
                    if arg['type']
                    else ""
                )
                default_str = (
                    f" (default: {format_code_content(arg['default'])})"
                    if arg['default']
                    else ""
                )
                escaped_description = escape_mdx_content(arg['description'])
                lines.append(
                    f"- **{arg['name']}**{type_str}: {escaped_description}{default_str}"
                )
            lines.append("")

        if doc_info.get('notes'):
            lines.append('**Note:**')
            lines.append("")
            lines.extend(
                [escape_mdx_content(line) for line in doc_info['notes']]
            )
            lines.append("")

    # Process methods
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            method_lines = generate_method_docs(node, class_name, module_name)
            lines.extend(method_lines)

    return lines


def generate_function_docs(func_node, module_name):
    """Generate documentation for a function"""
    lines = []

    # Function anchor point
    function_name = func_node.name
    lines.append(f'<a id="{module_name}.{function_name}"></a>')
    lines.append("")

    # Function header without backticks
    lines.append(f"## {function_name}")
    lines.append("")

    # Function signature in Python code block
    signature = generate_function_signature(func_node, multiline=True)

    lines.append("```python")
    lines.append(f"def {signature}:")
    lines.append("```")
    lines.append("")

    # Function docstring
    func_doc = ast.get_docstring(func_node)
    if func_doc:
        doc_info = parse_docstring(func_doc)

        if doc_info['description']:
            escaped_description = escape_mdx_content(doc_info['description'])
            lines.append(escaped_description)
            lines.append("")

        if doc_info['args']:
            lines.append("**Parameters:**")
            lines.append("")
            for arg in doc_info['args']:
                type_str = (
                    f" ({format_code_content(arg['type'])})"
                    if arg['type']
                    else ""
                )
                default_str = (
                    f" (default: {format_code_content(arg['default'])})"
                    if arg['default']
                    else ""
                )
                escaped_description = escape_mdx_content(arg['description'])
                lines.append(
                    f"- **{arg['name']}**{type_str}: {escaped_description}{default_str}"
                )
            lines.append("")

        if doc_info['returns']:
            lines.append("**Returns:**")
            lines.append("")
            escaped_returns = escape_mdx_content(doc_info['returns'])
            lines.append(f"  {escaped_returns}")
            lines.append("")

        if doc_info['raises']:
            lines.append("**Raises:**")
            lines.append("")
            for exc in doc_info['raises']:
                escaped_description = escape_mdx_content(exc['description'])
                lines.append(
                    f"- **{format_code_content(exc['exception'])}**: {escaped_description}"
                )
            lines.append("")

        if doc_info.get('notes'):
            lines.append('**Note:**')
            lines.append("")
            lines.extend(
                [escape_mdx_content(line) for line in doc_info['notes']]
            )
            lines.append("")

    return lines


def generate_method_docs(method_node, class_name, module_name):
    """Generate documentation for a class method"""
    lines = []

    # Method anchor point
    method_name = method_node.name
    lines.append(f'<a id="{module_name}.{class_name}.{method_name}"></a>')
    lines.append("")

    # Method header without backticks
    lines.append(f"### {method_name}")
    lines.append("")

    # Method signature in Python code block
    signature = generate_function_signature(method_node, multiline=True)

    lines.append("```python")
    lines.append(f"def {signature}:")
    lines.append("```")
    lines.append("")

    # Method docstring
    method_doc = ast.get_docstring(method_node)
    if method_doc:
        doc_info = parse_docstring(method_doc)

        if doc_info['description']:
            escaped_description = escape_mdx_content(doc_info['description'])
            lines.append(escaped_description)
            lines.append("")

        if doc_info['args']:
            lines.append("**Parameters:**")
            lines.append("")
            for arg in doc_info['args']:
                # Skip 'self' parameter
                if arg['name'] == 'self':
                    continue
                type_str = (
                    f" ({format_code_content(arg['type'])})"
                    if arg['type']
                    else ""
                )
                default_str = (
                    f" (default: {format_code_content(arg['default'])})"
                    if arg['default']
                    else ""
                )
                escaped_description = escape_mdx_content(arg['description'])
                lines.append(
                    f"- **{arg['name']}**{type_str}: {escaped_description}{default_str}"
                )
            lines.append("")

        if doc_info['returns']:
            lines.append("**Returns:**")
            lines.append("")
            escaped_returns = escape_mdx_content(doc_info['returns'])
            lines.append(f"  {escaped_returns}")
            lines.append("")

        if doc_info.get('notes'):
            lines.append('**Note:**')
            lines.append("")
            lines.extend(
                [escape_mdx_content(line) for line in doc_info['notes']]
            )
            lines.append("")

    return lines


def generate_function_signature(func_node, multiline=False):
    """Generate function signature from AST node"""
    args = []

    # Regular arguments
    for arg in func_node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)

    # Default values
    num_defaults = len(func_node.args.defaults)
    if num_defaults > 0:
        for i, default in enumerate(func_node.args.defaults):
            arg_index = len(func_node.args.args) - num_defaults + i
            args[arg_index] += f" = {ast.unparse(default)}"

    # *args
    if func_node.args.vararg:
        vararg_str = f"*{func_node.args.vararg.arg}"
        if func_node.args.vararg.annotation:
            vararg_str += f": {ast.unparse(func_node.args.vararg.annotation)}"
        args.append(vararg_str)

    # **kwargs
    if func_node.args.kwarg:
        kwarg_str = f"**{func_node.args.kwarg.arg}"
        if func_node.args.kwarg.annotation:
            kwarg_str += f": {ast.unparse(func_node.args.kwarg.annotation)}"
        args.append(kwarg_str)

    # Format signature based on length and multiline preference
    if multiline and (len(args) > 3 or sum(len(arg) for arg in args) > 60):
        # Multi-line format
        if args:
            formatted_args = ',\n    '.join(args)
            return f"{func_node.name}(\n    {formatted_args}\n)"
        else:
            return f"{func_node.name}()"
    else:
        # Single-line format
        return f"{func_node.name}({', '.join(args)})"


def generate_custom_docs(modules, output_dir, package_name="camel"):
    """Generate documentation using custom AST parser"""
    os.makedirs(output_dir, exist_ok=True)

    generated_count = 0
    skipped_count = 0

    for i, module in enumerate(modules):
        print(f"  [{i+1}/{len(modules)}] Processing {module}...")

        output_file = generate_ast_docs(module, output_dir)
        if output_file:
            print(f"    Generated {os.path.basename(output_file)}")
            generated_count += 1
        else:
            print(f"    Skipped {module} (insufficient content)")
            skipped_count += 1

    return generated_count, skipped_count


def discover_module_structure(package_name="camel"):
    """Dynamically discover the module structure from the actual package"""
    try:
        package = importlib.import_module(package_name)
        package_path = os.path.dirname(package.__file__)

        module_structure = {}

        # Walk through the package directory
        for root, dirs, files in os.walk(package_path):
            # Skip __pycache__ and hidden directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith('__pycache__') and not d.startswith('.')
            ]

            # Get relative path from package root
            rel_path = os.path.relpath(root, package_path)
            if rel_path == '.':
                current_module = package_name
            else:
                current_module = (
                    f"{package_name}.{rel_path.replace(os.sep, '.')}"
                )

            # Check if this directory has an __init__.py (making it a package)
            if '__init__.py' in files:
                # Get the top-level module name
                parts = current_module.split('.')
                if len(parts) >= 2:  # camel.something
                    top_level = parts[1]
                    if top_level not in module_structure:
                        module_structure[top_level] = {
                            'display_name': get_module_display_name(top_level),
                            'modules': [],
                        }

        # Now get all actual importable modules
        all_modules = get_all_modules(package_name)

        # Organize modules by top-level package
        for module in all_modules:
            parts = module.split('.')
            if len(parts) >= 2:  # camel.something
                top_level = parts[1]
                if top_level in module_structure:
                    module_structure[top_level]['modules'].append(module)

        return module_structure

    except ImportError as e:
        print(f"Error discovering package structure: {e}")
        return {}


def update_module_mappings():
    """Update MODULE_NAME_DISPLAY based on discovered modules"""
    global MODULE_NAME_DISPLAY, MODULE_ORDER

    structure = discover_module_structure()

    # Update display names for discovered modules
    for module_name in structure.keys():
        if module_name not in MODULE_NAME_DISPLAY:
            # Convert snake_case to Title Case
            display_name = module_name.replace('_', ' ').title()
            MODULE_NAME_DISPLAY[module_name] = display_name

    # Update module order to include newly discovered modules
    discovered_modules = list(structure.keys())
    existing_order = [m for m in MODULE_ORDER if m in discovered_modules]
    new_modules = [m for m in discovered_modules if m not in MODULE_ORDER]

    # Keep existing order for known modules, add new ones at the end
    MODULE_ORDER[:] = existing_order + sorted(new_modules)

    return structure


def main():
    parser = argparse.ArgumentParser(
        description="Generate API documentation and update mint.json configuration"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="docs/mintlify/reference",
        help="Output directory for MDX files",
    )
    parser.add_argument(
        "--mint_json",
        type=str,
        default="docs/mintlify/docs.json",
        help="Path to docs.json file",
    )
    parser.add_argument(
        "--package",
        type=str,
        default="camel",
        help="Package name to generate documentation for",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean output directory before generating new files",
    )
    parser.add_argument(
        "--skip_generation",
        action="store_true",
        help="Skip API documentation generation, only update mint.json",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only process modules that have been changed recently",
    )
    parser.add_argument(
        "--since_hours",
        type=int,
        default=24,
        help="Hours to look back for changed files (used with --incremental)",
    )
    args = parser.parse_args()

    if not args.skip_generation:
        # Update module mappings based on discovered structure
        print("Discovering module structure...")
        structure = update_module_mappings()
        print(f"Discovered {len(structure)} top-level modules")

        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)

        # Clean output directory (if needed)
        if args.clean:
            print(f"Cleaning output directory: {args.output_dir}")
            for file in glob.glob(os.path.join(args.output_dir, "*.mdx")):
                # Preserve the index.mdx file (API Reference landing page)
                if os.path.basename(file) == "index.mdx":
                    print(f"  Preserving {os.path.basename(file)}")
                    continue
                os.remove(file)
                print(f"  Removed {os.path.basename(file)}")

        # Get modules to process
        if args.incremental:
            print(
                f"Looking for modules changed in the last {args.since_hours} hours..."
            )
            modules = get_changed_modules(args.package, args.since_hours)
            if not modules:
                print("No modules have been changed recently.")
                return
            print(f"Found {len(modules)} changed modules")
        else:
            print(f"Discovering all modules in {args.package}...")
            modules = get_all_modules(args.package)

        # Generate documentation
        print(f"Generating documentation for {len(modules)} modules...")
        generated_count, skipped_count = generate_custom_docs(
            modules, args.output_dir, args.package
        )

        print(
            f"\nGenerated: {generated_count} files, Skipped: {skipped_count} files"
        )

    # Build module tree and update mint.json
    print("\nUpdating mint.json configuration...")

    # Get generated MDX files
    mdx_files = list(Path(args.output_dir).glob("*.mdx"))
    if not mdx_files:
        print(f"No MDX files found in {args.output_dir}")
        return

    print(f"Found {len(mdx_files)} MDX files")

    # Build module tree
    module_tree = build_module_tree(mdx_files)

    # Convert to navigation format
    navigation = convert_tree_to_navigation(module_tree)

    # Update mint.json
    if update_docs_json(args.mint_json, navigation):
        print(
            f"Updated {args.mint_json} with {len(navigation)} navigation groups"
        )

    # Print navigation structure summary
    print("\nNavigation structure summary:")
    for item in navigation:
        if isinstance(item, str):
            print(f"- {item}")
        else:
            print(f"- Group: {item['group']} ({len(item['pages'])} pages)")

    print("\nAPI documentation build completed successfully!")
    print(f"Documentation files: {args.output_dir}")
    print(f"Configuration file: {args.mint_json}")

    if not args.skip_generation:
        print("\nDocumentation generated using custom AST parser.")
        print("To preview your Mintlify documentation, run:")
        print("  cd docs/mintlify && npx mintlify dev")


if __name__ == "__main__":
    main()
