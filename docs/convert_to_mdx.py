#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script is used to convert rst, md, and ipynb files in the docs/cookbooks directory to mdx format for migration to mintify.
"""

import os
import sys
import re
import json
import shutil
import subprocess
from pathlib import Path
import nbformat
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import Preprocessor
import argparse


class RemoveOutputPreprocessor(Preprocessor):
    """Preprocessor to remove output results from notebook code cells."""
    
    def preprocess_cell(self, cell, resources, index):
        """Process a single cell; if it is a code cell, remove the output."""
        if cell.cell_type == 'code':
            cell.outputs = []
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
    for i, part in enumerate(parts):
        # Check if the current part is already duplicated in the result
        duplicate = False
        for j in range(len(result)):
            if part == result[j] and part != 'images':  # Allow keeping the images directory
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


def convert_rst_with_sphinx(rst_file, output_dir, temp_dir=None):
    """Convert RST files to Markdown using Sphinx, then convert to MDX."""
    print(f"Using Sphinx to convert RST file: {rst_file}")
    
    # Create temporary directory
    if temp_dir is None:
        temp_dir = Path("temp_sphinx_build")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Copy RST file to temporary directory
    temp_rst = Path(temp_dir) / f"{Path(rst_file).name}"
    shutil.copy(rst_file, temp_rst)
    
    # Create conf.py file
    with open(Path(temp_dir) / "conf.py", "w") as f:
        f.write("""
project = 'Temp'
extensions = ['myst_parser']
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
""")
    
    # Create index.rst
    with open(Path(temp_dir) / "index.rst", "w") as f:
        f.write(f"""
Temp
====

.. toctree::
   :maxdepth: 2
   
   {Path(rst_file).stem}
""")
    
    # Run sphinx-build
    build_dir = Path(temp_dir) / "_build" / "markdown"
    os.makedirs(build_dir, exist_ok=True)
    
    try:
        subprocess.run([
            "sphinx-build", "-b", "markdown", str(temp_dir), str(build_dir)
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print(f"Warning: sphinx-build failed, will use basic conversion method")
        return convert_rst_to_mdx(rst_file, output_dir)
    except FileNotFoundError:
        print(f"Warning: sphinx-build command not found, will use basic conversion method")
        return convert_rst_to_mdx(rst_file, output_dir)
    
    # Find the generated markdown file
    md_file = build_dir / f"{Path(rst_file).stem}.md"
    if not md_file.exists():
        print(f"Warning: sphinx failed to generate markdown file, will use basic conversion method")
        return convert_rst_to_mdx(rst_file, output_dir)
    
    # Read markdown and convert to mdx
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # Create output file path
    if output_dir:
        output_file = Path(output_dir) / f"{Path(rst_file).stem}.mdx"
    else:
        output_file = Path(f"{rst_file.with_suffix('.mdx')}")
    
    # Remove style tags
    md_content = re.sub(r"<style[\s\S]*?</style>", "", md_content, flags=re.IGNORECASE)
    
    # Fix HTML tag closures
    md_content = fix_html_tags(md_content)
    
    # Add MDX front matter
    if not md_content.startswith('---'):
        front_matter = """---
title: "{title}"
---

""".format(title=Path(rst_file).stem.replace('_', ' ').title())
        md_content = front_matter + md_content
    
    # Write to MDX file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # Clean up temporary files
    if not Path(temp_dir).is_relative_to(Path.cwd() / "temp"):
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return output_file


def convert_rst_to_mdx(rst_file, output_dir=None):
    """Convert RST files to MDX format (alternative method when not using Sphinx)."""
    print(f"Converting RST file: {rst_file}")
    
    # Read RST file content
    with open(rst_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create output file path
    if output_dir:
        output_file = Path(output_dir) / f"{Path(rst_file).stem}.mdx"
    else:
        output_file = Path(f"{rst_file.with_suffix('.mdx')}")
    
    # Replace RST specific syntax with MDX syntax
    # Replace titles
    content = re.sub(r'(.*)\n=+\s*\n', r'# \1\n\n', content)
    content = re.sub(r'(.*)\n-+\s*\n', r'## \1\n\n', content)
    
    # Replace toctree
    content = re.sub(r'.. toctree::\s*\n\s*:maxdepth:\s*\d+\s*\n\n', '', content)
    
    # Replace raw html
    content = re.sub(r'.. raw:: html\s*\n\n(.*?)\n\n', r'\1\n\n', content, flags=re.DOTALL)
    
    # Handle links
    content = re.sub(r':doc:`(.*?)`', r'[\1](\1.mdx)', content)
    
    # Remove other RST specific directives
    content = re.sub(r'.. .*::', '', content)
    
    # Remove style tags
    content = re.sub(r"<style[\s\S]*?</style>", "", content, flags=re.IGNORECASE)
    
    # Fix HTML tag closures, but do not escape asterisks
    content = fix_html_tags(content)
    
    # Add MDX front matter
    front_matter = """---
title: "{title}"
---

""".format(title=Path(rst_file).stem.replace('_', ' ').title())
    
    content = front_matter + content
    
    # Write to MDX file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_file


def convert_md_to_mdx(md_file, output_dir=None, image_dir=None, input_root=None):
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
    
    # Create image output directory
    if image_dir:
        # Use relative paths from the input root to organize image directories
        if input_root:
            rel_path = Path(md_file).relative_to(input_root)
            parent_dir = rel_path.parent.name
            file_name = rel_path.stem
            image_output_dir = Path(image_dir) / parent_dir / file_name
        else:
            rel_path = Path(md_file).relative_to(Path(md_file).parts[0])
            parent_dir = '/'.join(rel_path.parts[1:-1]) if len(rel_path.parts) > 2 else rel_path.parts[-2] if len(rel_path.parts) > 1 else "images"
            image_output_dir = Path(image_dir) / parent_dir / Path(md_file).stem
    else:
        parent_dir = Path(md_file).parent.name
        image_output_dir = Path(output_file).parent / "images" / parent_dir / Path(md_file).stem
    
    # Ensure image output directory exists
    os.makedirs(image_output_dir, exist_ok=True)
    
    # Calculate relative image path
    rel_image_path = os.path.relpath(image_output_dir, os.path.dirname(output_file))
    rel_image_path = rel_image_path.replace('\\', '/')  # Windows path compatibility
    rel_image_path = fix_duplicate_paths(rel_image_path)  # Fix duplicate directory names
    
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
                print(f"  Extracted and saved image from Markdown: {image_name}")
                
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
                if not local_img_path.startswith('./') and not local_img_path.startswith('../'):
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
                print(f"  Extracted and saved image from HTML tag: {image_name}")
                
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
    content = re.sub(r"<style[\s\S]*?</style>", "", content, flags=re.IGNORECASE)
    
    # Fix HTML tag closures
    content = fix_html_tags(content)
    
    # Add debug information for saved images
    if images_saved:
        content += "\n\n<!-- Saved images:\n"
        for img_name, img_path in images_saved:
            clean_path = rel_image_path.replace('//', '/')  # Fix double slashes in path
            content += f"- {img_name}: {clean_path}/{img_name}\n"
        content += "-->\n"
    
    # Check if there is already front matter; if not, add it
    if not content.startswith('---'):
        front_matter = """---
title: "{title}"
---

""".format(title=Path(md_file).stem.replace('_', ' ').title())
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
    return content


def convert_ipynb_to_mdx(ipynb_file, output_dir=None, image_dir=None, input_root=None, remove_outputs=True):
    """Convert Jupyter Notebook to MDX format."""
    print(f"Converting IPYNB file: {ipynb_file}")
    
    # Read Jupyter Notebook
    with open(ipynb_file, 'r', encoding='utf-8') as f:
        notebook = nbformat.read(f, as_version=4)
    
    # Create output file path
    if output_dir:
        output_file = Path(output_dir) / f"{Path(ipynb_file).stem}.mdx"
        if image_dir:
            # Use relative paths from the input root to organize image directories
            if input_root:
                rel_path = Path(ipynb_file).relative_to(input_root)
                # Simplify path, keeping only the last two levels
                parent_dir = rel_path.parent.name
                notebook_name = rel_path.stem
                image_output_dir = Path(image_dir) / parent_dir / notebook_name
            else:
                # Compatibility with old processing method
                rel_path = Path(ipynb_file).relative_to(Path(ipynb_file).parts[0])
                notebook_dir = '/'.join(rel_path.parts[1:-1]) if len(rel_path.parts) > 2 else rel_path.parts[-2]
                image_output_dir = Path(image_dir) / notebook_dir / Path(ipynb_file).stem
        else:
            image_output_dir = Path(output_dir) / 'images' / Path(ipynb_file).parent.name / Path(ipynb_file).stem
    else:
        output_file = Path(f"{ipynb_file.with_suffix('.mdx')}")
        image_output_dir = Path(ipynb_file).parent / 'images' / Path(ipynb_file).stem
    
    # Ensure image output directory exists
    os.makedirs(image_output_dir, exist_ok=True)
    
    # Configure exporter; if outputs need to be removed, add preprocessor
    exporter = MarkdownExporter()
    if remove_outputs:
        # Create a preprocessor to remove code cell outputs
        exporter.register_preprocessor(RemoveOutputPreprocessor, enabled=True)
    
    # Use nbconvert to convert Notebook to Markdown
    markdown, resources = exporter.from_notebook_node(notebook)
    
    # Extract and save images
    images_saved = []
    if 'outputs' in resources and resources['outputs']:
        print(f"  Found {len(resources['outputs'])} image resources")
        for image_name, image_data in resources['outputs'].items():
            image_path = os.path.join(image_output_dir, image_name)
            with open(image_path, 'wb') as f:
                f.write(image_data)
            images_saved.append((image_name, image_path))
    
    # Calculate relative image path, ensuring no duplicate directory names
    rel_image_path = os.path.relpath(image_output_dir, os.path.dirname(output_file))
    rel_image_path = rel_image_path.replace('\\', '/')  # Windows path compatibility
    rel_image_path = fix_duplicate_paths(rel_image_path)  # Fix duplicate directory names
    
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
                print(f"  Extracted and saved base64 image from Notebook: {image_name}")
                
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
    markdown = re.sub(r'!\[(.*?)\]\((data:image.*?)\)', extract_base64_image_from_notebook, markdown)
    # Then process other images
    markdown = re.sub(r'!\[(.*?)\]\(((?!data:image).*?)\)', replace_image_path, markdown)
    
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
                print(f"  Extracted and saved base64 image from HTML tag: {image_name}")
                
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
    markdown = re.sub(r"<style[\s\S]*?</style>", "", markdown, flags=re.IGNORECASE)
    
    # Fix HTML tag closures
    markdown = fix_html_tags(markdown)
    
    # Standardize HTML code blocks
    markdown = standardize_html_blocks(markdown)
    
    # Add debug information for saved images
    if images_saved:
        markdown += "\n\n<!-- Saved images:\n"
        for img_name, img_path in images_saved:
            clean_path = rel_image_path.replace('//', '/')  # Fix double slashes in path
            markdown += f"- {img_name}: {clean_path}/{img_name}\n"
        markdown += "-->\n"
    
    # Add MDX front matter
    notebook_title = Path(ipynb_file).stem.replace('_', ' ').title()
    
    # Check if the first cell of the notebook is markdown and contains a title
    if notebook.cells and notebook.cells[0].cell_type == 'markdown':
        first_cell_content = notebook.cells[0].source
        title_match = re.search(r'^#\s+(.*?)$', first_cell_content, re.MULTILINE)
        if title_match:
            notebook_title = title_match.group(1)
    
    front_matter = """---
title: "{title}"
---

""".format(title=notebook_title)
    
    markdown = front_matter + markdown
    
    # Write to MDX file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return output_file


def process_directory(directory, output_dir=None, image_dir=None, use_sphinx=False, remove_outputs=True):
    """Process all ipynb files in the specified directory and its subdirectories."""
    directory = Path(directory)
    converted_files = []
    
    if output_dir:
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)
    
    if image_dir:
        image_dir = Path(image_dir)
        os.makedirs(image_dir, exist_ok=True)
    
    # Statistics counters
    total_ipynb = 0
    total_images = 0
    
    # Traverse the directory
    for root, dirs, files in os.walk(directory):
        root_path = Path(root)
        
        # Create corresponding output directory for each subdirectory
        if output_dir:
            relative_path = root_path.relative_to(directory)
            current_output_dir = output_dir / relative_path
            current_image_dir = image_dir / relative_path if image_dir else None
            os.makedirs(current_output_dir, exist_ok=True)
            if current_image_dir:
                os.makedirs(current_image_dir, exist_ok=True)
        else:
            current_output_dir = None
            current_image_dir = None
        
        # Process files
        for file in files:
            file_path = root_path / file
            
            if file.endswith('.ipynb'):
                try:
                    output_file = convert_ipynb_to_mdx(file_path, current_output_dir, current_image_dir, directory, remove_outputs)
                    converted_files.append((file_path, output_file))
                    total_ipynb += 1
                except Exception as e:
                    print(f"Error converting IPYNB file {file_path}: {e}")
    
    # Count the number of generated images
    if image_dir:
        for root, dirs, files in os.walk(image_dir):
            total_images += len([f for f in files if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))])
    
    print(f"Statistics:")
    print(f"- IPYNB files: {total_ipynb}")
    print(f"- Extracted images: {total_images}")
    
    return converted_files



def main():
    parser = argparse.ArgumentParser(description='Convert IPYNB files to MDX format')
    parser.add_argument('--input', '-i', default='docs/cookbooks', help='Input directory path, default is docs/cookbooks')
    parser.add_argument('--output', '-o', help='Output directory path; if not specified, original files will be overwritten')
    parser.add_argument('--images', '-img', help='Image output directory path; if not specified, will be stored in output/images')
    parser.add_argument('--keep-outputs', '-k', action='store_true', help='Keep output results of Jupyter Notebook code cells')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed logs')
    
    args = parser.parse_args()
    
    print(f"Starting to process directory: {args.input}")
    converted_files = process_directory(
        args.input, 
        args.output,
        args.images,
        remove_outputs=not args.keep_outputs
    )
    
    print(f"Conversion completed, processed {len(converted_files)} files")
    
    if args.verbose:
        print("Conversion details:")
        for source, dest in converted_files:
            print(f"{source} -> {dest}")


if __name__ == "__main__":
    main()