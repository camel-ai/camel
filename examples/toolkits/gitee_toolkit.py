"""
Gitee Toolkit 示例

这个示例演示了如何使用 GiteeToolkit 与 Gitee 平台交互，
展示了初始化、仓库信息获取、分支管理等基本功能。

使用说明：
1. 确保已在 .env 文件中配置了 GITEE_ACCESS_TOKEN
2. 或使用示例中的模拟配置进行测试
"""
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

import os
import logging
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入Gitee工具包
try:
    from camel.toolkits.gitee_toolkit import GiteeToolkit
    GITEE_TOOLKIT_AVAILABLE = True
    logger.info("GiteeToolkit 模块已加载")
except ImportError as e:
    GITEE_TOOLKIT_AVAILABLE = False
    logger.error(f"无法导入 GiteeToolkit: {str(e)}")

# 加载环境变量
logger.info("加载环境变量...")
load_dotenv()

def main():
    """
    GiteeToolkit 功能展示主函数
    """
    try:
        # 检查Gitee工具包是否可用
        if not GITEE_TOOLKIT_AVAILABLE:
            logger.error("导入 GiteeToolkit 失败，请确保已安装必要的依赖")
            logger.info("您可以通过安装 camel 包来获取Gitee工具包功能")
            return
        
        # 从环境变量获取 Gitee 访问令牌
        access_token = os.getenv('GITEE_ACCESS_TOKEN')
        if not access_token:
            logger.warning("未找到 GITEE_ACCESS_TOKEN 环境变量，使用默认初始化")
            logger.info("请在 .env 文件中设置 GITEE_ACCESS_TOKEN 以获得完整功能")
        
        # 初始化 GiteeToolkit
        logger.info("初始化 GiteeToolkit...")
        try:
            gt = GiteeToolkit(access_token=access_token)
            logger.info("GiteeToolkit 初始化成功")
            
            # 示例1: 列出工具包提供的所有工具
            logger.info("\n=== 示例1: 列出工具包提供的所有工具 ===")
            try:
                tools = gt.get_tools()
                logger.info(f"GiteeToolkit 提供的工具 ({len(tools)} 个):")
                for i, tool in enumerate(tools, 1):
                    # 尝试多种方式获取工具名称
                    tool_name = str(tool)
                    
                    # 方法1: 从方法对象中提取函数名
                    if hasattr(tool, '__name__'):
                        tool_name = tool.__name__
                    # 方法2: 从绑定方法的字符串表示中提取方法名
                    elif 'bound method' in str(tool):
                        # 从字符串格式: '<bound method GiteeToolkit.method_name of ...>' 提取
                        import re
                        match = re.search(r'GiteeToolkit\.(\w+)', str(tool))
                        if match:
                            tool_name = match.group(1)
                    
                    logger.info(f"{i}. {tool_name}")
            except Exception as e:
                logger.warning(f"获取工具列表时出错: {str(e)}")
                # 手动列出主要功能
                logger.info("\nGiteeToolkit 主要功能:")
                main_features = [
                    "repository_exists: 检查仓库是否存在",
                    "gitee_create_branch: 创建分支",
                    "gitee_get_branch_list: 获取分支列表",
                    "gitee_create_merge_request: 创建合并请求",
                    "gitee_get_merge_request_list: 获取合并请求列表",
                    "gitee_merge_merge_request: 合并请求",
                    "gitee_create_webhook: 创建Webhook",
                    "gitee_get_issue_list: 获取Issue列表",
                    "gitee_set_branch_protection: 设置分支保护",
                    "gitee_get_branch_protection: 获取分支保护信息"
                ]
                for feature in main_features:
                    logger.info(f"- {feature}")
        except Exception as e:
            logger.error(f"GiteeToolkit 初始化失败: {str(e)}")
            return
        
        logger.info("\n=== Gitee Toolkit 功能介绍 ===")
        logger.info("GiteeToolkit 提供以下主要功能:")
        logger.info("1. 仓库管理: 检查仓库是否存在、获取仓库信息")
        logger.info("2. 分支操作: 创建、获取分支列表、设置分支保护")
        logger.info("3. 合并请求: 创建、获取、合并合并请求")
        logger.info("4. Issue管理: 获取Issue列表")
        logger.info("5. Webhook管理: 创建Webhook")
        
        # 模拟仓库示例，避免实际API调用错误
        logger.info("\n=== Gitee Toolkit 使用示例 ===")
        
        # 模拟示例代码：检查仓库是否存在
        example_code = """
        # 检查仓库是否存在的示例代码
        try:
            exists = gt.repository_exists(repo_name="owner/repo")
            logger.info(f"仓库 owner/repo 存在: {{exists}}")
        except Exception as e:
            logger.warning(f"检查仓库是否存在时出错: {{str(e)}}")
        """
        logger.info(example_code)
        
        # 模拟示例代码：创建分支
        example_code = """
        # 创建分支的示例代码
        try:
            result = gt.gitee_create_branch(
                repo_name="owner/repo",
                branch_name="new-feature",
                ref="master"
            )
            logger.info(f"分支创建结果: {{result}}")
        except Exception as e:
            logger.warning(f"创建分支时出错: {{str(e)}}")
        """
        logger.info(example_code)
        
        # 模拟示例代码：获取分支列表
        example_code = """
        # 获取分支列表的示例代码
        try:
            branches = gt.gitee_get_branch_list(repo_name="owner/repo")
            logger.info(f"找到 {{len(branches)}} 个分支")
            for branch in branches:
                logger.info(f"  - {{branch['name']}}")
        except Exception as e:
            logger.warning(f"获取分支列表时出错: {{str(e)}}")
        """
        logger.info(example_code)
            
        logger.info("\n=== 使用说明 ===")
        logger.info("1. 请确保已在 .env 文件中正确配置了 GITEE_ACCESS_TOKEN")
        logger.info("2. 将示例代码中的仓库路径替换为实际可访问的 Gitee 仓库")
        logger.info("3. 在实际使用时，请根据您的需求修改示例代码")
    
    except Exception as e:
        logger.error(f"示例执行过程中发生错误: {str(e)}", exc_info=True)
    finally:
        logger.info("\nGiteeToolkit 示例执行完成！")

if __name__ == "__main__":
    main()