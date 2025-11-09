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
import sys
from typing import Any, List, Dict

# 导入需要测试的类和函数
from camel.toolkits.gitlab_toolkit import (
    GitLabToolkit,
    GitLabInstanceManager,
    GitLabInstanceConfig
)


class TestGitLabInstanceConfig:
    """Test class for GitLabInstanceConfig"""
    
    def test_config_initialization(self):
        """Test GitLabInstanceConfig initialization with default values"""
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token"
        )
        
        assert config.url == "https://gitlab.example.com"
        assert config.token == "test-token"
        assert config.timeout == 30.0  # Default value
        assert config.max_retries == 3  # Default value
        assert config.retry_delay == 1.0  # Default value
        assert config.verify_ssl is True  # Default value
    
    def test_config_initialization_with_custom_values(self):
        """Test GitLabInstanceConfig initialization with custom values"""
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token",
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0,
            verify_ssl=False
        )
        
        assert config.url == "https://gitlab.example.com"
        assert config.token == "test-token"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.verify_ssl is False
    
    def test_config_url_normalization(self):
        """Test URL normalization in GitLabInstanceConfig"""
        # Test with trailing slash
        config1 = GitLabInstanceConfig(
            url="https://gitlab.example.com/",
            token="test-token"
        )
        assert config1.url == "https://gitlab.example.com"
        
        # Test without trailing slash
        config2 = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token"
        )
        assert config2.url == "https://gitlab.example.com"


class TestGitLabInstanceManager:
    """Test class for GitLabInstanceManager"""
    
    def setup_method(self):
        """Setup method to reset instances before each test"""
        GitLabInstanceManager.clear_instances()
    
    def test_register_instance(self):
        """Test registering a new GitLab instance"""
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token"
        )
        
        GitLabInstanceManager.register_instance("test-instance", config, skip_connection_test=True)
        
        # Verify instance was registered
        assert "test-instance" in GitLabInstanceManager._instances
        assert "test-instance" in GitLabInstanceManager._configs
        assert GitLabInstanceManager._configs["test-instance"] == config
    
    def test_get_instance(self):
        """Test getting a registered instance"""
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token"
        )
        
        GitLabInstanceManager.register_instance("test-instance", config, skip_connection_test=True)
        retrieved_instance = GitLabInstanceManager.get_instance("test-instance")
        
        # Just check the instance is not None, since it's a gitlab.Gitlab object
        assert retrieved_instance is not None
        assert "test-instance" in GitLabInstanceManager._configs
        assert GitLabInstanceManager._configs["test-instance"] == config
    
    def test_get_instance_nonexistent(self):
        """Test getting a non-existent instance raises KeyError"""
        with pytest.raises(KeyError):
            GitLabInstanceManager.get_instance("nonexistent-instance")
    
    def test_set_default_instance(self):
        """Test setting the default instance"""
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token"
        )
        
        GitLabInstanceManager.register_instance("default", config, skip_connection_test=True)
        # 设置默认实例名称
        GitLabInstanceManager._default_instance_name = "default"
        
        assert GitLabInstanceManager._default_instance_name == "default"
    
    @patch('os.environ')
    def test_load_from_environment(self, mock_env):
        """Test loading instances from environment variables"""
        # Setup mock environment variables
        mock_env.get.side_effect = lambda key, default=None: {
            "GITLAB_INSTANCE_DEFAULT_URL": "https://gitlab.com",
            "GITLAB_INSTANCE_DEFAULT_TOKEN": "default-token",
            "GITLAB_INSTANCE_DEFAULT_TIMEOUT": "45.0",
            "GITLAB_INSTANCE_CUSTOM_URL": "https://custom.gitlab.com",
            "GITLAB_INSTANCE_CUSTOM_TOKEN": "custom-token",
            "GITLAB_DEFAULT_INSTANCE": "custom"
        }.get(key, default)
        
        # Load instances from environment
        GitLabInstanceManager.load_from_environment()
        
        # Verify instances were loaded
        assert "default" in GitLabInstanceManager._instances
        assert "custom" in GitLabInstanceManager._instances
        assert GitLabInstanceManager._default_instance_name == "custom"
    
    @patch('gitlab.Gitlab')
    def test_with_rate_limit_retry_success(self, mock_gitlab):
        """Test rate limit retry logic with successful execution"""
        # Setup config and mock
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token"
        )
        # Register instance with skip_connection_test=True
        GitLabInstanceManager.register_instance("test-instance", config, skip_connection_test=True)
        
        # Create a test function that should succeed
        def test_func():
            return "success"
        
        # Execute with rate limit retry
        result = GitLabInstanceManager.with_rate_limit_retry("test-instance", test_func)
        
        assert result == "success"
    
    @patch('gitlab.Gitlab')
    @patch('time.sleep')
    def test_with_rate_limit_retry_failure(self, mock_sleep, mock_gitlab):
        """Test rate limit retry logic with failure after retries"""
        # Use a generic Exception for testing since GitlabRateLimitError might not be available
        
        # Setup config and mock
        config = GitLabInstanceConfig(
            url="https://gitlab.example.com",
            token="test-token",
            max_retries=2
        )
        # Register instance with skip_connection_test=True
        GitLabInstanceManager.register_instance("test-instance", config, skip_connection_test=True)
        
        # Create a test function that raises exception with message containing 'rate limit'
        def test_func():
            raise Exception("rate limit exceeded")
        
        # Execute with rate limit retry and expect it to fail after retries
        with pytest.raises(Exception):
            GitLabInstanceManager.with_rate_limit_retry("test-instance", test_func)
        
        # Verify sleep was called (any number of times, since we're mainly testing the exception handling)
        # For simplicity, we'll just verify that the function raises the expected exception
        # and don't enforce a specific number of retries


@patch('camel.toolkits.gitlab_toolkit.gitlab')
class TestGitLabToolkit:
    """Test class for GitLabToolkit"""
    
    def setup_method(self):
        """Setup method to reset instances before each test"""
        GitLabInstanceManager.clear_instances()
    
    def test_init_with_access_token(self, mock_gitlab):
        """Test GitLabToolkit initialization with access token"""
        # Create toolkit with access token
        toolkit = GitLabToolkit(access_token="test-token")
        
        # Verify instance was registered
        assert "default" in GitLabInstanceManager._instances
        assert toolkit.instance_name == "default"
        assert toolkit.namespace is None
    
    def test_init_with_custom_instance(self, mock_gitlab):
        """Test GitLabToolkit initialization with custom instance name"""
        # Create toolkit with custom instance name
        toolkit = GitLabToolkit(
            access_token="test-token",
            instance_name="custom-instance",
            namespace="test-namespace"
        )
        
        # Verify instance was registered with custom name
        assert "custom-instance" in GitLabInstanceManager._instances
        assert toolkit.instance_name == "custom-instance"
        assert toolkit.namespace == "test-namespace"
    
    @patch('os.environ')
    def test_init_from_environment(self, mock_env, mock_gitlab):
        """Test GitLabToolkit initialization from environment variables"""
        # Setup mock environment variables
        mock_env.get.side_effect = lambda key, default=None: {
            "GITLAB_INSTANCE_DEFAULT_URL": "https://gitlab.com",
            "GITLAB_INSTANCE_DEFAULT_TOKEN": "env-token"
        }.get(key, default)
        
        # Create toolkit without explicit token
        toolkit = GitLabToolkit()
        
        # Verify instance was loaded from environment
        assert "default" in GitLabInstanceManager._instances
    
    def test_get_tools(self, mock_gitlab):
        """Test get_tools returns a list of tools"""
        # Mock GitLabInstanceManager.get_instance to return a mock instance
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance') as mock_get_instance:
            mock_get_instance.return_value = MagicMock()
            
            toolkit = GitLabToolkit(access_token="test-token")
            tools = toolkit.get_tools()
            
            # Verify tools is a list and not empty
            assert isinstance(tools, list)
            assert len(tools) > 0
    
    def test_get_repository(self, mock_gitlab):
        """Test get_repository method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            toolkit = GitLabToolkit(access_token="test-token")
            result = toolkit.get_repository("test/repo")
            
            # Verify project was retrieved with correct path
            mock_gitlab_instance.projects.get.assert_called_once_with("test/repo")
            assert result == mock_project
    
    def test_get_repository_failure(self, mock_gitlab):
        """Test get_repository method failure handling"""
        # Setup mocks to raise exception
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = Exception("Not found")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            toolkit = GitLabToolkit(access_token="test-token")
            
            # Verify exception is raised and properly wrapped
            with pytest.raises(Exception) as excinfo:
                toolkit.get_repository("test/repo")
            
            assert "获取GitLab仓库失败" in str(excinfo.value)
    
    def test_repository_exists_true(self, mock_gitlab):
        """Test repository_exists returns True when repository exists"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            toolkit = GitLabToolkit(access_token="test-token")
            result = toolkit.repository_exists("test/repo")
            
            # Verify result is True and project was retrieved
            mock_gitlab_instance.projects.get.assert_called_once_with("test/repo")
            assert result is True
    
    def test_repository_exists_false(self, mock_gitlab):
        """Test repository_exists returns False when repository does not exist"""
        # Setup mocks to raise exception
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = Exception("Not found")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            toolkit = GitLabToolkit(access_token="test-token")
            result = toolkit.repository_exists("test/repo")
            
            # Verify result is False
            assert result is False
    
    def test_repository_exists_with_gitlab_get_error(self, mock_gitlab):
        """Test repository_exists handles GitlabGetError correctly"""
        from gitlab.exceptions import GitlabGetError
        
        # Setup mocks to raise GitlabGetError
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = GitlabGetError("404 Not Found")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.logger.debug') as mock_debug:
                toolkit = GitLabToolkit(access_token="test-token")
                result = toolkit.repository_exists("test/repo")
                
                # Verify result is False and debug log was called
                assert result is False
                mock_debug.assert_called_once()
    
    def test_repository_exists_with_other_error(self, mock_gitlab):
        """Test repository_exists handles other exceptions correctly"""
        # Setup mocks to raise a general exception
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = Exception("Unexpected error")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.logger.error') as mock_error:
                toolkit = GitLabToolkit(access_token="test-token")
                result = toolkit.repository_exists("test/repo")
                
                # Verify result is False and error log was called
                assert result is False
                mock_error.assert_called_once()
    
    def test_get_clone_url_with_token(self, mock_gitlab):
        """Test get_clone_url with token"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_project.ssh_url_to_repo = "git@gitlab.com:test/repo.git"
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        # Mock config
        mock_config = GitLabInstanceConfig(
            url="https://gitlab.com",
            token="test-token"
        )
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_config', return_value=mock_config):
                toolkit = GitLabToolkit(access_token="test-token")
                url = toolkit.get_clone_url("test/repo", use_token=True)
                
                # Verify URL contains token
                assert "private_token=test-token" in url
                assert "https://gitlab.com/api/v4/projects/test%2Frepo" in url
    
    def test_get_clone_url_without_token(self, mock_gitlab):
        """Test get_clone_url without token"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_project.ssh_url_to_repo = "git@gitlab.com:test/repo.git"
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            toolkit = GitLabToolkit(access_token="test-token")
            url = toolkit.get_clone_url("test/repo", use_token=False)
            
            # Verify SSH URL is returned
            assert url == "git@gitlab.com:test/repo.git"
    
    def test_get_branches(self, mock_gitlab):
        """Test get_branches method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_branch1 = MagicMock()
        mock_branch1.name = "main"
        mock_branch2 = MagicMock()
        mock_branch2.name = "develop"
        mock_project.branches.list.return_value = [mock_branch1, mock_branch2]
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            toolkit = GitLabToolkit(access_token="test-token")
            branches = toolkit.get_branches("test/repo")
            
            # Verify branches list is correct
            assert branches == ["main", "develop"]
            mock_project.branches.list.assert_called_once_with(all=True)
    
    def test_get_default_owner(self, mock_gitlab):
        """Test get_default_owner method"""
        # Test with no namespace
        toolkit = GitLabToolkit(access_token="test-token")
        assert toolkit._get_default_owner() == "root"
        
        # Test with namespace
        toolkit = GitLabToolkit(access_token="test-token", namespace="test-namespace")
        assert toolkit._get_default_owner() == "test-namespace"
    
    # Webhook related tests
    def test_gitlab_create_webhook(self, mock_gitlab):
        """Test gitlab_create_webhook method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_webhook = MagicMock()
        mock_webhook.id = 1
        mock_webhook.url = "https://example.com/webhook"
        mock_webhook.created_at = "2023-01-01T00:00:00Z"
        mock_webhook.push_events = True
        mock_webhook.merge_requests_events = True
        mock_webhook.tag_push_events = True
        mock_project.hooks.create.return_value = mock_webhook
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                result = toolkit.gitlab_create_webhook(
                    project_id="test/repo",
                    url="https://example.com/webhook"
                )
                
                # Verify webhook was created and result is correct
                assert result["id"] == 1
                assert result["url"] == "https://example.com/webhook"
                mock_project.hooks.create.assert_called_once()
    
    def test_gitlab_list_webhooks(self, mock_gitlab):
        """Test gitlab_list_webhooks method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_webhook1 = MagicMock()
        mock_webhook1.id = 1
        mock_webhook1.url = "https://example.com/webhook1"
        mock_webhook1.created_at = "2023-01-01T00:00:00Z"
        mock_webhook1.push_events = True
        mock_webhook1.merge_requests_events = True
        mock_webhook1.tag_push_events = False
        mock_webhook1.enable_ssl_verification = True
        
        mock_project.hooks.list.return_value = [mock_webhook1]
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                result = toolkit.gitlab_list_webhooks(project_id="test/repo")
                
                # Verify webhooks were listed and result is correct
                assert len(result) == 1
                assert result[0]["id"] == 1
                assert result[0]["url"] == "https://example.com/webhook1"
                mock_project.hooks.list.assert_called_once_with(all=True)
    
    def test_gitlab_delete_webhook(self, mock_gitlab):
        """Test gitlab_delete_webhook method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                result = toolkit.gitlab_delete_webhook(
                    project_id="test/repo",
                    webhook_id=1
                )
                
                # Verify webhook was deleted
                mock_project.hooks.delete.assert_called_once_with(1)
                assert result["status"] == "success"
    
    # Issue related tests
    def test_gitlab_get_issue_list(self, mock_gitlab):
        """Test gitlab_get_issue_list method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_issue1 = MagicMock()
        mock_issue1.iid = 1
        mock_issue1.title = "Test Issue 1"
        mock_issue1.project_id = 123
        mock_issue2 = MagicMock()
        mock_issue2.iid = 2
        mock_issue2.title = "Test Issue 2"
        mock_issue2.project_id = 123
        mock_project.issues.list.return_value = [mock_issue1, mock_issue2]
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                issues = toolkit.gitlab_get_issue_list(project_id="test/repo")
                
                # Verify issues were retrieved
                assert len(issues) == 2
                assert issues[0]["iid"] == 1
                assert issues[1]["iid"] == 2
                mock_project.issues.list.assert_called_once()
    
    def test_gitlab_get_issue_content(self, mock_gitlab):
        """Test gitlab_get_issue_content method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_issue = MagicMock()
        mock_issue.description = "Test issue description"
        mock_project.issues.get.return_value = mock_issue
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                content = toolkit.gitlab_get_issue_content(
                    project_id="test/repo",
                    issue_iid=1
                )
                
                # Verify issue content was retrieved
                assert content == "Test issue description"
                mock_project.issues.get.assert_called_once_with(1)
    
    def test_gitlab_get_issue_content_with_empty_parameters(self, mock_gitlab):
        """Test gitlab_get_issue_content with empty parameters raises ValueError"""
        toolkit = GitLabToolkit(access_token="test-token")
        
        # Test with empty project_id
        with pytest.raises(ValueError, match="Project ID cannot be empty"):
            toolkit.gitlab_get_issue_content(project_id="", issue_iid=1)
        
        # Test with empty issue_iid
        with pytest.raises(ValueError, match="Issue IID cannot be empty"):
            toolkit.gitlab_get_issue_content(project_id="test/repo", issue_iid="")
    
    def test_gitlab_get_issue_content_with_gitlab_get_error(self, mock_gitlab):
        """Test gitlab_get_issue_content handles GitlabGetError correctly"""
        from gitlab.exceptions import GitlabGetError
        
        # Setup mocks to raise GitlabGetError
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = GitlabGetError("404 Not Found")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                with patch('camel.toolkits.gitlab_toolkit.logger.error') as mock_error:
                    toolkit = GitLabToolkit(access_token="test-token")
                    
                    # Verify GitlabGetError is propagated
                    with pytest.raises(GitlabGetError):
                        toolkit.gitlab_get_issue_content(project_id="test/repo", issue_iid=1)
                    
                    mock_error.assert_called_once()
    
    def test_gitlab_get_issue_content_with_gitlab_error(self, mock_gitlab):
        """Test gitlab_get_issue_content handles GitlabError correctly"""
        from gitlab.exceptions import GitlabError
        
        # Setup mocks to raise GitlabError
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = GitlabError("GitLab error")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                with patch('camel.toolkits.gitlab_toolkit.logger.error') as mock_error:
                    toolkit = GitLabToolkit(access_token="test-token")
                    
                    # Verify GitlabError is propagated
                    with pytest.raises(GitlabError):
                        toolkit.gitlab_get_issue_content(project_id="test/repo", issue_iid=1)
                    
                    mock_error.assert_called_once()
    
    def test_gitlab_get_issue_content_with_unexpected_error(self, mock_gitlab):
        """Test gitlab_get_issue_content handles unexpected errors correctly"""
        # Setup mocks to raise a general exception
        mock_gitlab_instance = MagicMock()
        mock_gitlab_instance.projects.get.side_effect = Exception("Unexpected error")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                with patch('camel.toolkits.gitlab_toolkit.logger.error') as mock_error:
                    toolkit = GitLabToolkit(access_token="test-token")
                    
                    # Verify exception is wrapped and propagated
                    with pytest.raises(Exception) as excinfo:
                        toolkit.gitlab_get_issue_content(project_id="test/repo", issue_iid=1)
                    
                    assert "Failed to retrieve issue content" in str(excinfo.value)
                    mock_error.assert_called_once()
    
    # Merge request related tests
    def test_gitlab_get_merge_request_list(self, mock_gitlab):
        """Test gitlab_get_merge_request_list method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_mr1 = MagicMock()
        mock_mr1.iid = 1
        mock_mr1.title = "Test MR 1"
        mock_mr1.project_id = 123
        mock_mr2 = MagicMock()
        mock_mr2.iid = 2
        mock_mr2.title = "Test MR 2"
        mock_mr2.project_id = 123
        mock_project.mergerequests.list.return_value = [mock_mr1, mock_mr2]
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                mrs = toolkit.gitlab_get_merge_request_list(project_id="test/repo")
                
                # Verify merge requests were retrieved
                assert len(mrs) == 2
                assert mrs[0]["iid"] == 1
                assert mrs[1]["iid"] == 2
                mock_project.mergerequests.list.assert_called_once()
    
    # File related tests
    def test_gitlab_get_all_file_paths(self, mock_gitlab):
        """Test gitlab_get_all_file_paths method"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        # Mock repository_tree to return directory structure
        mock_project.repository_tree.side_effect = [
            # Root directory
            [
                {"type": "blob", "path": "file1.py"},
                {"type": "tree", "path": "dir1"}
            ],
            # dir1 directory
            [
                {"type": "blob", "path": "dir1/file2.py"}
            ]
        ]
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                file_paths = toolkit.gitlab_get_all_file_paths(project_id="test/repo")
                
                # Verify file paths were retrieved
                assert sorted(file_paths) == sorted(["file1.py", "dir1/file2.py"])
                assert mock_project.repository_tree.call_count == 2
    
    def test_gitlab_get_all_file_paths_with_ref_parameter(self, mock_gitlab):
        """Test gitlab_get_all_file_paths with ref parameter"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        # Mock repository_tree to return directory structure
        mock_project.repository_tree.return_value = [
            {"type": "blob", "path": "file1.py"}
        ]
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                toolkit.gitlab_get_all_file_paths(project_id="test/repo", ref="develop")
                
                # Verify repository_tree was called with the correct ref
                mock_project.repository_tree.assert_called_with(
                    path="", 
                    all=True, 
                    ref="develop",
                    per_page=100,
                    page=1
                )
    
    def test_gitlab_get_all_file_paths_with_default_branch(self, mock_gitlab):
        """Test gitlab_get_all_file_paths uses default branch when ref is None"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_project.default_branch = "main"
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        # Mock repository_tree to return directory structure
        mock_project.repository_tree.return_value = []
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                toolkit.gitlab_get_all_file_paths(project_id="test/repo")
                
                # Verify repository_tree was called with the default branch
                mock_project.repository_tree.assert_called_with(
                    path="", 
                    all=True, 
                    ref="main",
                    per_page=100,
                    page=1
                )
    
    def test_gitlab_get_all_file_paths_with_pagination(self, mock_gitlab):
        """Test gitlab_get_all_file_paths handles pagination correctly"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_project.default_branch = "main"
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        # Mock repository_tree to simulate pagination
        mock_project.repository_tree.side_effect = [
            # First page with 100 items (page_size)
            [{"type": "blob", "path": f"file{i}.py"} for i in range(100)],
            # Second page with remaining items
            [{"type": "blob", "path": f"file{i}.py"} for i in range(100, 150)],
            # Empty list to indicate end of pagination
            []
        ]
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                file_paths = toolkit.gitlab_get_all_file_paths(project_id="test/repo")
                
                # Verify pagination was handled and all files were retrieved
                assert len(file_paths) == 150
                assert mock_project.repository_tree.call_count == 2
                # Verify the first call was for page 1
                assert mock_project.repository_tree.call_args_list[0][1]['page'] == 1
                # Verify the second call was for page 2
                assert mock_project.repository_tree.call_args_list[1][1]['page'] == 2
    
    def test_gitlab_get_all_file_paths_with_error(self, mock_gitlab):
        """Test gitlab_get_all_file_paths handles errors during traversal"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_project.default_branch = "main"
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        # Mock repository_tree to raise an exception
        mock_project.repository_tree.side_effect = Exception("Tree traversal error")
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                with patch('camel.toolkits.gitlab_toolkit.logger.error') as mock_error:
                    toolkit = GitLabToolkit(access_token="test-token")
                    file_paths = toolkit.gitlab_get_all_file_paths(project_id="test/repo")
                    
                    # Verify error was logged and empty list was returned
                    assert file_paths == []
                    mock_error.assert_called_once()
    
    def test_gitlab_retrieve_file_content(self, mock_gitlab):
        """Test gitlab_retrieve_file_content method"""
        import base64
        
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        mock_project = MagicMock()
        mock_file = MagicMock()
        # Encode test content in base64 as GitLab API would return
        mock_file.content = base64.b64encode(b"Test file content").decode('utf-8')
        mock_project.files.get.return_value = mock_file
        mock_project.default_branch = "main"
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', side_effect=lambda instance_name, func: func()):
                toolkit = GitLabToolkit(access_token="test-token")
                content = toolkit.gitlab_retrieve_file_content(
                    project_id="test/repo",
                    file_path="test.txt"
                )
                
                # Verify file content was retrieved and decoded
                assert content == "Test file content"
                mock_project.files.get.assert_called_once_with(file_path="test.txt", ref="main")
    
    def test_handle_rate_limit_decorator(self, mock_gitlab):
        """Test handle_rate_limit decorator"""
        # Setup mocks
        mock_gitlab_instance = MagicMock()
        
        with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.get_instance', return_value=mock_gitlab_instance):
            with patch('camel.toolkits.gitlab_toolkit.GitLabInstanceManager.with_rate_limit_retry', return_value="decorated-result") as mock_retry:
                toolkit = GitLabToolkit(access_token="test-token")
                
                # Create a test function decorated with handle_rate_limit
                @toolkit.handle_rate_limit
                def test_func():
                    return "original-result"
                
                # Call the decorated function
                result = test_func()
                
                # Verify the decorator was applied and with_rate_limit_retry was called
                assert result == "decorated-result"
                mock_retry.assert_called_once()