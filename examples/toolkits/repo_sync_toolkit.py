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
import json
import logging
import tempfile
from dotenv import load_dotenv
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 导入仓库同步工具包
from camel.toolkits.repo_sync_toolkit import RepoSyncToolkit
from camel.types import RepositoryPlatformType, RepositorySyncConfig

def main():
    """
    RepoSyncToolkit 功能演示
    
    本示例演示了如何使用 RepoSyncToolkit 在不同版本控制系统之间同步仓库，
    支持 GitHub、GitLab、Gitee 和 SVN 之间的相互同步。
    """
    try:
        # 初始化 RepoSyncToolkit
        logger.info("初始化 RepoSyncToolkit...")
        toolkit = RepoSyncToolkit()
        logger.info("RepoSyncToolkit 初始化成功")
        
        # 示例1: 列出工具包提供的主要方法
        logger.info("\n=== 示例1: RepoSyncToolkit 主要功能 ===")
        main_features = [
            "create_sync_config: 创建同步配置",
            "add_sync_config: 添加同步配置并获取ID",
            "sync_repositories: 执行仓库同步操作",
            "_get_platform_toolkit: 获取平台特定工具包"
        ]
        logger.info(f"RepoSyncToolkit 主要功能 ({len(main_features)} 个):")
        for i, feature in enumerate(main_features, 1):
            logger.info(f"{i}. {feature}")
        
        # 创建临时目录用于同步操作
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"\n创建临时目录用于同步操作: {temp_dir}")
            
            # 示例2: 创建GitHub到Gitee的同步配置
            logger.info("\n=== 示例2: 创建GitHub到Gitee的同步配置 ===")
            # 使用toolkit的create_sync_config方法创建配置
            github_to_gitee_config = toolkit.create_sync_config(
                source_platform=RepositoryPlatformType.GITHUB,
                target_platform=RepositoryPlatformType.GITEE,
                source_repo="https://github.com/example/source-repo",
                target_repo="https://gitee.com/example/dest-repo",
                source_branch="main",
                target_branch="main",
                source_credentials={"access_token": os.getenv("GITHUB_TOKEN")},
                target_credentials={"access_token": os.getenv("GITEE_TOKEN")},
                include_patterns=["src/", "docs/"],
                exclude_patterns=["tests/", ".github/"]
            )
            
            # 显示配置信息（不直接保存JSON，因为RepositorySyncConfig不可直接序列化）
            logger.info("GitHub 到 Gitee 的同步配置创建成功")
            logger.info("配置内容:")
            logger.info(f"- 源平台: {github_to_gitee_config.source_platform}")
            logger.info(f"- 目标平台: {github_to_gitee_config.target_platform}")
            logger.info(f"- 源仓库: {github_to_gitee_config.source_repo}")
            logger.info(f"- 目标仓库: {github_to_gitee_config.target_repo}")
            logger.info(f"- 源分支: {github_to_gitee_config.source_branch}")
            logger.info(f"- 目标分支: {github_to_gitee_config.target_branch}")
            
            # 示例3: 创建SVN到GitHub的同步配置
            logger.info("\n=== 示例3: 创建SVN到GitHub的同步配置 ===")
            # 使用toolkit的create_sync_config方法创建配置
            svn_to_github_config = toolkit.create_sync_config(
                source_platform=RepositoryPlatformType.SVN,
                target_platform=RepositoryPlatformType.GITHUB,
                source_repo="https://svn.example.com/repos/project/trunk",
                target_repo="https://github.com/example/svn-mirror",
                source_branch="trunk",
                target_branch="main",
                source_credentials={
                    "username": os.getenv("SVN_USERNAME"),
                    "password": os.getenv("SVN_PASSWORD")
                },
                target_credentials={"access_token": os.getenv("GITHUB_TOKEN")},
                incremental_sync=True  # 保持历史记录
            )
            
            # 显示配置信息
            logger.info("SVN 到 GitHub 的同步配置创建成功")
            logger.info("配置内容:")
            logger.info(f"- 源平台: {svn_to_github_config.source_platform}")
            logger.info(f"- 目标平台: {svn_to_github_config.target_platform}")
            logger.info(f"- 源仓库: {svn_to_github_config.source_repo}")
            logger.info(f"- 目标仓库: {svn_to_github_config.target_repo}")
            logger.info(f"- 源分支: {svn_to_github_config.source_branch}")
            logger.info(f"- 目标分支: {svn_to_github_config.target_branch}")
            
            # 示例4: 演示如何使用同步配置
            logger.info("\n=== 示例4: 使用同步配置进行同步操作 ===")
            
            # 生成配置ID示例
            logger.info("生成配置ID:")
            # 添加配置并获取配置ID
            config_id = toolkit.add_sync_config(github_to_gitee_config)
            logger.info(f"配置ID: {config_id}")
            
            # 示例代码: 如何执行同步操作
            example_code = """
            # 执行同步操作的示例代码
            try:
                # 执行同步（使用已经创建的RepositorySyncConfig对象）
                sync_result = toolkit.sync_repositories(
                    config=github_to_gitee_config
                )
                
                # 处理同步结果
                if sync_result.success:
                    logger.info(f"同步成功: {sync_result.message}")
                    if sync_result.details:
                        logger.info(f"源提交: {sync_result.details.get('source_commit')}")
                        logger.info(f"目标提交: {sync_result.details.get('destination_commit')}")
                else:
                    logger.error(f"同步失败: {sync_result.message}")
                    if sync_result.errors:
                        for error in sync_result.errors:
                            logger.error(f"错误详情: {str(error)}")
                
            except Exception as e:
                logger.error(f"同步过程中发生错误: {str(e)}", exc_info=True)
            """
            logger.info(example_code)
            
            # 示例5: 演示批量同步功能
            logger.info("\n=== 示例5: 批量同步功能 ===")
            
            # 创建批量同步配置列表
            batch_configs = [
                github_to_gitee_config,
                svn_to_github_config
            ]
            
            # 示例代码: 如何执行批量同步
            example_code = """
            # 执行批量同步的示例代码
            try:
                # 逐一执行同步
                results = []
                for config in batch_configs:
                    # 为每个配置添加到toolkit
                    config_id = toolkit.add_sync_config(config)
                    # 执行同步
                    sync_result = toolkit.sync_repositories(config=config)
                    results.append((config_id, sync_result))
                
                # 处理批量同步结果
                for i, (config_id, result) in enumerate(results, 1):
                    status = "成功" if result.success else "失败"
                    logger.info(f"同步任务 {i} (配置ID: {config_id}): {status}")
                    logger.info(f"  消息: {result.message}")
                    if result.details:
                        logger.info(f"  源提交: {result.details.get('source_commit')}")
                        logger.info(f"  目标提交: {result.details.get('destination_commit')}")
                
            except Exception as e:
                logger.error(f"批量同步过程中发生错误: {str(e)}", exc_info=True)
            """
            logger.info(example_code)
        
        logger.info("\nRepoSyncToolkit 示例执行完成！")
        logger.info("注意: 本示例中的实际同步操作需要有效的仓库URL和凭据")
        logger.info("请在 .env 文件中配置相应的环境变量以进行实际同步")
        
    except Exception as e:
        logger.error(f"示例执行过程中发生错误: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()