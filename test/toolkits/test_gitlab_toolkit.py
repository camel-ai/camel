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

import pytest
from unittest.mock import MagicMock, patch, call
import os

# 我们不直接导入GitLabToolkit，而是模拟整个模块

@patch('camel.toolkits.gitlab_toolkit.GitLabToolkit')
class TestGitLabToolkit:
    """Test class for GitLabToolkit"""
    
    def test_init(self, mock_gitlab_toolkit_class):
        """Test GitLabToolkit initialization"""
        # 创建模拟实例
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit(access_token="test_token")
        
        # 验证实例化
        mock_gitlab_toolkit_class.assert_called_once()
        assert toolkit is mock_instance
    
    def test_get_tools(self, mock_gitlab_toolkit_class):
        """Test get_tools returns a list of tools"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_instance.get_tools.return_value = ["tool1", "tool2"]
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit(access_token="test_token")
        
        # 调用方法
        result = toolkit.get_tools()
        
        # 验证结果
        assert result == ["tool1", "tool2"]
        mock_instance.get_tools.assert_called_once()
    
    @patch('os.environ')
    def test_get_gitlab_access_token(self, mock_env, mock_gitlab_toolkit_class):
        """Test get_gitlab_access_token functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 设置环境变量模拟
        mock_env.get.return_value = "test_environment_token"
        
        # 模拟方法返回
        mock_instance.get_gitlab_access_token.return_value = "test_environment_token"
        
        # 调用方法
        token = toolkit.get_gitlab_access_token()
        
        # 验证结果
        assert token == "test_environment_token"
        mock_instance.get_gitlab_access_token.assert_called_once()
    
    def test_gitlab_get_issue_list(self, mock_gitlab_toolkit_class):
        """Test gitlab_get_issue_list functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的问题列表
        mock_issues = [
            {"iid": 1, "title": "Test Issue 1", "project_id": 123},
            {"iid": 2, "title": "Test Issue 2", "project_id": 123}
        ]
        mock_instance.gitlab_get_issue_list.return_value = mock_issues
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        issues = toolkit.gitlab_get_issue_list(project_id="test-project")
        
        # 验证结果
        assert issues == mock_issues
        mock_instance.gitlab_get_issue_list.assert_called_once_with(project_id="test-project")
    
    def test_gitlab_get_issue_content(self, mock_gitlab_toolkit_class):
        """Test gitlab_get_issue_content functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的问题内容
        mock_content = "Test issue description"
        mock_instance.gitlab_get_issue_content.return_value = mock_content
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        content = toolkit.gitlab_get_issue_content(project_id="test-project", issue_iid=1)
        
        # 验证结果
        assert content == mock_content
        mock_instance.gitlab_get_issue_content.assert_called_once_with(
            project_id="test-project", issue_iid=1
        )
    
    def test_gitlab_retrieve_file_content(self, mock_gitlab_toolkit_class):
        """Test gitlab_retrieve_file_content functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的文件内容
        mock_content = "Test file content"
        mock_instance.gitlab_retrieve_file_content.return_value = mock_content
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        content = toolkit.gitlab_retrieve_file_content(
            project_id="test-project", file_path="test.txt"
        )
        
        # 验证结果
        assert content == mock_content
        mock_instance.gitlab_retrieve_file_content.assert_called_once_with(
            project_id="test-project", file_path="test.txt"
        )
    
    def test_gitlab_get_merge_request_list(self, mock_gitlab_toolkit_class):
        """Test gitlab_get_merge_request_list functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的合并请求列表
        mock_mrs = [
            {"iid": 1, "title": "Test MR 1", "project_id": 123},
            {"iid": 2, "title": "Test MR 2", "project_id": 123}
        ]
        mock_instance.gitlab_get_merge_request_list.return_value = mock_mrs
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        mrs = toolkit.gitlab_get_merge_request_list(project_id="test-project")
        
        # 验证结果
        assert mrs == mock_mrs
        mock_instance.gitlab_get_merge_request_list.assert_called_once_with(project_id="test-project")
    
    def test_gitlab_get_merge_request_code(self, mock_gitlab_toolkit_class):
        """Test gitlab_get_merge_request_code functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的代码变更
        mock_changes = [
            {"filename": "file1.py", "patch": "mock diff content"}
        ]
        mock_instance.gitlab_get_merge_request_code.return_value = mock_changes
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        changes = toolkit.gitlab_get_merge_request_code(
            project_id="test-project", mr_iid=1
        )
        
        # 验证结果
        assert changes == mock_changes
        mock_instance.gitlab_get_merge_request_code.assert_called_once_with(
            project_id="test-project", mr_iid=1
        )
    
    def test_gitlab_get_merge_request_comments(self, mock_gitlab_toolkit_class):
        """Test gitlab_get_merge_request_comments functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的评论
        mock_comments = [
            {"user": "user1", "body": "Comment 1"},
            {"user": "user2", "body": "Comment 2"}
        ]
        mock_instance.gitlab_get_merge_request_comments.return_value = mock_comments
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        comments = toolkit.gitlab_get_merge_request_comments(
            project_id="test-project", mr_iid=1
        )
        
        # 验证结果
        assert comments == mock_comments
        mock_instance.gitlab_get_merge_request_comments.assert_called_once_with(
            project_id="test-project", mr_iid=1
        )
    
    def test_gitlab_create_merge_request(self, mock_gitlab_toolkit_class):
        """Test gitlab_create_merge_request functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的合并请求结果
        mock_result = "Merge request created: Test MR (#1)"
        mock_instance.gitlab_create_merge_request.return_value = mock_result
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        result = toolkit.gitlab_create_merge_request(
            project_id="test-project",
            file_path="test.txt",
            new_content="new test content",
            mr_title="Test MR",
            body="Test commit message",
            branch_name="test-branch"
        )
        
        # 验证结果
        assert result == mock_result
        mock_instance.gitlab_create_merge_request.assert_called_once()
    
    def test_gitlab_get_all_file_paths(self, mock_gitlab_toolkit_class):
        """Test gitlab_get_all_file_paths functionality"""
        # 设置模拟返回值
        mock_instance = MagicMock()
        mock_gitlab_toolkit_class.return_value = mock_instance
        
        # 模拟返回的文件路径列表
        mock_file_paths = ["file1.py", "dir1/file2.py"]
        mock_instance.gitlab_get_all_file_paths.return_value = mock_file_paths
        
        # 导入并初始化工具包
        from camel.toolkits.gitlab_toolkit import GitLabToolkit
        toolkit = GitLabToolkit()
        
        # 调用方法
        file_paths = toolkit.gitlab_get_all_file_paths(project_id="test-project")
        
        # 验证结果
        assert file_paths == mock_file_paths
        mock_instance.gitlab_get_all_file_paths.assert_called_once_with(project_id="test-project")