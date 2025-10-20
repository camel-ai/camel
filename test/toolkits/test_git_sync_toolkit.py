# -*- coding: utf-8 -*-
"""
GitSyncToolkit 单元测试

用于测试Git仓库同步工具包的核心功能，包括配置验证、凭证处理、同步逻辑和错误处理。
"""

import os
import sys
import logging
import tempfile
import shutil
from unittest.mock import patch, MagicMock, call
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from camel.toolkits.git_sync_toolkit import (
    GitSyncToolkit, 
    GitSyncConfig, 
    GitPlatformType,
    SyncResult,
    ConflictResolutionStrategy
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_git_sync_toolkit')

class TestGitSyncToolkit:
    """
    GitSyncToolkit的单元测试类，测试核心同步功能和错误处理
    """
    
    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        
        # 创建基本配置文件
        with open(self.config_path, "w") as f:
            f.write('{"sync_configs": []}')
        
        # 初始化工具包
        self.toolkit = GitSyncToolkit(config_path=self.config_path)
        
        # 使用实际环境变量，不再使用模拟值
        self.env_vars = {
            "GITHUB_ACCESS_TOKEN": os.getenv("GITHUB_ACCESS_TOKEN", "test_github_token"),
            "GITEE_ACCESS_TOKEN": os.getenv("GITEE_ACCESS_TOKEN", "test_gitee_token"),
            "GITLAB_ACCESS_TOKEN": os.getenv("GITLAB_ACCESS_TOKEN", "test_gitlab_token")
        }
        
        # 创建测试配置，使用硬编码的测试令牌
        self.test_config = GitSyncConfig(
            source_platform=GitPlatformType.GITHUB,
            source_repo="owner/test-repo",
            source_credentials={'access_token': 'test_github_token'},
            target_configs=[
                {'platform': 'gitee', 'repo': 'owner/test-repo-gitee', 'credentials': {'access_token': 'test_gitee_token'}},
                {'platform': 'gitlab', 'repo': 'owner/test-repo-gitlab', 'credentials': {'access_token': 'test_gitlab_token'}}
            ],
            sync_branches=["main", "develop"],
            sync_tags=True,
            incremental_sync=True,
            conflict_resolution=ConflictResolutionStrategy.SOURCE_WINS
        )
    
    def teardown_method(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_validation(self):
        """测试配置验证功能"""
        # 测试有效配置
        errors = self.test_config.validate()
        assert len(errors) == 0, f"有效配置验证失败: {errors}"
        
        # 测试无效配置 - 没有目标仓库
        invalid_config = GitSyncConfig(
            source_platform=GitPlatformType.GITHUB,
            source_repo="owner/test-repo",
            target_configs=[]
        )
        
        errors = invalid_config.validate()
        assert len(errors) > 0, "无效配置(无目标仓库)验证失败"
    
    @patch.dict('os.environ', {})
    def test_config_with_missing_credentials(self):
        """测试缺少凭证的配置验证"""
        # 创建缺少凭证的配置
        no_cred_config = GitSyncConfig(
            source_platform=GitPlatformType.GITHUB,
            source_repo="owner/test-repo",
            target_configs=[{'platform': 'gitee', 'repo': 'owner/test-repo-gitee'}],
        )
        
        # 由于缺少凭证，验证应该失败
        errors = no_cred_config.validate()
        assert len(errors) > 0, "缺少凭证的配置验证失败"
    
    @patch('camel.toolkits.git_sync_toolkit._prepare_local_repo')
    @patch('camel.toolkits.git_sync_toolkit._sync_to_git_platform')
    @patch('camel.toolkits.git_sync_toolkit._get_platform_toolkit')
    def test_sync_repositories_successful(self, mock_get_toolkit, mock_sync, mock_prepare):
        """测试成功同步仓库"""
        # 配置模拟对象
        mock_prepare.return_value = self.temp_dir
        mock_sync.return_value = ["已同步分支main", "已同步分支develop", "已同步2个标签"]
        
        # 创建模拟的工具包对象
        mock_toolkit = MagicMock()
        mock_toolkit.get_clone_url.return_value = "https://github.com/owner/test-repo.git"
        mock_get_toolkit.return_value = mock_toolkit
        
        with patch.dict('os.environ', self.env_vars):
            # 添加配置
            config_id = self.toolkit.add_sync_config(self.test_config)
            
            # 执行同步
            result = self.toolkit.sync_repositories(config_id)
            
        # 验证结果
        assert result.success
        assert len(result.changes) > 0, "同步结果应该包含至少一个更改"
        mock_prepare.assert_called_once()
        assert mock_sync.call_count == 2  # 两个目标仓库
    
    def test_create_sync_config(self):
        """测试创建同步配置"""
        with patch.dict('os.environ', self.env_vars):
            # 使用create_sync_config方法创建配置
            config_id = self.toolkit.create_sync_config(
                source_platform="github",
                source_repo="test_owner/test_repo",
                target_configs=[
                    {"platform": "gitee", "repo": "test_owner/test_repo"},
                    {"platform": "gitlab", "repo": "test_owner/test_repo"}
                ],
                sync_branches=["main", "develop"],
                sync_tags=True,
                incremental_sync=True
            )
            
            # 验证配置已被正确创建和存储
            assert config_id is not None, "配置ID不应为None"
            
            # 检查配置是否存在
            configs = self.toolkit.list_sync_configs()
            assert len(configs) == 1, "应只存在一个配置"
            assert configs[0].id == config_id, "配置ID不匹配"
    
    def test_list_sync_configs(self):
        """测试列出所有同步配置"""
        # 添加两个配置
        config1_id = self.toolkit.add_sync_config(self.test_config)
        
        # 创建第二个配置
        config2 = GitSyncConfig(
            source_platform=GitPlatformType.GITHUB,
            source_repo="owner/another-repo",
            source_credentials={'access_token': 'test_github_token'},
            target_configs=[{'platform': 'gitee', 'repo': 'owner/another-repo'}],
        )
        config2_id = self.toolkit.add_sync_config(config2)
        
        # 获取配置列表
        configs = self.toolkit.list_sync_configs()
        
        # 验证结果
        assert len(configs) == 2, "应返回两个配置"
        config_ids = [config.id for config in configs]
        assert config1_id in config_ids, "第一个配置ID不在列表中"
        assert config2_id in config_ids, "第二个配置ID不在列表中"
    
    def test_delete_sync_config(self):
        """测试删除同步配置"""
        # 添加配置
        config_id = self.toolkit.add_sync_config(self.test_config)
        
        # 验证配置存在
        configs_before = self.toolkit.list_sync_configs()
        assert len(configs_before) == 1, "配置添加失败"
        
        # 删除配置
        result = self.toolkit.delete_sync_config(config_id)
        
        # 验证配置已删除
        assert result, "删除配置失败"
        configs_after = self.toolkit.list_sync_configs()
        assert len(configs_after) == 0, "配置删除后仍存在"
    
    def test_incremental_sync_flag(self):
        """测试增量同步标志的处理"""
        with patch.dict('os.environ', self.env_vars):
            # 创建带增量同步的配置
            inc_config_id = self.toolkit.create_sync_config(
                source_platform="github",
                source_repo="owner/test-repo",
                target_configs=[{"platform": "gitee", "repo": "owner/test-repo"}],
                incremental_sync=True
            )
            
            # 创建不带增量同步的配置
            full_config_id = self.toolkit.create_sync_config(
                source_platform="github",
                source_repo="owner/another-repo",
                target_configs=[{"platform": "gitee", "repo": "owner/another-repo"}],
                incremental_sync=False
            )
            
            # 获取配置并验证
            configs = self.toolkit.list_sync_configs()
            inc_config = next(c for c in configs if c.id == inc_config_id)
            full_config = next(c for c in configs if c.id == full_config_id)
            
            assert inc_config.incremental_sync, "增量同步标志设置错误"
            assert not full_config.incremental_sync, "增量同步标志设置错误"
    
    def test_get_tools(self):
        """测试获取工具列表"""
        tools = self.toolkit.get_tools()
        
        # 验证工具列表不为空
        assert isinstance(tools, list), "get_tools应该返回列表"
        assert len(tools) > 0, "工具列表不应为空"
        
        # 检查关键工具是否存在
        tool_names = [tool.get_function_name() for tool in tools]
        expected_tools = [
            "git_sync_create_config",
            "git_sync_list_configs",
            "git_sync_delete_config",
            "git_sync_repositories"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"期望的工具{expected_tool}不存在"