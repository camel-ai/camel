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

# 加载环境变量
load_dotenv()

def main():
    """
    GitHub Toolkit 演示示例
    
    注意：此示例需要有效的 GitHub 访问令牌
    1. 在 .env 文件中设置 GITHUB_ACCESS_TOKEN
    2. 或直接在代码中提供令牌
    """
    try:
        # 尝试导入并使用 GithubToolkit
        from camel.toolkits import GithubToolkit
        
        # 获取环境变量中的访问令牌
        access_token = os.getenv('GITHUB_ACCESS_TOKEN')
        
        if access_token:
            # 如果有访问令牌，初始化工具包
            logger.info("正在初始化 GithubToolkit...")
            try:
                gt = GithubToolkit(access_token=access_token)
                logger.info("GithubToolkit 初始化成功")
                
                # 列出工具包提供的工具
                logger.info("\n=== 列出工具包提供的工具 ===")
                try:
                    tools = gt.get_tools()
                    logger.info(f"GithubToolkit 提供的工具 ({len(tools)} 个):")
                    for i, tool in enumerate(tools, 1):
                        logger.info(f"{i}. {tool.name}")
                except Exception as e:
                    logger.warning(f"获取工具列表时出错: {str(e)}")
                    # 手动列出主要功能
                    logger.info("\nGithubToolkit 主要功能:")
                    main_features = [
                        "github_get_all_file_paths: 获取仓库中所有文件路径",
                        "github_retrieve_file_content: 获取文件内容",
                        "github_upload_file: 上传文件到仓库",
                        "github_update_file: 更新仓库中的文件",
                        "github_delete_file: 删除仓库中的文件"
                    ]
                    for feature in main_features:
                        logger.info(f"- {feature}")
                
                logger.info("\n在有有效访问令牌的情况下，可以执行以下操作:")
                logger.info("1. 获取仓库文件列表: gt.github_get_all_file_paths(repo_name='owner/repo')")
                logger.info("2. 获取文件内容: gt.github_retrieve_file_content(repo_name='owner/repo', file_path='path/to/file')")
                logger.info("3. 创建问题: gt.github_create_issue(...)")
                logger.info("4. 创建拉取请求: gt.github_create_pull_request(...)")
                
                # 确保在有gt变量定义的作用域内使用它
                try:
                    # 示例：获取仓库中的文件列表
                    logger.info("\n=== 示例代码演示 ===")
                    logger.info("要获取文件内容，可以使用以下代码:")
                    example_code = """
                    # 获取文件内容示例
                    content = gt.github_retrieve_file_content(
                        "camel-ai/camel",  # 仓库名
                        "camel/agents/chat_agent.py",  # 文件路径
                        "main"  # 分支名
                    )
                    print(f"文件内容前100个字符: {content[:100]}...")
                    """
                    logger.info(example_code)
                except Exception as e:
                    logger.error(f"示例代码执行失败: {str(e)}")
                    
            except Exception as e:
                logger.error(f"GithubToolkit 初始化失败: {str(e)}")
        else:
            # 如果没有访问令牌，显示提示信息
            logger.warning("未找到 GITHUB_ACCESS_TOKEN 环境变量")
            logger.info("请在 .env 文件中设置 GITHUB_ACCESS_TOKEN 以获得完整功能")
            logger.info("获取令牌地址: https://github.com/settings/tokens")
            
            # 展示如何初始化和使用工具包的代码示例
            logger.info("\n=== 示例代码 ===")
            example_code = """
            # 初始化 GithubToolkit
            from camel.toolkits import GithubToolkit
            
            # 方法1: 从环境变量自动获取令牌
            gt = GithubToolkit()
            
            # 方法2: 直接提供令牌
            # gt = GithubToolkit(access_token='your_github_token')
            
            # 使用示例
            paths = gt.github_get_all_file_paths(repo_name="camel-ai/camel")
            print(paths[:5])  # 显示前5个文件路径
            """
            logger.info(example_code)
            
    except ImportError as e:
        logger.error(f"导入 GithubToolkit 失败: {str(e)}")
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
    finally:
        logger.info("\nGithubToolkit 示例执行完成!")

if __name__ == "__main__":
    main()
