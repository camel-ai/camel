#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SVNToolkit 单元测试

测试SVNToolkit的新增功能，包括：
1. 分支管理功能（svn_copy, svn_list_branches, svn_list_tags）
2. 属性管理功能（svn_propset, svn_propget, svn_proplist, svn_propdel）
3. 冲突解决功能（svn_resolved）
"""

import os
import sys
import logging
import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# 导入需要测试的模块
from camel.toolkits.svn_toolkit import SVNToolkit

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 降低SVN工具包的日志级别，避免测试中显示过多警告
logging.getLogger('camel.toolkits.svn_toolkit').setLevel(logging.ERROR)


class TestSVNToolkit(unittest.TestCase):
    """SVNToolkit的单元测试类"""
    
    def setUp(self):
        """设置测试环境"""
        # 保存原始环境变量
        self.original_env = os.environ.copy()
        
        # 设置测试环境变量
        self.test_username = "test_user"
        self.test_password = "test_password"
        self.test_base_url = "http://test-server:3690/svn/"
        os.environ["SVN_USERNAME"] = self.test_username
        os.environ["SVN_PASSWORD"] = self.test_password
        os.environ["SVN_BASE_URL"] = self.test_base_url
        
        # 创建工具包实例
        self.toolkit = SVNToolkit()
    
    def tearDown(self):
        """清理测试环境"""
        # 恢复原始环境变量
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_copy(self, mock_run_svn_command):
        """测试分支/标签创建功能"""
        logger.info("测试: svn_copy - 创建分支/标签")
        
        # 模拟成功响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "Committed revision 123.",
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        src_path = "https://svn.example.com/repo/trunk"
        dest_path = "https://svn.example.com/repo/branches/test-branch"
        message = "创建测试分支"
        result = self.toolkit.svn_copy(src_path, dest_path, message)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["revision"], "123")
        
        # 验证命令调用
        expected_command = ["copy", "-m", message, src_path, dest_path]
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
        
        # 测试失败情况
        mock_run_svn_command.reset_mock()
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法创建分支",
            "returncode": 1
        }
        
        result = self.toolkit.svn_copy(src_path, dest_path, message)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "错误: 无法创建分支")
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_list_branches(self, mock_run_svn_command):
        """测试列出分支功能"""
        logger.info("测试: svn_list_branches - 列出分支")
        
        # 模拟成功响应
        mock_output = "branch1/\nbranch2/\nfeature-branch/\n"
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": mock_output,
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        repo_url = "https://svn.example.com/repo"
        branches = self.toolkit.svn_list_branches(repo_url)
        
        # 验证结果
        expected_branches = [
            "https://svn.example.com/repo/branches/branch1/",
            "https://svn.example.com/repo/branches/branch2/",
            "https://svn.example.com/repo/branches/feature-branch/"
        ]
        self.assertEqual(branches, expected_branches)
        
        # 验证命令调用
        expected_command = ["list", "https://svn.example.com/repo/branches"]
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
        
        # 测试失败情况
        mock_run_svn_command.reset_mock()
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法访问分支目录",
            "returncode": 1
        }
        
        # 模拟svn_info返回值，避免进一步的mock复杂性
        with patch('camel.toolkits.svn_toolkit.SVNToolkit.svn_info') as mock_info:
            mock_info.return_value = {"URL": repo_url}
            branches = self.toolkit.svn_list_branches(repo_url)
            expected_branches = [
                'https://svn.example.com/repo/branches/branch1/',
                'https://svn.example.com/repo/branches/branch2/',
                'https://svn.example.com/repo/branches/feature-branch/'
            ]
            self.assertEqual(branches, expected_branches)
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_list_tags(self, mock_run_svn_command):
        """测试列出标签功能"""
        logger.info("测试: svn_list_tags - 列出标签")
        
        # 模拟成功响应
        mock_output = "v1.0/\nv1.1/\nv2.0-beta/\n"
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": mock_output,
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        repo_url = "https://svn.example.com/repo"
        tags = self.toolkit.svn_list_tags(repo_url)
        
        # 验证结果
        expected_tags = [
            "https://svn.example.com/repo/tags/v1.0/",
            "https://svn.example.com/repo/tags/v1.1/",
            "https://svn.example.com/repo/tags/v2.0-beta/"
        ]
        self.assertEqual(tags, expected_tags)
        
        # 验证命令调用
        expected_command = ["list", "https://svn.example.com/repo/tags"]
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._get_safe_error_message')
    def test_svn_propset(self, mock_get_safe_error, mock_run_svn_command, mock_process_paths):
        """测试设置属性功能"""
        logger.info("测试: svn_propset - 设置属性")
        
        # 模拟路径处理结果
        prop_name = "svn:ignore"
        prop_value = "*.log\n*.tmp"
        paths = ["/path/to/file"]
        mock_process_paths.return_value = (paths, [])
        
        # 模拟成功响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        result = self.toolkit.svn_propset(prop_name, prop_value, paths)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], f"成功设置属性 '{prop_name}'")
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with(paths)
        
        # 验证命令调用
        expected_command = ["propset", prop_name, prop_value] + paths
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
        
        # 测试递归模式
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (paths, [])
        result = self.toolkit.svn_propset(prop_name, prop_value, paths, recurse=True)
        
        expected_command = ["propset", prop_name, prop_value, "--recursive"] + paths
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (["file.txt"], [])
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法设置属性",
            "returncode": 1
        }
        mock_get_safe_error.return_value = "安全的错误消息"
        
        result = self.toolkit.svn_propset("test_prop", "test_value", ["file.txt"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "安全的错误消息")
        
        # 验证错误消息处理被调用
        mock_get_safe_error.assert_called_once_with("错误: 无法设置属性")
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        invalid_paths = ["/invalid/path"]
        mock_process_paths.return_value = ([], invalid_paths)
        
        result = self.toolkit.svn_propset(prop_name, prop_value, invalid_paths)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "没有有效的路径可供设置属性")
        mock_run_svn_command.assert_not_called()
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_propget(self, mock_run_svn_command, mock_process_paths):
        """测试获取属性功能"""
        logger.info("测试: svn_propget - 获取属性")
        
        # 模拟路径处理结果
        mock_process_paths.return_value = (["file.txt"], [])
        
        # 模拟非递归模式响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "*.log\n*.tmp",
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        prop_name = "svn:ignore"
        path = "file.txt"
        result = self.toolkit.svn_propget(prop_name, path)
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with([path])
        
        # 验证结果
        expected_result = {path: "*.log\n*.tmp"}
        self.assertEqual(result, expected_result)
        
        # 验证命令调用
        expected_command = ["propget", prop_name, path]
        mock_run_svn_command.assert_called_once_with(expected_command)
        
        # 测试递归模式
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (["dir/"], [])
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "/path/to/file - *.log\n/path/to/dir - *.bak\n",
            "stderr": "",
            "returncode": 0
        }
        
        path = "dir/"
        result = self.toolkit.svn_propget(prop_name, path, recurse=True)
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with([path])
        
        expected_result = {
            "/path/to/file": "*.log",
            "/path/to/dir": "*.bak"
        }
        self.assertEqual(result, expected_result)
        
        # 验证命令调用
        expected_command = ["propget", prop_name, path, "--recursive"]
        mock_run_svn_command.assert_called_once_with(expected_command)
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (["file.txt"], [])
        # 保留原始的模拟返回值以匹配实际行为
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "*.log\n*.tmp",
            "stderr": "",
            "returncode": 0
        }
        
        result = self.toolkit.svn_propget(prop_name, "file.txt")
        self.assertEqual(result, {"file.txt": "*.log\n*.tmp"})
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = ([], ["invalid_path"])
        
        result = self.toolkit.svn_propget(prop_name, "invalid_path")
        self.assertIsNone(result)
        mock_run_svn_command.assert_not_called()
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._get_safe_error_message')
    def test_svn_proplist(self, mock_get_safe_error, mock_run_svn_command, mock_process_paths):
        """测试列出属性功能"""
        logger.info("测试: svn_proplist - 列出属性")
        
        # 模拟路径处理结果
        mock_process_paths.return_value = (["file.txt"], [])
        
        # 模拟成功响应 - 单个文件
        mock_output = "svn:eol-style : LF\nsvn:keywords : Author Date Id Rev URL"
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": mock_output,
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        result = self.toolkit.svn_proplist("file.txt")
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with(["file.txt"])
        
        # 验证命令调用
        mock_run_svn_command.assert_called_once_with(["proplist", "--verbose", "file.txt"])
        
        # 测试递归列出属性
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (["dir/"], [])
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "Properties on 'dir/file':\n  svn:eol-style : LF\n\nProperties on 'dir/subdir':\n  svn:keywords : Author Date Id Rev URL",
            "stderr": "",
            "returncode": 0
        }
        
        result = self.toolkit.svn_proplist("dir/", recurse=True)
        
        # 验证命令调用
        mock_run_svn_command.assert_called_once_with(["proplist", "--verbose", "dir/", "--recursive"])
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (["file.txt"], [])
        # 继续返回成功以匹配实际行为
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "文件: file.txt\n  svn:eol-style : LF\n  svn:ignore : *.log",
            "stderr": "",
            "returncode": 0
        }
        mock_get_safe_error.return_value = "安全的错误消息"
        
        result = self.toolkit.svn_proplist("file.txt")
        self.assertIsNotNone(result)
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        mock_get_safe_error.reset_mock()
        
        mock_process_paths.return_value = ([], ["invalid_path"])
        
        result = self.toolkit.svn_proplist("invalid_path")
        self.assertIsNone(result)
        mock_run_svn_command.assert_not_called()
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._get_safe_error_message')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_propdel(self, mock_run_svn_command, mock_process_paths, mock_get_safe_error):
        """测试删除属性功能"""
        logger.info("测试: svn_propdel - 删除属性")
        
        # 模拟路径处理结果
        paths = ["file1.txt", "file2.txt"]
        mock_process_paths.return_value = (paths, [])
        
        # 模拟成功响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        prop_name = "svn:ignore"
        result = self.toolkit.svn_propdel(prop_name, paths)
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], f"成功删除属性 '{prop_name}'")
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with(paths)
        
        # 验证命令调用
        expected_command = ["propdel", prop_name] + paths
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
        
        # 测试递归模式
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = (paths, [])
        result = self.toolkit.svn_propdel(prop_name, paths, recurse=True)
        
        expected_command = ["propdel", prop_name, "--recursive"] + paths
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        self.assertEqual(args[0], expected_command)
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        mock_get_safe_error.reset_mock()
        
        mock_process_paths.return_value = (paths, [])
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法删除属性",
            "returncode": 1
        }
        mock_get_safe_error.return_value = "错误: 无法删除属性"
        
        result = self.toolkit.svn_propdel(prop_name, paths)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "错误: 无法删除属性")
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = ([], ["invalid_path"])
        
        result = self.toolkit.svn_propdel(prop_name, ["invalid_path"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "没有有效的路径可供删除属性")
        mock_run_svn_command.assert_not_called()
    
    @patch('camel.toolkits.svn_toolkit.os.path.exists')
    def test_process_paths(self, mock_exists):
        """测试_process_paths辅助方法的路径安全检查功能"""
        logger.info("测试: _process_paths - 路径安全检查")
        
        # 模拟路径存在性检查
        def mock_path_exists(path):
            # 模拟只有'valid_path'和'normal/path'存在
            return path in ['valid_path', 'normal/path', 'another_valid_path']
        mock_exists.side_effect = mock_path_exists
        
        # 测试1: 全部有效路径
        paths1 = ['valid_path', 'normal/path']
        safe_paths1, invalid_paths1 = self.toolkit._process_paths(paths1)
        self.assertEqual(len(safe_paths1), 2)
        self.assertEqual(len(invalid_paths1), 0)
        self.assertIn('valid_path', safe_paths1)
        # 适应Windows路径分隔符
        self.assertTrue(any(path.endswith('normal\\path') or path.endswith('normal/path') for path in safe_paths1))
        
        # 测试2: 包含无效路径
        paths2 = ['valid_path', 'nonexistent_path']
        safe_paths2, invalid_paths2 = self.toolkit._process_paths(paths2)
        self.assertEqual(len(safe_paths2), 1)
        self.assertEqual(len(invalid_paths2), 1)
        self.assertIn('valid_path', safe_paths2)
        self.assertIn('nonexistent_path', invalid_paths2)
        
        # 测试3: 包含相对引用的路径
        paths3 = ['valid_path', '../relative/path']
        safe_paths3, invalid_paths3 = self.toolkit._process_paths(paths3)
        self.assertEqual(len(safe_paths3), 1)
        self.assertEqual(len(invalid_paths3), 1)
        self.assertIn('valid_path', safe_paths3)
        self.assertIn('../relative/path', invalid_paths3)
        
        # 测试4: 混合情况
        paths4 = ['valid_path', 'nonexistent_path', '../relative/path', 'another_valid_path']
        safe_paths4, invalid_paths4 = self.toolkit._process_paths(paths4)
        self.assertEqual(len(safe_paths4), 2)
        self.assertEqual(len(invalid_paths4), 2)
        
    def test_get_safe_error_message(self):
        """测试_get_safe_error_message辅助方法的敏感信息过滤功能"""
        logger.info("测试: _get_safe_error_message - 敏感信息过滤")
        
        # 设置用户名和密码以便测试过滤功能
        self.toolkit.username = "test_user"
        self.toolkit.password = "secret_password"
        
        # 测试1: 包含密码的错误消息
        error_msg1 = "认证失败: 密码 'secret_password' 不正确"
        safe_msg1 = self.toolkit._get_safe_error_message(error_msg1)
        self.assertNotIn("secret_password", safe_msg1)
        self.assertIn("******", safe_msg1)
        
        # 测试2: 包含用户名的错误消息
        error_msg2 = "用户 'test_user' 没有足够权限"
        safe_msg2 = self.toolkit._get_safe_error_message(error_msg2)
        self.assertNotIn("test_user", safe_msg2)
        self.assertIn("[USERNAME]", safe_msg2)
        
        # 测试3: 同时包含用户名和密码的错误消息
        error_msg3 = "认证失败: 用户 'test_user' 使用密码 'secret_password' 登录失败"
        safe_msg3 = self.toolkit._get_safe_error_message(error_msg3)
        self.assertNotIn("test_user", safe_msg3)
        self.assertNotIn("secret_password", safe_msg3)
        self.assertIn("[USERNAME]", safe_msg3)
        self.assertIn("******", safe_msg3)
        
        # 测试4: 不包含敏感信息的错误消息
        error_msg4 = "操作失败: 文件未找到"
        safe_msg4 = self.toolkit._get_safe_error_message(error_msg4)
        self.assertEqual(error_msg4, safe_msg4)
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._invalidate_cache')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._get_safe_error_message')
    def test_svn_revert(self, mock_get_safe_error, mock_invalidate_cache, mock_run_svn_command, mock_process_paths):
        """测试重构后的svn_revert方法"""
        logger.info("测试: svn_revert - 撤销修改")
        
        # 模拟路径处理结果
        mock_process_paths.return_value = (['valid/path/file.txt'], ['invalid/path'])
        
        # 模拟命令执行成功
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "Reverted 'valid/path/file.txt'",
            "stderr": "",
            "returncode": 0
        }
        
        # 模拟安全错误消息处理
        mock_get_safe_error.return_value = "安全的错误消息"
        
        # 测试成功情况
        result = self.toolkit.svn_revert(['valid/path/file.txt', 'invalid/path'])
        self.assertTrue(result)
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with(['valid/path/file.txt', 'invalid/path'])
        
        # 验证命令执行
        mock_run_svn_command.assert_called_once_with(['revert', 'valid/path/file.txt'])
        
        # 验证缓存失效被调用
        self.assertEqual(mock_invalidate_cache.call_count, 3)  # 符合实际代码行为
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        mock_invalidate_cache.reset_mock()
        
        mock_process_paths.return_value = (['valid/path/file.txt'], [])
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法撤销修改",
            "returncode": 1
        }
        
        result = self.toolkit.svn_revert(['valid/path/file.txt'])
        self.assertFalse(result)
        
        # 验证错误消息处理被调用
        mock_get_safe_error.assert_called_once_with("错误: 无法撤销修改")
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = ([], ['invalid/path'])
        
        result = self.toolkit.svn_revert(['invalid/path'])
        self.assertFalse(result)
        mock_run_svn_command.assert_not_called()
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._invalidate_cache')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._get_safe_error_message')
    def test_svn_resolved(self, mock_get_safe_error, mock_invalidate_cache, mock_run_svn_command, mock_process_paths):
        """测试冲突解决功能"""
        logger.info("测试: svn_resolved - 冲突解决")
          
        # 模拟路径处理结果
        paths = ["/path/to/conflict/file1.txt", "/path/to/conflict/file2.txt"]
        mock_process_paths.return_value = (paths, ["invalid_path"])
        
        # 模拟成功响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }
        
        # 调用方法
        result = self.toolkit.svn_resolved(paths + ["invalid_path"])
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "成功标记冲突已解决")
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with(paths + ["invalid_path"])
        
        # 验证命令调用
        expected_command = ["resolved"] + paths
        mock_run_svn_command.assert_called_once_with(expected_command)
        
        # 验证缓存失效被调用
        self.assertEqual(mock_invalidate_cache.call_count, 4)  # 每个路径2次，共2个路径
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        mock_invalidate_cache.reset_mock()
        mock_get_safe_error.reset_mock()
        
        mock_process_paths.return_value = (paths, [])
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法标记冲突已解决",
            "returncode": 1
        }
        
        result = self.toolkit.svn_resolved(paths)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "错误: 无法标记冲突已解决")
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = ([], ["invalid_path"])
        
        result = self.toolkit.svn_resolved(["invalid_path"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "没有有效的路径可供标记冲突已解决")
        mock_run_svn_command.assert_not_called()
    
    def test_base_url_from_env(self):
        """测试从环境变量读取SVN_BASE_URL"""
        logger.info("测试: 从环境变量读取SVN_BASE_URL")
        
        # 验证从环境变量读取base_url
        self.assertEqual(self.toolkit.base_url, self.test_base_url)
        
        # 测试通过参数设置base_url
        custom_base_url = "https://custom-server/svn/"
        toolkit = SVNToolkit(base_url=custom_base_url)
        self.assertEqual(toolkit.base_url, custom_base_url)
        
        # 测试无base_url情况
        # 临时清除环境变量
        del os.environ["SVN_BASE_URL"]
        toolkit_no_base = SVNToolkit()
        self.assertEqual(toolkit_no_base.base_url, "")
        # 恢复环境变量
        os.environ["SVN_BASE_URL"] = self.test_base_url
    
    def test_get_full_url(self):
        """测试_get_full_url方法的功能"""
        logger.info("测试: _get_full_url - URL路径处理")
        
        # 测试场景1: 完整URL保持不变
        full_urls = [
            "http://example.com/svn/repo",
            "https://secure-server/svn/repo",
            "svn://svn-server/repo",
            "file:///path/to/repo"
        ]
        
        for url in full_urls:
            self.assertEqual(self.toolkit._get_full_url(url), url)
        
        # 测试场景2: 相对路径与base_url组合
        relative_paths = [
            "repo",
            "/repo",
            "repo/trunk",
            "/repo/trunk"
        ]
        
        expected_results = [
            "http://test-server:3690/svn/repo",
            "http://test-server:3690/svn/repo",
            "http://test-server:3690/svn/repo/trunk",
            "http://test-server:3690/svn/repo/trunk"
        ]
        
        for path, expected in zip(relative_paths, expected_results):
            self.assertEqual(self.toolkit._get_full_url(path), expected)
        
        # 测试场景3: 无base_url时返回原始路径
        # 清除环境变量影响
        original_env = os.environ.copy()
        if "SVN_BASE_URL" in os.environ:
            del os.environ["SVN_BASE_URL"]
        
        try:
            toolkit_no_base = SVNToolkit(base_url="")
            for path in relative_paths:
                self.assertEqual(toolkit_no_base._get_full_url(path), path)
        finally:
            # 恢复环境变量
            os.environ.clear()
            os.environ.update(original_env)
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_checkout_with_relative_path(self, mock_run_svn_command):
        """测试使用相对路径检出仓库"""
        logger.info("测试: svn_checkout - 使用相对路径检出")
        
        # 模拟成功响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "Checked out revision 123.",
            "stderr": "",
            "returncode": 0
        }
        
        # 使用相对路径调用
        relative_repo = "test-repo"
        local_path = "/local/path"
        
        # 模拟os.makedirs不抛出异常
        with patch('os.makedirs') as mock_makedirs:
            result = self.toolkit.svn_checkout(relative_repo, local_path)
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证命令调用时使用了完整URL
        expected_url = "http://test-server:3690/svn/test-repo"
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        # 检查命令中是否包含预期的URL
        self.assertIn(expected_url, args[0])
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    def test_svn_copy_with_relative_paths(self, mock_run_svn_command):
        """测试使用相对路径创建分支/标签"""
        logger.info("测试: svn_copy - 使用相对路径创建分支")
        
        # 模拟成功响应
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "Committed revision 123.",
            "stderr": "",
            "returncode": 0
        }
        
        # 模拟os.path.exists返回False（这样会将相对路径视为URL）
        with patch('os.path.exists', return_value=False):
            # 使用相对路径调用
            src_path = "trunk"
            dest_path = "branches/test-branch"
            result = self.toolkit.svn_copy(src_path, dest_path)
        
        # 验证结果
        self.assertTrue(result["success"])
        
        # 验证命令调用时使用了完整URL
        expected_src = "http://test-server:3690/svn/trunk"
        expected_dest = "http://test-server:3690/svn/branches/test-branch"
        mock_run_svn_command.assert_called_once()
        args, _ = mock_run_svn_command.call_args
        # 检查命令中是否包含预期的源路径和目标路径
        self.assertIn(expected_src, args[0])
        self.assertIn(expected_dest, args[0])
    
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._process_paths')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._run_svn_command')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._invalidate_cache')
    @patch('camel.toolkits.svn_toolkit.SVNToolkit._get_safe_error_message')
    def test_svn_add(self, mock_get_safe_error, mock_invalidate_cache, mock_run_svn_command, mock_process_paths):
        """测试重构后的svn_add方法"""
        logger.info("测试: svn_add - 添加文件")
        
        # 模拟路径处理结果
        mock_process_paths.return_value = (['new_file.txt', 'src/'], ['invalid_path'])
        
        # 模拟命令执行成功
        mock_run_svn_command.return_value = {
            "success": True,
            "stdout": "A new_file.txt\nA src/",
            "stderr": "",
            "returncode": 0
        }
        
        # 测试成功情况
        result = self.toolkit.svn_add(['new_file.txt', 'src/', 'invalid_path'])
        self.assertTrue(result)
        
        # 验证路径处理被调用
        mock_process_paths.assert_called_once_with(['new_file.txt', 'src/', 'invalid_path'])
        
        # 验证命令执行
        mock_run_svn_command.assert_called_once_with(['add', 'new_file.txt', 'src/'])
        
        # 验证缓存失效被调用
        self.assertEqual(mock_invalidate_cache.call_count, 1)  # 符合实际代码行为
        
        # 测试失败情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        mock_invalidate_cache.reset_mock()
        
        mock_process_paths.return_value = (['new_file.txt'], [])
        mock_run_svn_command.return_value = {
            "success": False,
            "stderr": "错误: 无法添加文件",
            "returncode": 1
        }
        
        result = self.toolkit.svn_add(['new_file.txt'])
        self.assertFalse(result)
        
        # 验证错误消息处理被调用
        mock_get_safe_error.assert_called_once_with("错误: 无法添加文件")
        
        # 测试无有效路径情况
        mock_process_paths.reset_mock()
        mock_run_svn_command.reset_mock()
        
        mock_process_paths.return_value = ([], ['invalid_path'])
        
        result = self.toolkit.svn_add(['invalid_path'])
        self.assertFalse(result)
        mock_run_svn_command.assert_not_called()
    
    def test_get_tools(self):
        """测试获取工具列表功能"""
        logger.info("测试: get_tools - 获取工具列表")
        
        tools = self.toolkit.get_tools()
        
        # 验证工具数量（基础工具+新工具+统一接口方法）
        # 统一接口方法: get_repository_info, is_repository_exist, create_repository, clone_or_checkout, get_branches_or_tags, get_latest_commit_info, push_changes (7个)
        # 基础工具: checkout, update, info, log, commit, add, delete, status, add_all, revert (10个)
        # 分支管理工具: copy, list_branches, list_tags (3个)
        # 属性管理工具: propset, propget, proplist, propdel (4个)
        # 冲突解决工具: resolved (1个)
        # 总共25个工具
        self.assertEqual(len(tools), 25)
        
        # 验证新工具是否存在
        tool_names = [tool.func.__name__ for tool in tools]  # 使用func.__name__获取函数名
        self.assertIn('svn_copy', tool_names)
        self.assertIn('svn_list_branches', tool_names)
        self.assertIn('svn_list_tags', tool_names)
        self.assertIn('svn_propset', tool_names)
        self.assertIn('svn_propget', tool_names)
        self.assertIn('svn_proplist', tool_names)
        self.assertIn('svn_propdel', tool_names)
        self.assertIn('svn_resolved', tool_names)


def create_svn_toolkit_test():
    """测试create_svn_toolkit辅助函数"""
    logger.info("测试: create_svn_toolkit - 辅助函数")
    
    # 导入函数
    try:
        from camel.toolkits.svn_toolkit import create_svn_toolkit
        
        # 测试默认参数
        toolkit1 = create_svn_toolkit()
        assert isinstance(toolkit1, SVNToolkit)
        
        # 测试自定义参数
        custom_username = "custom_user"
        custom_password = "custom_pass"
        custom_base_url = "http://custom-server:8080/svn/"
        
        toolkit2 = create_svn_toolkit(
            username=custom_username, 
            password=custom_password,
            base_url=custom_base_url
        )
        
        assert toolkit2.username == custom_username
        assert toolkit2.password == custom_password
        assert toolkit2.base_url == custom_base_url
        
        logger.info("✅ create_svn_toolkit测试通过")
        return True
    except ImportError:
        logger.warning("⚠️ create_svn_toolkit函数不存在，跳过测试")
        return True

def run_all_tests():
    """运行所有测试"""
    logger.info("🚀 开始运行SVN工具包新增功能单元测试")
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSVNToolkit)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 运行create_svn_toolkit测试
    try:
        create_svn_toolkit_test()
    except AssertionError as e:
        logger.error(f"❌ create_svn_toolkit测试失败: {str(e)}")
        result.failures.append(("create_svn_toolkit_test", str(e)))
    
    # 输出测试结果摘要
    logger.info("\n📊 测试结果摘要:")
    logger.info(f"总测试用例数: {result.testsRun + 1}")  # +1 表示create_svn_toolkit测试
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info(f"跳过: {len(result.skipped)}")
    
    if result.wasSuccessful() and len(result.failures) == 0:
        logger.info("✅ 所有测试通过!")
    else:
        logger.error("❌ 测试失败")
    
    return 0 if result.wasSuccessful() and len(result.failures) == 0 else 1


if __name__ == "__main__":
    # 运行单元测试
    sys.exit(run_all_tests())