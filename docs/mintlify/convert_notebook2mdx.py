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

"""
This script is used to convert rst, md, and ipynb files in
the docs/cookbooks directory to mdx format for migration to mintify.
"""

import argparse
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import nbformat
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import Preprocessor


class RemoveOutputPreprocessor(Preprocessor):
    """Preprocessor to remove output results from notebook code cells."""

    def preprocess_cell(self, cell, resources, index):
        """Process a single cell; if it is a code cell, remove the output."""
        if cell.cell_type == 'code':
            print(
                f"[DEBUG] Preprocessor removing outputs from code cell {index}"
            )
            cell.outputs = []
            cell.execution_count = None
        return cell, resources


def fix_html_tags(content):
    """Fix HTML tag closures and handle MDX special syntax."""
    # Fix common unclosed tags
    # Handle <i> tags
    content = re.sub(r'<i>([^<]*?)(?!</i>)(?=<|\n|$)', r'<i>\1</i>', content)

    # Handle conflicts between HTML tags and JSX syntax in MDX
    # Handle img tags, ensuring correct self-closing format
    content = re.sub(r'<img([^>]*?)></img>', r'<img\1/>', content)
    # For img tags without closing tags, add self-closing slash
    content = re.sub(r'<img([^>/]*?)>(?!</img>)', r'<img\1/>', content)

    # For other self-closing tags, ensure correct JSX format
    content = re.sub(r'<([\w]+)([^>]*?)\/>', r'<\1\2/>', content)

    # Do not escape asterisks and underscores in Markdown syntax
    # We completely remove this part of the code to keep Markdown syntax intact

    # Restore special characters in code blocks
    code_block_pattern = re.compile(r'```.*?```', re.DOTALL)

    def restore_code_block(match):
        return match.group(0)

    content = code_block_pattern.sub(restore_code_block, content)

    return content


def fix_duplicate_paths(path_str):
    """Fix duplicate directory names in image paths."""
    # First, standardize the path by removing extra slashes
    path_str = path_str.replace('//', '/')

    # Split the path
    parts = path_str.split('/')

    # Remove empty parts
    parts = [part for part in parts if part]

    # Detect and remove duplicate path segments
    result = []
    for _i, part in enumerate(parts):
        # Check if the current part is already duplicated in the result
        duplicate = False
        for j in range(len(result)):
            if (
                part == result[j] and part != 'images'
            ):  # Allow keeping the images directory
                duplicate = True
                break
        if not duplicate:
            result.append(part)

    # Ensure the images directory is at the beginning of the path
    if 'images' in result:
        result.remove('images')
        if not result or result[0] != 'images':
            result.insert(0, 'images')

    # Combine the path, prefixing with ./
    path = './images/' if 'images' in result else './'
    if result and result[0] == 'images':
        path = './' + '/'.join(result)
    else:
        path = './images/' + '/'.join(result) if result else './images'

    # Ensure no extra slashes
    path = path.replace('//', '/')

    return path


def convert_md_to_mdx(
    md_file, output_dir=None, image_dir=None, input_root=None
):
    """Convert Markdown files to MDX format."""
    print(f"Converting MD file: {md_file}")

    # Read Markdown file content
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create output file path
    if output_dir:
        output_file = Path(output_dir) / f"{Path(md_file).stem}.mdx"
    else:
        output_file = Path(f"{md_file.with_suffix('.mdx')}")

    # Simplified image directory logic: always create images folder next to the mdx file
    image_output_dir = Path(output_file).parent / "images"

    # Ensure image output directory exists
    os.makedirs(image_output_dir, exist_ok=True)

    # Images are always in ./images/ relative to mdx file
    rel_image_path = "./images"

    # Extract and process base64 encoded images
    images_saved = []

    # Match image links in Markdown
    def extract_base64_image(match):
        img_alt = match.group(1)
        img_path = match.group(2)

        # Check if it is a base64 encoded image
        if img_path.startswith('data:image'):
            # Parse base64 encoding
            try:
                header, base64_data = img_path.split(',', 1)
                image_format = header.split(';')[0].split('/')[1]

                # Generate file name
                image_name = f"{Path(md_file).stem}_{len(images_saved) + 1}.{image_format}"
                image_path = os.path.join(image_output_dir, image_name)

                # Save image
                import base64

                with open(image_path, 'wb') as img_file:
                    img_file.write(base64.b64decode(base64_data))

                images_saved.append((image_name, image_path))
                print(
                    f"  Extracted and saved image from Markdown: {image_name}"
                )

                # Return updated image reference, using simplified alt text
                return f'![{img_alt}]({rel_image_path}/{image_name})'
            except Exception as e:
                print(f"  Error extracting base64 image: {e}")
                return match.group(0)
        elif '://' in img_path or img_path.startswith('http'):
            return match.group(0)  # Keep external URLs
        else:
            # Handle local images
            try:
                local_img_path = img_path
                # Ensure using forward slashes
                local_img_path = local_img_path.replace('\\', '/')
                # If not a relative path, construct a relative path
                if not local_img_path.startswith(
                    './'
                ) and not local_img_path.startswith('../'):
                    return f'![{img_alt}]({rel_image_path}/{os.path.basename(local_img_path)})'
                return f'![{img_alt}]({local_img_path})'
            except Exception as e:
                print(f"  Error processing local image path: {e}")
                return match.group(0)

    # Process images in Markdown format
    content = re.sub(r'!\[(.*?)\]\((.*?)\)', extract_base64_image, content)

    # Handle image tags in HTML
    def extract_base64_html_img(match):
        full_tag = match.group(0)
        src_match = re.search(r'src=["\'](.*?)["\']', full_tag)
        if not src_match:
            return full_tag

        src = src_match.group(1)
        if src.startswith('data:image'):
            try:
                header, base64_data = src.split(',', 1)
                image_format = header.split(';')[0].split('/')[1]

                # Generate file name
                image_name = f"{Path(md_file).stem}_{len(images_saved) + 1}.{image_format}"
                image_path = os.path.join(image_output_dir, image_name)

                # Save image
                import base64

                with open(image_path, 'wb') as img_file:
                    img_file.write(base64.b64decode(base64_data))

                images_saved.append((image_name, image_path))
                print(
                    f"  Extracted and saved image from HTML tag: {image_name}"
                )

                # Return updated image tag
                new_src = f"{rel_image_path}/{image_name}"
                return full_tag.replace(src, new_src)
            except Exception as e:
                print(f"  Error extracting base64 image from HTML: {e}")
                return full_tag
        elif '://' in src or src.startswith('http'):
            return full_tag  # Keep external URLs
        else:
            # Handle local image paths
            try:
                new_src = f"{rel_image_path}/{os.path.basename(src)}"
                return full_tag.replace(src, new_src)
            except Exception as e:
                print(f"  Error processing HTML image path: {e}")
                return full_tag

    content = re.sub(r'<img[^>]+>', extract_base64_html_img, content)

    # Remove style tags
    content = re.sub(
        r"<style[\s\S]*?</style>", "", content, flags=re.IGNORECASE
    )

    # Fix HTML tag closures
    content = fix_html_tags(content)

    # Check if there is already front matter; if not, add it
    if not content.startswith('---'):
        title = Path(md_file).stem.replace('_', ' ').title()
        front_matter = """---
title: "{title}"
---

""".format(title=title)

        # For key_modules files, remove any H1 header that matches the title to avoid duplication
        if 'key_modules' in str(md_file):
            # Remove H1 header that matches the title (case-insensitive)
            h1_pattern = r'^#\s+' + re.escape(title) + r'\s*\n'
            content = re.sub(
                h1_pattern, '', content, flags=re.MULTILINE | re.IGNORECASE
            )

            # Also try to match the original filename-based title
            original_title = Path(md_file).stem.replace('_', ' ')
            h1_pattern_original = (
                r'^#\s+' + re.escape(original_title) + r'\s*\n'
            )
            content = re.sub(
                h1_pattern_original,
                '',
                content,
                flags=re.MULTILINE | re.IGNORECASE,
            )

        content = front_matter + content

    # Write to MDX file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return output_file


def standardize_html_blocks(content):
    """Standardize HTML code blocks, especially for handling button and image layouts."""
    print("Starting to standardize HTML code blocks...")

    # Original HTML block
    old_html = '''<div class="align-center">
  <a href="https://www.camel-ai.org/"><img src="https://i.postimg.cc/KzQ5rfBC/button.png"width="150"></a>
  <a href="https://discord.camel-ai.org"><img src="https://i.postimg.cc/L4wPdG9N/join-2.png"  width="150"></a></a>
'''

    # New standardized HTML block
    new_html = '''<div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
  <a href="https://www.camel-ai.org/">
    <img src="https://i.postimg.cc/KzQ5rfBC/button.png" width="150" alt="CAMEL Homepage"/>
  </a>
  <a href="https://discord.camel-ai.org">
    <img src="https://i.postimg.cc/L4wPdG9N/join-2.png" width="150" alt="Join Discord"/>
  </a>
</div>'''

    # Directly replace
    if old_html in content:
        print("Found HTML block to replace")
        content = content.replace(old_html, new_html)
    else:
        print("Did not find HTML block to replace")

    old2 = """⭐ <i>Star us on [*Github*](https://github.com/camel-ai/camel), join our [*Discord*](https://discord.camel-ai.org) or follow our [*X*](https://x.com/camelaiorg)</i>
</div>"""
    new2 = """
⭐ *Star us on [GitHub](https://github.com/camel-ai/camel), join our [Discord](https://discord.camel-ai.org), or follow us on [X](https://x.com/camelaiorg)*

---"""
    if old2 in content:
        print("Found HTML block to replace")
        content = content.replace(old2, new2)
    else:
        print("Did not find HTML block to replace")

    old3 = """
<div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
  <a href="https://www.camel-ai.org/">
    <img src="https://i.postimg.cc/KzQ5rfBC/button.png" width="150" alt="CAMEL Homepage"/>
  </a>
  <a href="https://discord.camel-ai.org">
    <img src="https://i.postimg.cc/L4wPdG9N/join-2.png" width="150" alt="Join Discord"/>
  </a>
</div>  
⭐ <i>Star us on </i><a href="https://github.com/camel-ai/camel">Github</a> </i>, join our [*Discord*](https://discord.camel-ai.org) or follow our [*X*](https://x.com/camelaiorg)  ⭐
</div>"""
    new3 = """
<div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
  <a href="https://www.camel-ai.org/">
    <img src="https://i.postimg.cc/KzQ5rfBC/button.png" width="150" alt="CAMEL Homepage"/>
  </a>
  <a href="https://discord.camel-ai.org">
    <img src="https://i.postimg.cc/L4wPdG9N/join-2.png" width="150" alt="Join Discord"/>
  </a>
</div>  

⭐ *Star us on [GitHub](https://github.com/camel-ai/camel), join our [Discord](https://discord.camel-ai.org), or follow us on [X](https://x.com/camelaiorg)*
"""

    if old3 in content:
        print("Found HTML block to replace")
        content = content.replace(old3, new3)
    else:
        print("Did not find HTML block to replace")

    return content


def convert_ipynb_to_mdx(
    ipynb_file,
    output_dir=None,
    image_dir=None,
    input_root=None,
    remove_outputs=True,
):
    """Convert Jupyter Notebook to MDX format."""
    print(f"Converting IPYNB file: {ipynb_file}")

    if nbformat is None:
        raise RuntimeError(
            "nbformat/nbconvert is not installed. Cannot process .ipynb files."
        )

    # Read Jupyter Notebook
    with open(ipynb_file, 'r', encoding='utf-8') as f:
        notebook = nbformat.read(f, as_version=4)

    # Configure exporter; if outputs need to be removed, add preprocessor
    exporter = MarkdownExporter()
    if remove_outputs:
        print("  Registering preprocessor to remove outputs")
        exporter.register_preprocessor(RemoveOutputPreprocessor, enabled=True)

    # Use nbconvert to convert Notebook to Markdown
    markdown, resources = exporter.from_notebook_node(notebook)

    # Fallback: Manual cleanup if preprocessor didn't work
    if remove_outputs:
        # Check if outputs are still present (indicating preprocessor didn't work)
        outputs_found = False
        for cell in notebook.cells:
            if cell.cell_type == 'code' and cell.outputs:
                outputs_found = True
                break

        if outputs_found:
            print("  Preprocessor didn't work, falling back to manual cleanup")
            for i, cell in enumerate(notebook.cells):
                if cell.cell_type == 'code':
                    if cell.outputs:
                        print(
                            f"  [DEBUG] Manual cleanup of code cell {i}: had {len(cell.outputs)} outputs"
                        )
                    cell.outputs = []
                    cell.execution_count = None
                    if hasattr(cell, 'metadata'):
                        cell.metadata.pop('execution', None)
                        cell.metadata.pop('scrolled', None)

            # Re-convert with cleaned notebook
            markdown, resources = exporter.from_notebook_node(notebook)

    # Create output file path
    if output_dir:
        output_file = Path(output_dir) / f"{Path(ipynb_file).stem}.mdx"
    else:
        output_file = Path(f"{ipynb_file.with_suffix('.mdx')}")

    # Simplified image directory logic: always create images folder next to the mdx file
    image_output_dir = Path(output_file).parent / "images"

    # Ensure image output directory exists
    os.makedirs(image_output_dir, exist_ok=True)

    # Extract and save images
    images_saved = []
    if resources.get('outputs'):
        print(f"  Found {len(resources['outputs'])} image resources")
        for image_name, image_data in resources['outputs'].items():
            image_path = os.path.join(image_output_dir, image_name)
            with open(image_path, 'wb') as f:
                f.write(image_data)
            images_saved.append((image_name, image_path))

    # Images are always in ./images/ relative to mdx file
    rel_image_path = "./images"

    # Process base64 encoded images
    def extract_base64_image_from_notebook(match):
        img_alt = match.group(1)
        img_path = match.group(2)

        # Check if it is a base64 encoded image
        if img_path.startswith('data:image'):
            try:
                # Parse base64 encoding
                header, base64_data = img_path.split(',', 1)
                image_format = header.split(';')[0].split('/')[1]

                # Generate file name
                image_name = f"{Path(ipynb_file).stem}_{len(images_saved) + 1}.{image_format}"
                image_path = os.path.join(image_output_dir, image_name)

                # Save image
                import base64

                with open(image_path, 'wb') as img_file:
                    img_file.write(base64.b64decode(base64_data))

                images_saved.append((image_name, image_path))
                print(
                    f"  Extracted and saved base64 image from Notebook: {image_name}"
                )

                # Return updated image reference, keeping original alt text
                return f'![{img_alt}]({rel_image_path}/{image_name})'
            except Exception as e:
                print(f"  Error extracting base64 image: {e}")
                return match.group(0)

        # Handle non-base64 images
        return replace_image_path(match)

    # Adjust image references in markdown
    def replace_image_path(match):
        img_alt = match.group(1)
        img_path = match.group(2)
        # Check if it is a local image or external URL
        if '://' in img_path or img_path.startswith('http'):
            return f'![{img_alt}]({img_path})'
        else:
            # Ensure path uses slashes, not backslashes
            fixed_path = img_path.replace('\\', '/')
            return f'![{img_alt}]({rel_image_path}/{os.path.basename(fixed_path)})'

    # First process base64 images
    markdown = re.sub(
        r'!\[(.*?)\]\((data:image.*?)\)',
        extract_base64_image_from_notebook,
        markdown,
    )
    # Then process other images
    markdown = re.sub(
        r'!\[(.*?)\]\(((?!data:image).*?)\)', replace_image_path, markdown
    )

    # Handle image tags in HTML
    def replace_html_img(match):
        full_tag = match.group(0)
        src_match = re.search(r'src=["\'](.*?)["\']', full_tag)
        if not src_match:
            return full_tag

        src = src_match.group(1)
        if src.startswith('data:image'):
            try:
                # Parse base64 encoding
                header, base64_data = src.split(',', 1)
                image_format = header.split(';')[0].split('/')[1]

                # Generate file name
                image_name = f"{Path(ipynb_file).stem}_html_{len(images_saved) + 1}.{image_format}"
                image_path = os.path.join(image_output_dir, image_name)

                # Save image
                import base64

                with open(image_path, 'wb') as img_file:
                    img_file.write(base64.b64decode(base64_data))

                images_saved.append((image_name, image_path))
                print(
                    f"  Extracted and saved base64 image from HTML tag: {image_name}"
                )

                # Return updated image tag
                new_src = f"{rel_image_path}/{image_name}"
                return full_tag.replace(src, new_src)
            except Exception as e:
                print(f"  Error extracting base64 image from HTML: {e}")
                return full_tag
        elif '://' in src or src.startswith('http'):
            return full_tag  # Keep external URLs unchanged
        else:
            # Replace local path
            new_src = f"{rel_image_path}/{os.path.basename(src)}"
            return full_tag.replace(src, new_src)

    markdown = re.sub(r'<img[^>]+>', replace_html_img, markdown)

    # Remove style tags
    markdown = re.sub(
        r"<style[\s\S]*?</style>", "", markdown, flags=re.IGNORECASE
    )

    # Fix HTML tag closures
    markdown = fix_html_tags(markdown)

    # Standardize HTML code blocks
    markdown = standardize_html_blocks(markdown)

    # Add MDX front matter
    notebook_title = Path(ipynb_file).stem.replace('_', ' ').title()

    # Check if the first cell of the notebook is markdown and contains a title
    if notebook.cells and notebook.cells[0].cell_type == 'markdown':
        first_cell_content = notebook.cells[0].source
        title_match = re.search(
            r'^#\s+(.*?)$', first_cell_content, re.MULTILINE
        )
        if title_match:
            notebook_title = title_match.group(1)
            markdown = re.sub(
                r'^#\s+' + re.escape(notebook_title) + r'\s*\n',
                '',
                markdown,
                flags=re.MULTILINE,
            )

    front_matter = """---
title: "{title}"
---

""".format(title=notebook_title)

    markdown = front_matter + markdown

    # Write to MDX file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return output_file


def process_directory(
    directory,
    output_dir=None,
    image_dir=None,
    use_sphinx=False,
    remove_outputs=True,
    incremental=False,
    since_hours=24,
    use_git=False,
    base_branch="origin/master",
    specific_files=None,
):
    """Process all ipynb and md files in the specified directory and its subdirectories."""
    directory = Path(directory)
    converted_files = []

    if output_dir:
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    # Statistics counters
    total_ipynb = 0
    total_md = 0
    total_images = 0

    # Determine which files to process
    files_to_process = []

    if specific_files:
        # Process specific files provided
        files_to_process = [Path(f) for f in specific_files]
        print(f"Processing {len(files_to_process)} specific files")
    elif incremental:
        if use_git:
            # Use git to find changed files
            print(f"Looking for files changed compared to {base_branch}...")
            files_to_process = get_git_changed_files(directory, base_branch)
        else:
            # Use file modification time
            print(
                f"Looking for files changed in the last {since_hours} hours..."
            )
            files_to_process = get_changed_files(directory, since_hours)

        if not files_to_process:
            print("No changed files found.")
            return converted_files

        print(f"Found {len(files_to_process)} changed files:")
        for f in files_to_process:
            print(f"  - {f}")
    else:
        # Process all files (original behavior)
        print("Processing all files in directory...")
        for root, _dirs, files in os.walk(directory):
            root_path = Path(root)
            for file in files:
                if file.endswith(('.ipynb', '.md', '.mdx')):
                    files_to_process.append(root_path / file)

    # Process the determined files
    for file_path in files_to_process:
        # Determine the group for this file
        group_name = smart_detect_group_from_path(file_path, directory)

        # Create output directory structure
        if output_dir:
            # Create group-specific output directory
            if 'cookbooks' in str(file_path):
                current_output_dir = output_dir / "cookbooks" / group_name
            else:
                current_output_dir = output_dir / group_name
            os.makedirs(current_output_dir, exist_ok=True)
        else:
            current_output_dir = None

        # Process the file
        try:
            if file_path.suffix == '.ipynb':
                output_file = convert_ipynb_to_mdx(
                    file_path,
                    current_output_dir,
                    None,  # No longer use image_dir
                    directory,
                    remove_outputs,
                )
                converted_files.append((file_path, output_file))
                total_ipynb += 1
                print(f"  Converted IPYNB: {file_path.name} -> {output_file}")
            elif file_path.suffix == '.md':
                output_file = convert_md_to_mdx(
                    file_path,
                    current_output_dir,
                    None,  # No longer use image_dir
                    directory,
                )
                converted_files.append((file_path, output_file))
                total_md += 1
                print(f"  Converted MD: {file_path.name} -> {output_file}")
            elif file_path.suffix == '.mdx':
                # If an explicit output directory is provided and differs from the current
                # file location, copy the mdx file to the expected output location to keep
                # folder structures in sync. Otherwise, just reference the existing file.
                if (
                    current_output_dir
                    and file_path.parent != current_output_dir
                ):
                    dest_path = current_output_dir / file_path.name
                    try:
                        import shutil

                        shutil.copy2(file_path, dest_path)
                        output_file = dest_path
                    except Exception as copy_err:
                        print(
                            f"Error copying MDX file {file_path} -> {dest_path}: {copy_err}"
                        )
                        output_file = file_path  # Fallback to original path
                else:
                    output_file = file_path

                converted_files.append((file_path, output_file))
                print(f"  Detected modified MDX: {file_path.name}")

                # Reverse sync: copy the modified MDX back to the corresponding
                # source docs directory (docs/...) as a .md file so changes made
                # in Mintlify output become the new canonical docs source.
                try:
                    if 'mintlify' in file_path.parts:
                        mintlify_idx = list(file_path.parts).index('mintlify')
                        rel_parts = file_path.parts[mintlify_idx + 1 :]

                        dest_md_path = (
                            Path('docs')
                            .joinpath(*rel_parts)
                            .with_suffix('.md')
                        )
                        dest_md_path.parent.mkdir(parents=True, exist_ok=True)

                        import shutil

                        shutil.copy2(file_path, dest_md_path)
                        print(f"    ↳ Synced MDX back to {dest_md_path}")
                except Exception as sync_err:
                    print(
                        f"Warning: failed to sync MDX back to docs folder: {sync_err}"
                    )
        except Exception as e:
            print(f"Error converting {file_path}: {e}")

    # Count images in output directory
    if output_dir:
        for _root, _dirs, files in os.walk(output_dir):
            if "images" in _root:
                total_images += len(
                    [
                        f
                        for f in files
                        if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))
                    ]
                )

    print("Statistics:")
    print(f"- IPYNB files: {total_ipynb}")
    print(f"- MD files: {total_md}")
    print(f"- Extracted images: {total_images}")

    return converted_files


def generate_navigation_from_converted_files(
    converted_files, input_root, relative_path_prefix=""
):
    """
    Generate navigation structure for docs.json based on actually converted files.
    """
    # Define group mapping and order
    group_mapping = {
        'basic_concepts': 'Basic Concepts',
        'advanced_features': 'Advanced Features',
        'applications': 'Applications',
        'data_generation': 'Data Generation',
        'data_processing': 'Data Processing',
        'loong': 'Loong',
        'multi_agent_society': 'Multi Agent Society',
        'mcp': 'MCP',
    }

    # Group order
    group_order = [
        'basic_concepts',
        'advanced_features',
        'applications',
        'data_generation',
        'data_processing',
        'loong',
        'multi_agent_society',
        'mcp',
    ]

    # Collect converted files organized by group
    groups = defaultdict(list)
    input_root = Path(input_root)

    for source_file, output_file in converted_files:
        # Determine the group for this file
        group_name = smart_detect_group_from_path(source_file, input_root)

        # Create relative path for docs.json
        output_path = Path(output_file)

        # Extract the relative path from the output file
        # Assuming output structure is: output_dir/cookbooks/group_name/file.mdx
        if 'cookbooks' in output_path.parts:
            cookbooks_idx = list(output_path.parts).index('cookbooks')
            if cookbooks_idx + 2 < len(
                output_path.parts
            ):  # cookbooks/group/file.mdx
                group_from_path = output_path.parts[cookbooks_idx + 1]
                file_stem = output_path.stem
                rel_path = f"{relative_path_prefix}cookbooks/{group_from_path}/{file_stem}"
                groups[group_from_path].append(rel_path)

    # Generate navigation structure
    navigation_groups = []

    for group_key in group_order:
        if groups.get(group_key):
            # Sort files alphabetically
            sorted_pages = sorted(groups[group_key])

            group_config = {
                "group": group_mapping.get(
                    group_key, group_key.replace('_', ' ').title()
                ),
                "pages": sorted_pages,
            }
            navigation_groups.append(group_config)

    # Also check for any additional groups not in the predefined order
    for group_name in groups:
        if group_name not in group_order and groups[group_name]:
            sorted_pages = sorted(groups[group_name])
            group_config = {
                "group": group_mapping.get(
                    group_name, group_name.replace('_', ' ').title()
                ),
                "pages": sorted_pages,
            }
            navigation_groups.append(group_config)

    return navigation_groups


def update_docs_json(
    docs_json_path,
    converted_files,
    input_root,
    relative_path_prefix="",
    incremental=False,
):
    """
    Update docs.json file with newly converted files.
    In incremental mode, merge new entries with existing ones.
    """
    docs_json_path = Path(docs_json_path)

    if not docs_json_path.exists():
        print(f"Warning: docs.json not found at {docs_json_path}")
        return False

    try:
        # Read current docs.json
        with open(docs_json_path, 'r', encoding='utf-8') as f:
            docs_config = json.load(f)

        # Generate new navigation for converted files only
        new_cookbooks_nav = generate_navigation_from_converted_files(
            converted_files, input_root, relative_path_prefix
        )

        if not new_cookbooks_nav:
            print("No cookbooks navigation to update")
            return False

        # Find and update the Cookbooks section in navigation
        updated = False
        for tab in docs_config.get("navigation", {}).get("tabs", []):
            if tab.get("tab") == "Documentation":
                for group in tab.get("groups", []):
                    if group.get("group") == "Cookbooks":
                        if incremental:
                            # In incremental mode, merge with existing navigation
                            existing_nav = group.get("pages", [])
                            merged_nav = merge_navigation_groups(
                                existing_nav, new_cookbooks_nav
                            )
                            group["pages"] = merged_nav
                            print(
                                f"Merged cookbooks navigation: {len(merged_nav)} total groups"
                            )
                        else:
                            # In full mode, replace the entire navigation
                            group["pages"] = new_cookbooks_nav
                            print(
                                f"Replaced cookbooks navigation with {len(new_cookbooks_nav)} groups"
                            )
                        updated = True
                        break
                if updated:
                    break

        if not updated:
            print("Could not find Cookbooks section in docs.json to update")
            return False

        # Write updated docs.json
        with open(docs_json_path, 'w', encoding='utf-8') as f:
            json.dump(docs_config, f, indent=2, ensure_ascii=False)

        print(f"Successfully updated {docs_json_path}")
        return True

    except Exception as e:
        print(f"Error updating docs.json: {e}")
        return False


def merge_navigation_groups(existing_nav, new_nav):
    """
    Merge new navigation groups with existing ones.
    Updates existing groups and adds new ones.
    """
    # Convert existing navigation to a dict for easier manipulation
    existing_groups = {}
    if isinstance(existing_nav, list):
        for item in existing_nav:
            if isinstance(item, dict) and "group" in item:
                existing_groups[item["group"]] = set(item.get("pages", []))

    # Merge new navigation
    for new_group in new_nav:
        group_name = new_group["group"]
        new_pages = set(new_group.get("pages", []))

        if group_name in existing_groups:
            # Merge pages for existing group
            existing_groups[group_name].update(new_pages)
        else:
            # Add new group
            existing_groups[group_name] = new_pages

    # Convert back to the expected format
    merged_nav = []
    for group_name, pages in existing_groups.items():
        merged_nav.append({"group": group_name, "pages": sorted(pages)})

    # Sort groups by the predefined order
    group_order = [
        'Basic Concepts',
        'Advanced Features',
        'Applications',
        'Data Generation',
        'Data Processing',
        'Loong',
        'Multi Agent Society',
        'MCP',
    ]

    def get_group_order(group):
        try:
            return group_order.index(group["group"])
        except ValueError:
            return len(group_order)  # Put unknown groups at the end

    merged_nav.sort(key=get_group_order)

    return merged_nav


def get_changed_files(directory, since_hours=24, file_extensions=None):
    """Get recently modified files in the directory"""
    if file_extensions is None:
        file_extensions = ['.ipynb', '.md', '.mdx']

    changed_files = []
    directory = Path(directory)

    # Calculate time threshold
    time_threshold = time.time() - (since_hours * 3600)

    # Traverse all files in the directory
    for root, _dirs, files in os.walk(directory):
        for file in files:
            file_path = Path(root) / file

            # Check if file has the right extension
            if any(file.endswith(ext) for ext in file_extensions):
                # Check file modification time
                if file_path.stat().st_mtime > time_threshold:
                    changed_files.append(file_path)

    return sorted(changed_files)


def get_git_changed_files(
    directory, base_branch="origin/master", file_extensions=None
):
    """Get files changed in git compared to base branch"""
    if file_extensions is None:
        file_extensions = ['.ipynb', '.md', '.mdx']

    try:
        # Find the git repository root
        git_root_result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            cwd=directory,
        )

        if git_root_result.returncode != 0:
            print(f"Failed to find git root: {git_root_result.stderr}")
            return []

        git_root = Path(git_root_result.stdout.strip())

        # Get list of changed files from git (run from git root)
        result = subprocess.run(
            ['git', 'diff', '--name-only', base_branch, 'HEAD'],
            capture_output=True,
            text=True,
            cwd=git_root,
        )

        if result.returncode != 0:
            print(f"Git command failed: {result.stderr}")
            return []

        changed_files = []
        directory = Path(directory).resolve()  # Convert to absolute path

        for file_path in result.stdout.strip().split('\n'):
            if file_path:  # Skip empty lines
                # file_path is relative to git root
                full_path = git_root / file_path

                # Check if file is under the target directory and has the right extension
                try:
                    # Check if the file is under our target directory
                    full_path.resolve().relative_to(directory)

                    # Check if file exists and has the right extension
                    if full_path.exists() and any(
                        file_path.endswith(ext) for ext in file_extensions
                    ):
                        changed_files.append(full_path)
                except ValueError:
                    # File is not under target directory, skip it
                    continue

        return sorted(changed_files)

    except Exception as e:
        print(f"Error getting git changed files: {e}")
        return []


def smart_detect_group_from_path(file_path, input_root):
    """Intelligently detect the group name from file path"""
    file_path = Path(file_path)
    input_root = Path(input_root)

    try:
        # Get relative path from input root
        rel_path = file_path.relative_to(input_root)
        path_parts = rel_path.parts

        # Look for cookbooks in the path
        if 'cookbooks' in path_parts:
            cookbooks_idx = list(path_parts).index('cookbooks')
            if cookbooks_idx + 1 < len(path_parts):
                return path_parts[cookbooks_idx + 1]

        # If no cookbooks directory, preserve the directory structure
        if len(path_parts) > 1:
            # For files in subdirectories, use the immediate parent directory name
            # This preserves the original directory structure
            return path_parts[-2]  # Use the parent directory of the file

        # For files directly in the input root, use the input root's name
        return input_root.name

    except ValueError:
        # File is not under input_root, use parent directory name
        return file_path.parent.name


def main():
    parser = argparse.ArgumentParser(
        description='Convert IPYNB and MD files to MDX format'
    )
    parser.add_argument(
        '--input',
        '-i',
        default='docs/cookbooks',
        help='Input directory path, default is docs/cookbooks',
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output directory path; if not specified, original files will be overwritten',
    )
    parser.add_argument(
        '--images',
        '-img',
        help='Image output directory path; if not specified, will be stored in output/images',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true', help='Show detailed logs'
    )
    parser.add_argument(
        '--update-docs-json',
        '-u',
        help='Path to docs.json file to update with new navigation structure',
    )
    parser.add_argument(
        '--docs-path-prefix',
        '-p',
        default='',
        help='Path prefix for docs.json navigation entries (e.g., "docs/")',
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Only process files that have been changed recently',
    )
    parser.add_argument(
        '--since-hours',
        type=int,
        default=24,
        help='Hours to look back for changed files (used with --incremental)',
    )
    parser.add_argument(
        '--use-git',
        action='store_true',
        help='Use git to detect changed files instead of file modification time',
    )
    parser.add_argument(
        '--base-branch',
        default='origin/master',
        help='Base branch for git comparison (default: origin/master)',
    )
    parser.add_argument(
        '--files',
        nargs='*',
        help='Specific files to process (overrides incremental mode)',
    )

    args = parser.parse_args()

    print(f"Starting to process directory: {args.input}")

    # Determine processing mode
    if args.files:
        print(f"Processing {len(args.files)} specific files")
    elif args.incremental:
        if args.use_git:
            print(
                f"Incremental mode: using git to find changes compared to {args.base_branch}"
            )
        else:
            print(
                f"Incremental mode: processing files changed in the last {args.since_hours} hours"
            )
    else:
        print("Full mode: processing all files")

    converted_files = process_directory(
        args.input,
        args.output,
        args.images,
        remove_outputs=True,
        incremental=args.incremental,
        since_hours=args.since_hours,
        use_git=args.use_git,
        base_branch=args.base_branch,
        specific_files=args.files,
    )

    print(f"Conversion completed, processed {len(converted_files)} files")

    if args.verbose:
        print("Conversion details:")
        for source, dest in converted_files:
            print(f"{source} -> {dest}")

    # Update docs.json if requested
    if args.update_docs_json and args.output and converted_files:
        print("\nUpdating docs.json...")
        success = update_docs_json(
            args.update_docs_json,
            converted_files,
            args.input,
            args.docs_path_prefix,
            incremental=args.incremental,
        )
        if success:
            print("docs.json update completed successfully")
        else:
            print("docs.json update failed")
    elif converted_files and args.update_docs_json and not args.output:
        print(
            "\nNote: docs.json update skipped because no output directory was specified"
        )
    elif converted_files and not args.update_docs_json:
        print(
            "\nNote: docs.json update skipped (use --update-docs-json to enable)"
        )
    elif not converted_files and args.update_docs_json:
        print(
            "\nNote: docs.json update skipped because no files were converted"
        )

    return len(converted_files)


if __name__ == "__main__":
    main()
