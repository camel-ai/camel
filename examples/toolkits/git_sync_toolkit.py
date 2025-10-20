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
GitSyncToolkit 使用示例

本示例展示了GitSyncToolkit的核心功能，包括：
1. 跨平台同步（GitHub、Gitee、GitLab）
2. 单向与多目标同步
3. 冲突解决策略
4. 增量同步优化
"""

import os
import time
import json
from typing import Dict

from camel.toolkits.git_sync_toolkit import (
    GitSyncToolkit,
    GitPlatformType,
    ConflictResolutionStrategy,
    GitSyncConfig
)

def get_api_tokens() -> Dict[str, str]:
    """
    从环境变量获取API访问令牌，或提示用户输入
    
    Returns:
        Dict[str, str]: 包含GitHub、Gitee和GitLab访问令牌的字典
    """
    tokens = {}
    
    # 从环境变量获取令牌，如果不存在则提供提示
    github_token = os.environ.get("GITHUB_ACCESS_TOKEN")
    gitee_token = os.environ.get("GITEE_ACCESS_TOKEN")
    gitlab_token = os.environ.get("GITLAB_ACCESS_TOKEN")
    
    # 检查并提示
    if not github_token:
        print("警告: 未设置GITHUB_ACCESS_TOKEN环境变量")
    if not gitee_token:
        print("警告: 未设置GITEE_ACCESS_TOKEN环境变量")
    if not gitlab_token:
        print("警告: 未设置GITLAB_ACCESS_TOKEN环境变量")
    
    tokens["github"] = github_token
    tokens["gitee"] = gitee_token
    tokens["gitlab"] = gitlab_token
    
    return tokens

def demo_basic_sync():
    """演示基本同步功能"""
    print("\n=== 基本同步演示 ===")
    print("此示例展示如何在不同Git平台之间进行单向同步")
    
    # 创建同步工具实例
    sync_toolkit = GitSyncToolkit()
    
    # 示例 1: GitHub -> Gitee 同步
    print("\n1. GitHub -> Gitee 同步")
    print("----------------------------------------")
    
    # 创建从 GitHub 同步到 Gitee 的配置
    try:
        github_to_gitee_config_id = sync_toolkit.create_sync_config(
            source_platform="github",
            source_repo="example_owner/example_repo",  # 源仓库
            target_configs=[
                {
                    "platform": "gitee",
                    "repo": "example_owner/example_repo",  # 目标仓库
                    # "credentials": {"access_token": "optional_explicit_token"},  # 可选，直接提供令牌
                }
            ],
            sync_branches=["main", "develop"],  # 同步多个分支
            sync_tags=True,
            incremental_sync=True,  # 启用增量同步
            force_push=False  # 不使用强制推送
        )
        
        print(f"创建配置成功，配置ID: {github_to_gitee_config_id}")
        
        # 注意：实际同步需要正确设置环境变量和有效的仓库信息
        print("\n提示: 要执行实际同步，请确保已设置有效的环境变量并使用实际存在的仓库")
        # 执行同步示例（注释掉，避免实际执行）
        # result = sync_toolkit.sync_repositories(github_to_gitee_config_id)
        # print(f"同步结果: {result.success}")
        # print(f"同步详情: {result.changes}")
        
    except Exception as e:
        print(f"创建配置时出错: {e}")

def demo_multi_target_sync():
    """演示多目标同步功能"""
    print("\n=== 多目标同步演示 ===")
    print("此示例展示如何从单一源仓库同步到多个目标平台")
    
    # 创建同步工具实例
    sync_toolkit = GitSyncToolkit()
    
    try:
        # 创建一个源仓库到多个目标仓库的配置
        multi_target_config_id = sync_toolkit.create_sync_config(
            source_platform="github",
            source_repo="example_owner/main_repo",  # 单一源仓库
            target_configs=[
                {
                    "platform": "gitee",
                    "repo": "example_owner/main_repo",  # 目标1: Gitee
                },
                {
                    "platform": "gitlab",
                    "repo": "example_owner/main_repo",  # 目标2: GitLab
                }
            ],
            sync_branches=["main"],
            sync_tags=True,
            incremental_sync=True,
            # 冲突解决策略: 源仓库优先
            conflict_resolution=ConflictResolutionStrategy.SOURCE_WINS
        )
        
        print(f"创建多目标配置成功，配置ID: {multi_target_config_id}")
        
    except Exception as e:
        print(f"创建多目标配置时出错: {e}")

def demo_conflict_resolution():
    """演示不同的冲突解决策略"""
    print("\n=== 冲突解决策略演示 ===")
    print("此示例展示如何配置不同的冲突解决策略")
    
    # 创建同步工具实例
    sync_toolkit = GitSyncToolkit()
    
    # 策略列表及其描述
    strategies = [
        (ConflictResolutionStrategy.SOURCE_WINS, "源仓库优先 - 总是使用源仓库内容覆盖目标仓库"),
        (ConflictResolutionStrategy.TARGET_WINS, "目标仓库优先 - 保留目标仓库内容，忽略源仓库冲突部分"),
        (ConflictResolutionStrategy.TIMESTAMP_BASED, "基于时间戳 - 使用最后修改的内容"),
        (ConflictResolutionStrategy.MERGE, "自动合并 - 尝试自动合并冲突（可能产生合并冲突标记）")
    ]
    
    print("可用的冲突解决策略:")
    for strategy, description in strategies:
        print(f"- {strategy.value}: {description}")
    
    print("\n示例: 创建使用基于时间戳策略的配置")
    try:
        config_id = sync_toolkit.create_sync_config(
            source_platform="github",
            source_repo="example_owner/example_repo",
            target_configs=[{"platform": "gitee", "repo": "example_owner/example_repo"}],
            sync_branches=["main"],
            # 设置基于时间戳的冲突解决策略
            conflict_resolution=ConflictResolutionStrategy.TIMESTAMP_BASED
        )
        print(f"创建配置成功，配置ID: {config_id}")
    except Exception as e:
        print(f"创建配置时出错: {e}")

def demo_config_management():
    """演示配置管理功能"""
    print("\n=== 配置管理演示 ===")
    print("此示例展示如何列出和管理同步配置")
    
    # 创建同步工具实例
    sync_toolkit = GitSyncToolkit()
    
    # 创建测试配置
    config_id = None
    try:
        config_id = sync_toolkit.create_sync_config(
            source_platform="github",
            source_repo="example_owner/test_config_repo",
            target_configs=[{"platform": "gitee", "repo": "example_owner/test_config_repo"}],
        )
        print(f"创建配置成功，配置ID: {config_id}")
        
        # 列出所有配置
        print("\n列出所有配置:")
        configs = sync_toolkit.list_sync_configs()
        print(f"总配置数: {len(configs)}")
        
        for config in configs:
            print(f"- 配置ID: {config.id}")
            print(f"  源平台: {config.source_platform.value}")
            print(f"  源仓库: {config.source_repo}")
            print(f"  目标仓库数: {len(config.target_configs)}")
            print(f"  同步分支: {', '.join(config.sync_branches)}")
            print(f"  同步标签: {config.sync_tags}")
            print(f"  增量同步: {config.incremental_sync}")
        
        # 删除配置
        print(f"\n删除配置 {config_id}")
        deleted = sync_toolkit.delete_sync_config(config_id)
        print(f"删除结果: {'成功' if deleted else '失败'}")
        
        # 验证配置已删除
        remaining_configs = sync_toolkit.list_sync_configs()
        print(f"删除后剩余配置数: {len(remaining_configs)}")
        
    except Exception as e:
        print(f"配置管理操作出错: {e}")
        # 确保在出错时也删除创建的配置
        if config_id:
            try:
                sync_toolkit.delete_sync_config(config_id)
            except:
                pass

def main():
    """主函数，运行所有演示"""
    print("=================================================")
    print("GitSyncToolkit 使用示例")
    print("=================================================")
    print("本示例展示了GitSyncToolkit的核心功能，包括基本同步、")
    print("多目标同步、冲突解决策略和配置管理")
    print("=================================================")
    
    # 获取API令牌
    tokens = get_api_tokens()
    
    # 运行各种演示
    demo_basic_sync()
    demo_multi_target_sync()
    demo_conflict_resolution()
    demo_config_management()
    
    print("\n=================================================")
    print("演示完成")
    print("注意: 以上示例仅创建配置，未执行实际同步。")
    print("要执行实际同步，请确保:")
    print("1. 已设置有效的平台访问令牌环境变量")
    print("2. 使用实际存在的仓库路径")
    print("3. 取消注释相应的同步执行代码")
    print("=================================================")

if __name__ == "__main__":
    main()