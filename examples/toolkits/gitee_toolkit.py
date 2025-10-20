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
示例: 使用GiteeToolkit与Gitee仓库交互

本示例整合了常规Gitee服务和本地Gitee服务的使用方法，演示了如何初始化GiteeToolkit并使用其主要功能，包括:
1. 配置并连接到Gitee服务
2. 获取项目中的所有文件路径
3. 检索文件内容
4. 获取issues列表和详情
5. 创建merge request

使用前请确保:
1. 已设置环境变量: `GITEE_ACCESS_TOKEN`

更多信息请参考文档: https://gitee.com/api/v5/swagger#/
"""

import os
import sys
from camel.toolkits import GiteeToolkit
from camel.toolkits.gitee_toolkit import GiteeInstanceConfig, GiteeInstanceManager

def check_dependencies():
    """
    检查是否安装了必要的依赖包
    """
    try:
        import requests
        print("✓ 必要依赖已安装")
        return True
    except ImportError:
        print("✗ 缺少必要依赖: requests")
        print("请使用以下命令安装: pip install requests")
        return False

def setup_gitee_connection():
    """
    设置与Gitee服务的连接
    
    Returns:
        初始化好的GiteeToolkit实例
    """
    print("=== 配置Gitee连接 ===")
    
    try:
        # 从环境变量获取访问令牌
        if "GITEE_ACCESS_TOKEN" not in os.environ:
            # 尝试交互式获取访问令牌
            print("警告: 未设置GITEE_ACCESS_TOKEN环境变量")
            access_token = input("请输入您的Gitee访问令牌 (输入为空则退出): ")
            if not access_token:
                print("未提供访问令牌，程序终止")
                return None
            # 设置环境变量以便后续使用
            os.environ["GITEE_ACCESS_TOKEN"] = access_token
        else:
            access_token = os.environ["GITEE_ACCESS_TOKEN"]
            print("✓ 从环境变量获取访问令牌")
            
        # 初始化GiteeToolkit
        gt = GiteeToolkit(access_token=access_token)
        print("✓ 成功初始化Gitee连接")
        return gt
    except Exception as e:
        print(f"✗ Gitee连接初始化失败: {e}")
        return None

def get_all_file_paths(toolkit, project_id):
    """
    获取Gitee项目中的所有文件路径
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径 (格式: owner/repo)
        
    Returns:
        文件路径列表
    """
    print("\n=== 获取所有文件路径 ===")
    try:
        paths = toolkit.gitee_get_all_file_paths(project_id=project_id)
        print(f"项目 {project_id} 中的文件路径列表:")
        for path in paths[:5]:  # 只打印前5个路径作为示例
            print(f"  - {path}")
        if len(paths) > 5:
            print(f"  ... 还有 {len(paths) - 5} 个文件")
        return paths
    except Exception as e:
        print(f"✗ 获取文件路径失败: {e}")
        return []

def retrieve_file_content(toolkit, project_id, file_path, ref="master"):
    """
    获取Gitee项目中指定文件的内容
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
        file_path: 要检索的文件路径
        ref: 分支或标签名，默认为master
        
    Returns:
        文件内容
    """
    print(f"\n=== 获取文件内容: {file_path} ===")
    try:
        content = toolkit.gitee_retrieve_file_content(
            project_id=project_id,
            file_path=file_path,
            ref=ref
        )
        print(f"文件 {file_path} 的内容 (前500字符):")
        print(content[:500] + ("..." if len(content) > 500 else ""))
        return content
    except Exception as e:
        print(f"✗ 获取文件内容失败: {e}")
        return ""

def get_issues(toolkit, project_id, state="open"):
    """
    获取Gitee项目中的issues列表
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
        state: 过滤状态 ("open", "closed", "all")
        
    Returns:
        issues列表
    """
    print(f"\n=== 获取Issues列表 (状态: {state}) ===")
    try:
        issues = toolkit.gitee_get_issue_list(project_id=project_id, state=state)
        print(f"项目 {project_id} 中的issues:")
        for issue in issues[:5]:  # 只打印前5个作为示例
            print(f"  - #{issue['number']}: {issue['title']}")
        if len(issues) > 5:
            print(f"  ... 还有 {len(issues) - 5} 个issues")
        return issues
    except Exception as e:
        print(f"✗ 获取issues列表失败: {e}")
        return []

def get_issue_content(toolkit, project_id, issue_number):
    """
    获取指定issue的内容
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
        issue_number: issue的编号
        
    Returns:
        issue内容
    """
    print(f"\n=== 获取Issue #{issue_number} 内容 ===")
    try:
        content = toolkit.gitee_get_issue_content(project_id=project_id, issue_number=issue_number)
        print(f"Issue #{issue_number} 的内容 (前500字符):")
        print(content[:500] + ("..." if len(content) > 500 else ""))
        return content
    except Exception as e:
        print(f"✗ 获取issue内容失败: {e}")
        return ""

def create_merge_request(toolkit, project_id, title, body, base, head):
    """
    创建新的merge request
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
        title: merge request标题
        body: merge request描述
        base: 目标分支
        head: 源分支
        
    Returns:
        创建结果
    """
    print(f"\n=== 创建Merge Request ===")
    try:
        result = toolkit.gitee_create_merge_request(
            project_id=project_id,
            title=title,
            body=body,
            base=base,
            head=head
        )
        print(f"✓ Merge Request 创建成功!")
        print(f"  MR详情: {result}")
        return result
    except Exception as e:
        print(f"✗ 创建merge request失败: {e}")
        return ""

def demonstrate_core_functionality(toolkit, project_id):
    """
    演示GiteeToolkit的核心功能
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
    """
    if not toolkit:
        print("无法演示功能，工具包初始化失败")
        return
    
    # 1. 获取项目中的所有文件路径
    file_paths = get_all_file_paths(toolkit, project_id)
    
    # 2. 如果有文件，尝试获取README.md或第一个文件的内容
    if file_paths:
        if "README.md" in file_paths:
            retrieve_file_content(toolkit, project_id, "README.md")
        elif "README" in file_paths:
            retrieve_file_content(toolkit, project_id, "README")
        else:
            retrieve_file_content(toolkit, project_id, file_paths[0])
    
    # 3. 获取开启状态的issues列表
    issues = get_issues(toolkit, project_id, state="open")
    
    return issues

def demonstrate_advanced_functionality(toolkit, project_id, issues):
    """
    演示GiteeToolkit的高级功能
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
        issues: issues列表
    """
    if not toolkit:
        return
    
    print("\n=== 演示高级功能 ===")
    
    # 如果有issue，获取第一个issue的详情
    if issues:
        get_issue_content(toolkit, project_id, issues[0]['number'])

def demonstrate_merge_request_creation_interactive(toolkit, project_id):
    """
    交互式演示如何创建新的Merge Request
    
    Args:
        toolkit: GiteeToolkit实例
        project_id: Gitee项目ID或路径
    """
    if not toolkit:
        return
    
    print("\n=== 演示创建Merge Request (注意: 这会修改仓库内容!) ===")
    
    # 只在用户确认后执行
    confirmation = input("是否继续创建Merge Request? (y/N): ")
    if confirmation.lower() != 'y':
        print("取消创建Merge Request")
        return
    
    # 交互式获取创建MR所需信息
    title = input("请输入Merge Request标题 (默认为'测试更新'): ") or "测试更新"
    body = input("请输入Merge Request描述 (默认为'这是一个测试MR'): ") or "这是一个测试MR"
    base = input("请输入目标分支 (默认为'master'): ") or "master"
    head = input("请输入源分支 (默认为'feature/test-branch'): ") or "feature/test-branch"
    
    # 创建Merge Request
    create_merge_request(
        toolkit,
        project_id,
        title,
        body,
        base,
        head
    )

def main():
    """
    主函数 - 演示GiteeToolkit的各种功能
    """
    print("=== GiteeToolkit综合使用示例 ===")
    print("本示例演示了如何使用GiteeToolkit与Gitee仓库交互")
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 初始化GiteeToolkit
    toolkit = setup_gitee_connection()
    
    if not toolkit:
        print("\n程序终止: 无法初始化GiteeToolkit")
        return
    
    # 设置要操作的项目ID
    project_id = input("\n请输入Gitee项目路径 (例如: 'user/repo'): ")
    if not project_id:
        print("未提供项目ID，程序终止")
        return
    
    # 演示核心功能
    issues = demonstrate_core_functionality(toolkit, project_id)
    
    # 演示高级功能
    demonstrate_advanced_functionality(toolkit, project_id, issues)
    
    # 演示创建Merge Request (可选，需要用户确认)
    demonstrate_merge_request_creation_interactive(toolkit, project_id)
    
    print("\n=== GiteeToolkit使用示例完成 ===")

if __name__ == "__main__":
    main()