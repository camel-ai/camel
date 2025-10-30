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
示例: 使用GitLabToolkit与GitLab仓库交互

本示例整合了常规GitLab服务和本地GitLab服务的使用方法，演示了如何初始化GitLabToolkit并使用其主要功能，包括:
1. 配置并连接到常规或本地GitLab服务
2. 获取项目中的所有文件路径
3. 检索文件内容
4. 获取issues列表和详情
5. 获取merge requests列表和详情
6. 创建merge request

使用前请确保:
1. 已安装python-gitlab: `pip install python-gitlab`
2. 已设置环境变量: `GITLAB_ACCESS_TOKEN` (对于常规服务)
   或准备本地GitLab访问令牌 (对于本地服务)

更多信息请参考文档: https://docs.gitlab.com/ee/api/
"""

import os
from camel.toolkits import GitLabToolkit
from camel.toolkits.gitlab_toolkit import GitLabInstanceConfig, GitLabInstanceManager


def setup_standard_gitlab():
    """
    设置与标准GitLab服务的连接
    
    Returns:
        初始化好的GitLabToolkit实例
    """
    print("=== 配置标准GitLab连接 ===")
    
    try:
        # 从环境变量获取访问令牌
        if "GITLAB_ACCESS_TOKEN" not in os.environ:
            print("警告: 未设置GITLAB_ACCESS_TOKEN环境变量")
            print("请设置环境变量或考虑使用本地GitLab模式")
            return None
            
        # 初始化GitLabToolkit
        gt = GitLabToolkit()
        print("✓ 成功初始化标准GitLab连接")
        return gt
    except Exception as e:
        print(f"✗ 标准GitLab连接初始化失败: {e}")
        return None


def setup_local_gitlab_connection():
    """
    设置与本地GitLab服务的连接
    
    本函数演示如何配置并连接到本地GitLab服务
    """
    print("=== 配置本地GitLab连接 ===")
    
    # 注意：实际使用时需要替换为您的本地GitLab信息
    local_gitlab_url = "http://localhost:8080"  # 本地GitLab默认端口
    local_access_token = "your_local_gitlab_token"  # 本地GitLab访问令牌
    
    # 创建配置并注册实例
    config = GitLabInstanceConfig(
        url=local_gitlab_url,
        token=local_access_token,
        timeout=30.0,
        verify_ssl=False  # 本地服务可能使用自签名证书
    )
    
    # 注册本地GitLab实例
    local_instance_name = "local_gitlab"
    try:
        GitLabInstanceManager.register_instance(local_instance_name, config)
        print(f"✓ 成功注册本地GitLab实例: {local_instance_name}")
        
        # 初始化GitLabToolkit，指定要使用的实例名称
        toolkit = GitLabToolkit(instance_name=local_instance_name)
        print("✓ 成功初始化本地GitLab连接")
        return toolkit
    except Exception as e:
        print(f"✗ 本地GitLab连接失败: {e}")
        print("请检查:")
        print("  1. 本地GitLab服务是否正在运行")
        print("  2. 访问令牌是否正确")
        print("  3. GitLab URL是否正确")
        return None


def get_all_file_paths(toolkit, project_id):
    """
    获取GitLab项目中的所有文件路径
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        
    Returns:
        文件路径列表
    """
    print("\n=== 获取所有文件路径 ===")
    try:
        paths = toolkit.gitlab_get_all_file_paths(project_id=project_id)
        print(f"项目 {project_id} 中的文件路径列表:")
        for path in paths[:5]:  # 只打印前5个路径作为示例
            print(f"  - {path}")
        if len(paths) > 5:
            print(f"  ... 还有 {len(paths) - 5} 个文件")
        return paths
    except Exception as e:
        print(f"✗ 获取文件路径失败: {e}")
        return []


def retrieve_file_content(toolkit, project_id, file_path):
    """
    获取GitLab项目中指定文件的内容
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        file_path: 要检索的文件路径
        
    Returns:
        文件内容
    """
    print(f"\n=== 获取文件内容: {file_path} ===")
    try:
        content = toolkit.gitlab_retrieve_file_content(
            project_id=project_id,
            file_path=file_path
        )
        print(f"文件 {file_path} 的内容 (前500字符):")
        print(content[:500] + ("..." if len(content) > 500 else ""))
        return content
    except Exception as e:
        print(f"✗ 获取文件内容失败: {e}")
        return ""


def get_issues(toolkit, project_id, state="all"):
    """
    获取GitLab项目中的issues列表
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        state: 过滤状态 ("opened", "closed", "all")
        
    Returns:
        issues列表
    """
    print(f"\n=== 获取Issues列表 (状态: {state}) ===")
    try:
        issues = toolkit.gitlab_get_issue_list(project_id=project_id, state=state)
        print(f"项目 {project_id} 中的issues:")
        for issue in issues[:5]:  # 只打印前5个作为示例
            print(f"  - #{issue['iid']}: {issue['title']}")
        if len(issues) > 5:
            print(f"  ... 还有 {len(issues) - 5} 个issues")
        return issues
    except Exception as e:
        print(f"✗ 获取issues列表失败: {e}")
        return []


def get_issue_content(toolkit, project_id, issue_iid):
    """
    获取指定issue的内容
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        issue_iid: issue的内部ID
        
    Returns:
        issue内容
    """
    print(f"\n=== 获取Issue #{issue_iid} 内容 ===")
    try:
        content = toolkit.gitlab_get_issue_content(project_id=project_id, issue_iid=issue_iid)
        print(f"Issue #{issue_iid} 的内容 (前500字符):")
        print(content[:500] + ("..." if len(content) > 500 else ""))
        return content
    except Exception as e:
        print(f"✗ 获取issue内容失败: {e}")
        return ""


def get_merge_requests(toolkit, project_id, state="all"):
    """
    获取GitLab项目中的merge requests列表
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        state: 过滤状态 ("opened", "closed", "merged", "all")
        
    Returns:
        merge requests列表
    """
    print(f"\n=== 获取Merge Requests列表 (状态: {state}) ===")
    try:
        mrs = toolkit.gitlab_get_merge_request_list(project_id=project_id, state=state)
        print(f"项目 {project_id} 中的merge requests:")
        for mr in mrs[:5]:  # 只打印前5个作为示例
            print(f"  - #{mr['iid']}: {mr['title']}")
        if len(mrs) > 5:
            print(f"  ... 还有 {len(mrs) - 5} 个merge requests")
        return mrs
    except Exception as e:
        print(f"✗ 获取merge requests列表失败: {e}")
        return []


def get_merge_request_code(toolkit, project_id, mr_iid):
    """
    获取指定merge request的代码变更
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        mr_iid: merge request的内部ID
        
    Returns:
        代码变更列表
    """
    print(f"\n=== 获取Merge Request #{mr_iid} 代码变更 ===")
    try:
        changes = toolkit.gitlab_get_merge_request_code(project_id=project_id, mr_iid=mr_iid)
        print(f"Merge Request #{mr_iid} 的代码变更:")
        for change in changes[:3]:  # 只打印前3个文件变更作为示例
            print(f"  - 文件: {change['filename']}")
            print(f"    变更: {change['patch'][:200]}..." if len(change['patch']) > 200 else f"    变更: {change['patch']}")
            print()
        if len(changes) > 3:
            print(f"  ... 还有 {len(changes) - 3} 个文件变更")
        return changes
    except Exception as e:
        print(f"✗ 获取merge request代码变更失败: {e}")
        return []


def get_merge_request_comments(toolkit, project_id, mr_iid):
    """
    获取指定merge request的评论
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        mr_iid: merge request的内部ID
        
    Returns:
        评论列表
    """
    print(f"\n=== 获取Merge Request #{mr_iid} 评论 ===")
    try:
        comments = toolkit.gitlab_get_merge_request_comments(project_id=project_id, mr_iid=mr_iid)
        print(f"Merge Request #{mr_iid} 的评论:")
        for comment in comments[:3]:  # 只打印前3个评论作为示例
            print(f"  - {comment['user']}: {comment['body'][:100]}..." if len(comment['body']) > 100 else f"  - {comment['user']}: {comment['body']}")
        if len(comments) > 3:
            print(f"  ... 还有 {len(comments) - 3} 条评论")
        return comments
    except Exception as e:
        print(f"✗ 获取merge request评论失败: {e}")
        return []


def create_merge_request(toolkit, project_id, file_path, new_content, mr_title, body, branch_name):
    """
    创建新的merge request并更新文件内容
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        file_path: 要更新的文件路径
        new_content: 文件的新内容
        mr_title: merge request标题
        body: merge request描述
        branch_name: 新分支名称
        
    Returns:
        创建结果
    """
    print(f"\n=== 创建Merge Request ===")
    try:
        result = toolkit.gitlab_create_merge_request(
            project_id=project_id,
            file_path=file_path,
            new_content=new_content,
            mr_title=mr_title,
            body=body,
            branch_name=branch_name
        )
        print(f"✓ Merge Request 创建成功!")
        print(f"  MR详情: {result}")
        return result
    except Exception as e:
        print(f"✗ 创建merge request失败: {e}")
        return ""


def demonstrate_core_functionality(toolkit, project_id):
    """
    演示GitLabToolkit的核心功能
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
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
        else:
            retrieve_file_content(toolkit, project_id, file_paths[0])
    
    # 3. 获取开启状态的issues列表
    issues = get_issues(toolkit, project_id, state="opened")
    
    # 4. 获取开启状态的merge requests列表
    merge_requests = get_merge_requests(toolkit, project_id, state="opened")
    
    return issues, merge_requests


def demonstrate_advanced_functionality(toolkit, project_id, issues, merge_requests):
    """
    演示GitLabToolkit的高级功能
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
        issues: issues列表
        merge_requests: merge requests列表
    """
    if not toolkit:
        return
    
    print("\n=== 演示高级功能 ===")
    
    # 如果有issue，获取第一个issue的详情
    if issues:
        get_issue_content(toolkit, project_id, issues[0]['iid'])
    
    # 如果有merge request，获取其代码变更和评论
    if merge_requests:
        mr_iid = merge_requests[0]['iid']
        get_merge_request_code(toolkit, project_id, mr_iid)
        get_merge_request_comments(toolkit, project_id, mr_iid)


def demonstrate_merge_request_creation_interactive(toolkit, project_id):
    """
    交互式演示如何创建新的Merge Request
    
    Args:
        toolkit: GitLabToolkit实例
        project_id: GitLab项目ID或路径
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
    file_path = input("请输入要更新的文件路径 (默认为'test_update.md'): ") or "test_update.md"
    mr_title = input("请输入Merge Request标题 (默认为'测试更新'): ") or "测试更新"
    branch_name = input("请输入新分支名称 (默认为'test-gitlab-toolkit-update'): ") or "test-gitlab-toolkit-update"
    
    # 创建一个测试文件或更新现有文件
    create_merge_request(
        toolkit,
        project_id,
        file_path,
        "# 测试文件\n\n这是通过GitLabToolkit创建的测试文件。",
        mr_title,
        "这是一个自动化测试创建的Merge Request。",
        branch_name
    )


def main():
    """
    主函数 - 演示GitLabToolkit的各种功能
    """
    print("=== GitLabToolkit综合使用示例 ===")
    print("本示例整合了常规GitLab服务和本地GitLab服务的使用方法")
    
    # 选择连接模式
    print("\n请选择连接模式:")
    print("1. 标准GitLab服务 (使用环境变量GITLAB_ACCESS_TOKEN)")
    print("2. 本地GitLab服务")
    
    choice = input("请输入选择 (1/2): ")
    
    # 初始化GitLabToolkit
    toolkit = None
    if choice == "1":
        toolkit = setup_standard_gitlab()
    elif choice == "2":
        toolkit = setup_local_gitlab_connection()
    else:
        print("无效选择，默认使用标准GitLab服务")
        toolkit = setup_standard_gitlab()
    
    if not toolkit:
        print("\n程序终止: 无法初始化GitLabToolkit")
        return
    
    # 设置要操作的项目ID
    project_id = input("\n请输入GitLab项目ID或路径 (例如: 'group/project' 或 123): ")
    if not project_id:
        print("未提供项目ID，程序终止")
        return
    
    # 演示核心功能
    issues, merge_requests = demonstrate_core_functionality(toolkit, project_id)
    
    # 演示高级功能
    demonstrate_advanced_functionality(toolkit, project_id, issues, merge_requests)
    
    # 演示创建Merge Request (可选，需要用户确认)
    demonstrate_merge_request_creation_interactive(toolkit, project_id)
    
    print("\n=== GitLabToolkit使用示例完成 ===")


if __name__ == "__main__":
    main()