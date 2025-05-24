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

# 模块名到显示名称的映射
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

# 自定义顺序，这决定了顶级模块的显示顺序
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
    """创建pydoc-markdown配置文件"""
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
    """获取模块的美观显示名称"""
    if module_name in MODULE_NAME_DISPLAY:
        return MODULE_NAME_DISPLAY[module_name]
    # 如果没有映射，则将snake_case转换为title case
    return module_name.replace('_', ' ').title()

def get_all_modules(package_name="camel", recursive=True):
    """获取包中的所有模块"""
    modules = []
    
    try:
        # 导入主包
        package = importlib.import_module(package_name)
        modules.append(package_name)
        
        # 获取包的路径
        package_path = os.path.dirname(package.__file__)
        
        # 遍历包中的所有Python文件
        for root, dirs, files in os.walk(package_path):
            if not recursive and root != package_path:
                continue
                
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    # 计算模块的相对路径
                    rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(package_path))
                    # 转换为模块名称
                    module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                    modules.append(module_name)
            
            # 处理子包
            for dir_name in dirs:
                if os.path.isfile(os.path.join(root, dir_name, "__init__.py")):
                    # 计算子包的相对路径
                    rel_path = os.path.relpath(os.path.join(root, dir_name), os.path.dirname(package_path))
                    # 转换为包名称
                    subpackage_name = rel_path.replace(os.sep, ".")
                    modules.append(subpackage_name)
    
    except ImportError as e:
        print(f"Error importing {package_name}: {e}")
    
    return sorted(modules)

def get_changed_modules(package_name="camel", since_hours=24):
    """获取最近修改的模块（用于增量更新）"""
    changed_modules = []
    
    try:
        # 导入主包
        package = importlib.import_module(package_name)
        package_path = os.path.dirname(package.__file__)
        
        # 计算时间阈值
        time_threshold = time.time() - (since_hours * 3600)
        
        # 遍历包中的所有Python文件
        for root, dirs, files in os.walk(package_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    # 检查文件修改时间
                    if os.path.getmtime(file_path) > time_threshold:
                        if file == "__init__.py":
                            # 处理包
                            rel_path = os.path.relpath(root, os.path.dirname(package_path))
                            module_name = rel_path.replace(os.sep, ".")
                            changed_modules.append(module_name)
                        else:
                            # 处理模块
                            rel_path = os.path.relpath(file_path, os.path.dirname(package_path))
                            module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                            changed_modules.append(module_name)
    
    except ImportError as e:
        print(f"Error importing {package_name}: {e}")
    
    return sorted(list(set(changed_modules)))

def clean_generated_mdx(content, module_name):
    """清理生成的MDX内容，移除不需要的模块标题和格式化"""
    lines = content.split('\n')
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 跳过模块标题行（形如 "# camel.agents.\_utils"）
        if line.startswith('# camel.') and '\\' in line:
            i += 1
            continue
        
        # 跳过空的锚点行后面紧跟的模块标题
        if line.startswith('<a id="camel.') and line.endswith('"></a>'):
            # 检查下一行是否为空行
            if i + 1 < len(lines) and lines[i + 1].strip() == '':
                # 检查下下行是否是对应的模块标题
                if i + 2 < len(lines) and lines[i + 2].startswith('# camel.'):
                    # 保留锚点，跳过空行和标题
                    cleaned_lines.append(line)
                    i += 3
                    continue
        
        cleaned_lines.append(line)
        i += 1
    
    # 移除开头的多余空行
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    
    # 确保文件以换行符结尾
    content = '\n'.join(cleaned_lines)
    if content and not content.endswith('\n'):
        content += '\n'
    
    return content

def is_content_substantial(content):
    """检查内容是否足够实质性，避免生成空文档"""
    if not content.strip():
        return False
    
    # 移除空行和常见的无用内容
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # 过滤掉只有标题的情况
    substantial_lines = []
    for line in lines:
        # 跳过标题行
        if line.startswith('#'):
            continue
        # 跳过只有模块ID的行
        if line.startswith('<a id='):
            continue
        # 跳过空的代码块
        if line in ['```', '```python']:
            continue
        substantial_lines.append(line)
    
    # 如果实质内容少于3行，认为不够实质性
    return len(substantial_lines) >= 3

def generate_mdx_docs(module_name, output_dir):
    """为指定模块生成MDX文档"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 输出文件路径
    output_file = os.path.join(output_dir, f"{module_name}.mdx")
    
    # 使用pydoc-markdown生成文档
    try:
        result = subprocess.run(
            ["pydoc-markdown", "-I", ".", "-m", module_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        content = result.stdout
        
        # 清理内容
        cleaned_content = clean_generated_mdx(content, module_name)
        
        # 检查清理后的内容是否足够实质性
        if not is_content_substantial(cleaned_content):
            print(f"    Skipped {module_name} (insufficient content)")
            return None
        
        # 将输出写入文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error generating docs for {module_name}: {e}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return None

def build_module_tree(mdx_files):
    """根据MDX文件名构建模块树"""
    # 创建新的子模块字典的工厂函数
    def new_module_dict():
        return {"pages": [], "submodules": defaultdict(new_module_dict)}
    
    # 使用嵌套的defaultdict构建树结构
    module_tree = new_module_dict()
    
    for file in mdx_files:
        # 从文件名获取模块路径
        module_path = file.stem  # 去掉.mdx后缀
        
        # 通常我们期望文件名是"camel.xxx.yyy"这样的格式
        if not module_path.startswith("camel."):
            # 如果不是camel模块，跳过
            continue
        
        # 分割模块路径
        parts = module_path.split('.')
        
        # 构建引用路径
        reference_path = f"reference/{module_path}"
        
        # 如果只是camel模块本身
        if len(parts) == 1:
            module_tree["pages"].append(reference_path)
            continue
        
        # 处理子模块
        current = module_tree
        for i, part in enumerate(parts[:-1]):  # 不包括最后一个部分，它是文件名
            if i == 0:  # camel根模块
                continue
                
            # 导航到子模块
            current = current["submodules"][part]
        
        # 确保pages列表存在
        if "pages" not in current:
            current["pages"] = []
        
        # 确保目录页（如camel.agents/camel.agents.mdx）出现在其子模块之前
        if parts[-1] == parts[-2]:
            current["pages"].insert(0, reference_path)
        else:
            current["pages"].append(reference_path)
    
    return module_tree

def convert_tree_to_navigation(module_tree):
    """将模块树转换为mint.json的navigation格式"""
    navigation = []
    
    # 首先添加顶级camel模块
    if "camel" in [Path(p).stem.split('.')[-1] for p in module_tree["pages"]]:
        navigation.append("reference/camel")
    
    # 按自定义顺序添加子模块
    for module_name in MODULE_ORDER:
        if module_name in module_tree["submodules"]:
            submodule = module_tree["submodules"][module_name]
            
            # 获取子模块的漂亮显示名称
            display_name = get_module_display_name(module_name)
            
            # 创建导航组
            nav_group = {
                "group": display_name,
                "pages": []
            }
            
            # 添加该模块的直接页面
            if "pages" in submodule:
                nav_group["pages"].extend(sorted(submodule["pages"]))
            
            # 递归处理子模块
            if "submodules" in submodule and submodule["submodules"]:
                for sub_name, sub_data in sorted(submodule["submodules"].items()):
                    if "pages" in sub_data and sub_data["pages"]:
                        # 直接扁平化子模块的页面
                        nav_group["pages"].extend(sorted(sub_data["pages"]))
            
            # 只有当有页面时才添加组
            if nav_group["pages"]:
                navigation.append(nav_group)
    
    return navigation

def update_mint_json(mint_json_path, navigation):
    """更新mint.json文件中的API Reference导航部分"""
    if not Path(mint_json_path).exists():
        print(f"Error: {mint_json_path} not found")
        return False
    
    with open(mint_json_path, "r", encoding="utf-8") as f:
        mint_data = json.load(f)
    
    # 找到API Reference tab并更新其groups
    tabs = mint_data.get("navigation", {}).get("tabs", [])
    for tab in tabs:
        if tab.get("tab") == "API Reference":
            tab["groups"] = navigation
            break
    
    # 保存更新后的mint.json
    with open(mint_json_path, "w", encoding="utf-8") as f:
        json.dump(mint_data, f, indent=2, ensure_ascii=False)
    
    return True

def clean_existing_mdx_files(output_dir):
    """清理现有的MDX文件，移除不需要的模块标题"""
    mdx_files = list(Path(output_dir).glob("*.mdx"))
    if not mdx_files:
        print(f"No MDX files found in {output_dir}")
        return 0
    
    cleaned_count = 0
    
    for i, file_path in enumerate(mdx_files):
        module_name = file_path.stem  # 获取不带扩展名的文件名作为模块名
        print(f"  [{i+1}/{len(mdx_files)}] Cleaning {file_path.name}...")
        
        try:
            # 读取现有内容
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
            
            # 应用清理
            cleaned_content = clean_generated_mdx(original_content, module_name)
            
            # 检查是否有变化
            if cleaned_content != original_content:
                # 写回清理后的内容
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                print(f"    ✓ Cleaned {file_path.name}")
                cleaned_count += 1
            else:
                print(f"    - No changes needed for {file_path.name}")
                
        except Exception as e:
            print(f"    ✗ Error cleaning {file_path.name}: {e}")
    
    return cleaned_count

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
    parser.add_argument("--clean_existing", action="store_true",
                       help="Clean existing MDX files without regenerating them")
    parser.add_argument("--skip_generation", action="store_true",
                       help="Skip API documentation generation, only update mint.json")
    parser.add_argument("--incremental", action="store_true",
                       help="Only process modules that have been changed recently")
    parser.add_argument("--since_hours", type=int, default=24,
                       help="Hours to look back for changed files (used with --incremental)")
    args = parser.parse_args()
    
    # 如果只是清理现有文件
    if args.clean_existing:
        print(f"Cleaning existing MDX files in {args.output_dir}...")
        cleaned_count = clean_existing_mdx_files(args.output_dir)
        print(f"\nCleaning completed: {cleaned_count} files were modified")
        return
    
    if not args.skip_generation:
        # 检查pydoc-markdown是否已安装
        try:
            subprocess.run(["pydoc-markdown", "--version"], 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: pydoc-markdown is not installed. Please install it with:")
            print("  pip install pydoc-markdown")
            sys.exit(1)
        
        # 创建配置文件
        config_file = create_config_file()
        
        # 创建输出目录
        os.makedirs(args.output_dir, exist_ok=True)
        
        # 清理输出目录（如有需要）
        if args.clean:
            print(f"Cleaning output directory: {args.output_dir}")
            for file in glob.glob(os.path.join(args.output_dir, "*.mdx")):
                os.remove(file)
        
        # 获取要处理的模块
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
        
        # 生成文档
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
        
        # 清理配置文件
        if os.path.exists(config_file):
            os.remove(config_file)
        
        print(f"\nGenerated: {generated_count} files, Skipped: {skipped_count} files")
    
    # 构建模块树和更新mint.json
    print("\nUpdating mint.json configuration...")
    
    # 获取生成的MDX文件
    mdx_files = list(Path(args.output_dir).glob("*.mdx"))
    if not mdx_files:
        print(f"No MDX files found in {args.output_dir}")
        return
    
    print(f"Found {len(mdx_files)} MDX files")
    
    # 构建模块树
    module_tree = build_module_tree(mdx_files)
    
    # 转换为navigation格式
    navigation = convert_tree_to_navigation(module_tree)
    
    # 更新mint.json
    if update_mint_json(args.mint_json, navigation):
        print(f"Updated {args.mint_json} with {len(navigation)} navigation groups")
    
    # 打印navigation结构摘要
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