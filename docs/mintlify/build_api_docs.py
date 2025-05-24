#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import glob
import importlib
import re
import time
from pathlib import Path
import argparse
from collections import defaultdict

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
    "extractors": "Extractors"
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
    "personas"
]

def create_config_file(output_path="pydoc-markdown.yml"):
    """Create pydoc-markdown configuration file"""
    config = """loader:
  type: python
  search_path: ["."]

renderer:
  type: markdown
  render_toc: false
  descriptive_class_title: true
  classifiers_at_top: false
  render_module_header: false
  insert_header_anchors: true
  use_fixed_header_levels: true
  header_level_by_type:
    Module: 1
    Class: 2
    Function: 3
    Method: 3
    ClassMethod: 3
    StaticMethod: 3
    Property: 3
  add_method_class_prefix: false
  add_member_class_prefix: false
  signature_with_short_description: true

processors:
  - type: smart
  - type: filter
    documented_only: false
  - type: crossref
"""
    with open(output_path, "w") as f:
        f.write(config)
    return output_path

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
                    rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(package_path))
                    # Convert to module name
                    module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                    modules.append(module_name)
            
            # Handle subpackages
            for dir_name in dirs:
                if os.path.isfile(os.path.join(root, dir_name, "__init__.py")):
                    # Calculate relative path of the subpackage
                    rel_path = os.path.relpath(os.path.join(root, dir_name), os.path.dirname(package_path))
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
        for root, dirs, files in os.walk(package_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    # Check file modification time
                    if os.path.getmtime(file_path) > time_threshold:
                        if file == "__init__.py":
                            # Handle package
                            rel_path = os.path.relpath(root, os.path.dirname(package_path))
                            module_name = rel_path.replace(os.sep, ".")
                            changed_modules.append(module_name)
                        else:
                            # Handle module
                            rel_path = os.path.relpath(file_path, os.path.dirname(package_path))
                            module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                            changed_modules.append(module_name)
    
    except ImportError as e:
        print(f"Error importing {package_name}: {e}")
    
    return sorted(list(set(changed_modules)))

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

def generate_mdx_docs(module_name, output_dir):
    """Generate MDX documentation for the specified module"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Output file path
    output_file = os.path.join(output_dir, f"{module_name}.mdx")
    
    # Use pydoc-markdown to generate documentation
    try:
        result = subprocess.run(
            ["pydoc-markdown", "-I", ".", "-m", module_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        content = result.stdout
        
        # Check if content is substantial enough
        if not is_content_substantial(content):
            print(f"    Skipped {module_name} (insufficient content)")
            return None
        
        # Write output to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error generating docs for {module_name}: {e}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return None

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
        for i, part in enumerate(parts[:-1]):  # Exclude the last part, which is the file name
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
    
    # First add top-level camel module
    if "camel" in [Path(p).stem.split('.')[-1] for p in module_tree["pages"]]:
        navigation.append("reference/camel")
    
    # Add submodules in custom order
    for module_name in MODULE_ORDER:
        if module_name in module_tree["submodules"]:
            submodule = module_tree["submodules"][module_name]
            
            # Get pretty display name for submodule
            display_name = get_module_display_name(module_name)
            
            # Create navigation group
            nav_group = {
                "group": display_name,
                "pages": []
            }
            
            # Add direct pages for this module
            if "pages" in submodule:
                nav_group["pages"].extend(sorted(submodule["pages"]))
            
            # Recursively handle submodules
            if "submodules" in submodule and submodule["submodules"]:
                for sub_name, sub_data in sorted(submodule["submodules"].items()):
                    if "pages" in sub_data and sub_data["pages"]:
                        # Directly flatten submodule pages
                        nav_group["pages"].extend(sorted(sub_data["pages"]))
            
            # Only add group if it has pages
            if nav_group["pages"]:
                navigation.append(nav_group)
    
    return navigation

def update_mint_json(mint_json_path, navigation):
    """Update the API Reference navigation section in mint.json file"""
    if not Path(mint_json_path).exists():
        print(f"Error: {mint_json_path} not found")
        return False
    
    with open(mint_json_path, "r", encoding="utf-8") as f:
        mint_data = json.load(f)
    
    # Find API Reference tab and update its groups
    tabs = mint_data.get("navigation", {}).get("tabs", [])
    for tab in tabs:
        if tab.get("tab") == "API Reference":
            tab["groups"] = navigation
            break
    
    # Save updated mint.json
    with open(mint_json_path, "w", encoding="utf-8") as f:
        json.dump(mint_data, f, indent=2, ensure_ascii=False)
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Generate API documentation and update mint.json configuration")
    parser.add_argument("--output_dir", type=str, default="docs/mintlify/reference",
                       help="Output directory for MDX files")
    parser.add_argument("--mint_json", type=str, default="docs/mintlify/mint.json",
                       help="Path to mint.json file")
    parser.add_argument("--package", type=str, default="camel",
                       help="Package name to generate documentation for")
    parser.add_argument("--clean", action="store_true",
                       help="Clean output directory before generating new files")
    parser.add_argument("--skip_generation", action="store_true",
                       help="Skip API documentation generation, only update mint.json")
    parser.add_argument("--incremental", action="store_true",
                       help="Only process modules that have been changed recently")
    parser.add_argument("--since_hours", type=int, default=24,
                       help="Hours to look back for changed files (used with --incremental)")
    args = parser.parse_args()
    
    if not args.skip_generation:
        # Check if pydoc-markdown is installed
        try:
            subprocess.run(["pydoc-markdown", "--version"], 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: pydoc-markdown is not installed. Please install it with:")
            print("  pip install pydoc-markdown")
            sys.exit(1)
        
        # Create configuration file
        config_file = create_config_file()
        
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Clean output directory (if needed)
        if args.clean:
            print(f"Cleaning output directory: {args.output_dir}")
            for file in glob.glob(os.path.join(args.output_dir, "*.mdx")):
                os.remove(file)
        
        # Get modules to process
        if args.incremental:
            print(f"Looking for modules changed in the last {args.since_hours} hours...")
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
        generated_count = 0
        skipped_count = 0
        
        for i, module in enumerate(modules):
            print(f"  [{i+1}/{len(modules)}] Processing {module}...")
            output_file = generate_mdx_docs(module, args.output_dir)
            if output_file:
                print(f"    Generated {os.path.basename(output_file)}")
                generated_count += 1
            else:
                skipped_count += 1
        
        # Clean up configuration file
        if os.path.exists(config_file):
            os.remove(config_file)
        
        print(f"\nGenerated: {generated_count} files, Skipped: {skipped_count} files")
    
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
    if update_mint_json(args.mint_json, navigation):
        print(f"Updated {args.mint_json} with {len(navigation)} navigation groups")
    
    # Print navigation structure summary
    print("\nNavigation structure summary:")
    for item in navigation:
        if isinstance(item, str):
            print(f"- {item}")
        else:
            print(f"- Group: {item['group']} ({len(item['pages'])} pages)")
    
    print(f"\nAPI documentation build completed successfully!")
    print(f"Documentation files: {args.output_dir}")
    print(f"Configuration file: {args.mint_json}")
    
    if not args.skip_generation:
        print("\nTo preview your Mintlify documentation, run:")
        print("  cd docs/mintlify && npx mintlify dev")

if __name__ == "__main__":
    main() 