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

"""
SVN Toolkit 示例

这个示例演示了如何使用 SVNToolkit 与 SVN 仓库交互，
展示了初始化、获取信息、分支管理等基本功能。

使用说明：
1. 确保已在 .env 文件中配置了 SVN_USERNAME、SVN_PASSWORD 和 SVN_BASE_URL
2. 或使用示例中的模拟配置进行测试
"""

import os
import logging
import tempfile
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入SVN工具包
try:
    from camel.toolkits.svn_toolkit import SVNToolkit
    SVN_TOOLKIT_AVAILABLE = True
    logger.info("SVNToolkit 模块已加载")
except ImportError as e:
    SVN_TOOLKIT_AVAILABLE = False
    logger.error(f"无法导入 SVNToolkit: {str(e)}")

# 加载环境变量
logger.info("加载环境变量...")
load_dotenv()

# 导入SVN工具包
from camel.toolkits.svn_toolkit import SVNToolkit

def main():
    """
    SVNToolkit 功能展示主函数
    """
    try:
        # 检查SVN工具包是否可用
        if not SVN_TOOLKIT_AVAILABLE:
            logger.error("导入 SVNToolkit 失败，请确保已安装必要的依赖")
            logger.info("您可以通过安装 camel 包来获取SVN工具包功能")
            return
        
        logger.info("成功导入 SVN 工具包")
        
        # 从环境变量获取 SVN 配置
        svn_username = os.getenv('SVN_USERNAME')
        svn_password = os.getenv('SVN_PASSWORD')
        
        # 初始化 SVNToolkit
        logger.info("初始化 SVNToolkit...")
        try:
            st = SVNToolkit(username=svn_username, password=svn_password)
            logger.info("SVNToolkit 初始化成功")
            
            # 示例1: 列出工具包提供的所有工具
            logger.info("\n=== 示例1: 列出工具包提供的所有工具 ===")
            try:
                tools = st.get_tools()
                logger.info(f"SVNToolkit 提供的工具 ({len(tools)} 个):")
                for i, tool in enumerate(tools, 1):
                    # 尝试多种方式获取工具名称
                    tool_name = str(tool)
                    
                    # 方法1: 检查是否有_function属性(可能包含原始函数)
                    if hasattr(tool, '_function') and tool._function:
                        if hasattr(tool._function, '__name__'):
                            tool_name = tool._function.__name__
                    # 方法2: 检查是否有func属性
                    elif hasattr(tool, 'func') and tool.func:
                        if hasattr(tool.func, '__name__'):
                            tool_name = tool.func.__name__
                    # 方法3: 尝试从对象字符串中解析函数名
                    elif 'FunctionTool' in str(tool):
                        # 这是一个后备方案，从FunctionTool对象的字符串表示中提取有意义的信息
                        # 如果是其他类型的工具，可能需要不同的处理方式
                        tool_name = f"FunctionTool-{i}"
                    
                    logger.info(f"{i}. {tool_name}")
            except Exception as e:
                logger.warning(f"获取工具列表时出错: {str(e)}")
                # 手动列出主要功能
                logger.info("\nSVNToolkit 主要功能:")
                main_features = [
                    "svn_copy: 创建分支或标签",
                    "svn_list_branches: 列出仓库中的分支",
                    "svn_list_tags: 列出仓库中的标签",
                    "svn_propget: 获取属性值",
                    "svn_propset: 设置属性值",
                    "svn_proplist: 列出属性",
                    "svn_propdel: 删除属性",
                    "svn_resolved: 标记冲突已解决",
                    "svn_revert: 撤销修改"
                ]
                for feature in main_features:
                    logger.info(f"- {feature}")
        except Exception as e:
            logger.error(f"SVNToolkit 初始化失败: {str(e)}")
            return
        
        # 从环境变量获取SVN仓库URL
        # 从.env文件中读取SVN_BASE_URL配置
        example_svn_url = os.getenv('SVN_BASE_URL')
        # 添加日志显示实际读取到的环境变量值
        logger.info(f"从环境变量读取到的SVN_BASE_URL: {example_svn_url}")
        if not example_svn_url:
            example_svn_url = "https://svn.example.com/repos/project"  # 默认值，仅作为示例
            logger.info(f"未找到环境变量，使用默认值: {example_svn_url}")
        
        logger.info("\n=== SVN Toolkit 功能介绍 ===")
        logger.info("SVNToolkit 提供以下主要功能:")
        logger.info("1. 仓库管理: 获取仓库信息、创建仓库")
        logger.info("2. 分支操作: 创建、列出分支")
        logger.info("3. 标签管理: 创建、列出标签")
        logger.info("4. 文件操作: 检出、更新、提交文件")
        logger.info("5. 属性管理: 获取、设置、列出、删除属性")
        logger.info("6. 冲突解决: 标记冲突已解决、撤销修改")
        
        logger.info("\n=== SVN Toolkit 主要功能用法 ===")
        logger.info("1. svn_copy: 创建分支或标签")
        logger.info("   用法: svn_copy(src_path, dest_path, message='创建分支/标签')")
        logger.info("2. svn_list_branches: 列出仓库中的分支")
        logger.info("   用法: svn_list_branches(repo_url)")
        logger.info("3. svn_list_tags: 列出仓库中的标签")
        logger.info("   用法: svn_list_tags(repo_url)")
        logger.info("4. svn_propget: 获取属性值")
        logger.info("   用法: svn_propget(prop_name, path)")
        logger.info("5. svn_propset: 设置属性值")
        logger.info("   用法: svn_propset(prop_name, prop_value, path)")
        logger.info("6. svn_proplist: 列出属性")
        logger.info("   用法: svn_proplist(path)")
        logger.info("7. svn_propdel: 删除属性")
        logger.info("   用法: svn_propdel(prop_name, path)")
        logger.info("8. svn_resolved: 标记冲突已解决")
        logger.info("   用法: svn_resolved(path)")
        logger.info("9. svn_revert: 撤销修改")
        logger.info("   用法: svn_revert(path)")
        
        # 创建临时目录用于示例操作
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"\n创建临时目录: {temp_dir}")
            
            # 模拟一些分支和标签数据，用于演示
            sample_branches = ["feature/new-ui", "feature/api-v2", "bugfix/login-issue"]
            sample_tags = ["release/v1.0.0", "release/v1.1.0", "release/v1.2.0"]
            
            logger.info("\n=== SVNToolkit 使用示例代码 ===")
            
            # 示例1: 创建分支
            logger.info("\n示例1: 创建分支")
            svn_base_url = os.getenv('SVN_BASE_URL', "https://svn.example.com/repos/project")
            logger.info(f"示例代码将使用URL: {svn_base_url}")
            
            # 构建完整路径
            src_path = f"{svn_base_url}/trunk"
            dest_path = f"{svn_base_url}/branches/new-feature"
            
            logger.info(f"源路径: {src_path}")
            logger.info(f"目标路径: {dest_path}")
            
            example_code = f'''
            # 创建分支的示例代码
            try:
                st.svn_copy(
                    src_path="{src_path}",
                    dest_path="{dest_path}",
                    message="创建新功能分支"
                )
                logger.info("分支创建成功")
            except Exception as e:
                logger.warning(f"创建分支时出错: {{{{str(e)}}}}")
            '''
            logger.info(example_code)
            
            # 示例2: 列出分支
            logger.info("\n示例2: 列出分支")
            logger.info("由于这是演示环境，我们显示一些模拟的分支列表:")
            logger.info(f"找到 {len(sample_branches)} 个分支")
            for branch in sample_branches:
                logger.info(f"  - {branch}")
            
            example_code = f'''
            # 列出分支的示例代码
            try:
                branches = st.svn_list_branches(repo_url="{svn_base_url}")
                logger.info(f"找到 {{{{len(branches)}}}} 个分支")
                for branch in branches:
                    logger.info(f"  - {{{{branch}}}}")
            except Exception as e:
                logger.warning(f"列出分支时出错: {{{{str(e)}}}}")
            '''
            logger.info(example_code)
            
            # 示例3: 列出标签
            logger.info("\n示例3: 列出标签")
            logger.info("由于这是演示环境，我们显示一些模拟的标签列表:")
            logger.info(f"找到 {len(sample_tags)} 个标签")
            for tag in sample_tags:
                logger.info(f"  - {tag}")
            
            example_code = f'''
            # 列出标签的示例代码
            try:
                tags = st.svn_list_tags(repo_url="{svn_base_url}")
                logger.info(f"找到 {{{{len(tags)}}}} 个标签")
                for tag in tags:
                    logger.info(f"  - {{{{tag}}}}")
            except Exception as e:
                logger.warning(f"列出标签时出错: {{{{str(e)}}}}")
            '''
            logger.info(example_code)
        
        logger.info("\n=== 使用说明 ===")
        logger.info("1. 请确保已在 .env 文件中正确配置了 SVN 相关环境变量")
        logger.info("2. 确保您的环境中已安装 SVN 命令行客户端")
        logger.info("3. 将示例代码中的 URL 替换为实际可访问的 SVN 仓库地址")
        logger.info("4. 在实际使用时，请根据您的需求修改示例代码")
    
    except Exception as ex:
        logger.error(f"示例执行过程中发生错误: {str(ex)}", exc_info=True)
    finally:
        logger.info("\nSVNToolkit 示例执行完成！")

if __name__ == "__main__":
    main()