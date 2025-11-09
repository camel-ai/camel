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
import re
import logging
import subprocess
import sys
from typing import Dict, List, Optional, Union, Any
from functools import lru_cache
import time
from collections import defaultdict

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.version_control_base_toolkit import VersionControlBaseToolkit

logger = logging.getLogger(__name__)


class SVNToolkit(VersionControlBaseToolkit):
    """
    SVN工具包，用于与Subversion版本控制系统交互。
    
    完全基于SlikSVN命令行工具的实现，不使用pysvn库，
    提供完整的SVN操作功能，支持中英文环境输出解析。
    """
    
    # 平台名称
    PLATFORM_NAME: str = "svn"
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        cache_ttl: int = 300  # 缓存有效期（秒）
    ) -> None:
        """
        初始化SVN工具包。
        
        Args:
            username: SVN用户名，如果未提供，将从环境变量SVN_USERNAME获取
            password: SVN密码，如果未提供，将从环境变量SVN_PASSWORD获取
            base_url: SVN基础URL，如果未提供，将从环境变量SVN_BASE_URL获取
            timeout: 操作超时时间（秒）
            cache_ttl: 缓存有效期（秒），默认为300秒
        """
        super().__init__(timeout=timeout)
        
        self.username = username or os.environ.get("SVN_USERNAME")
        # 安全处理密码，避免不必要的暴露
        self.password = password or os.environ.get("SVN_PASSWORD")
        # 明确优先级：参数 > 环境变量 > 默认值
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = os.environ.get("SVN_BASE_URL", "")
        
        # 检查命令行SVN是否可用
        self.svn_available = self._check_svn_available()
        if not self.svn_available:
            logger.warning("⚠️ SVN命令行工具不可用，请确保已安装SlikSVN或其他SVN命令行客户端")
        else:
            logger.info("✅ SlikSVN命令行客户端可用")
            
        # 记录配置信息
        if self.base_url:
            logger.info(f"📁 SVN基础URL: {self.base_url}")
        
        # 性能优化：添加缓存机制
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}
        self._workspace_cache = defaultdict(dict)  # 工作区管理缓存
            
    def _handle_error(self, exception: Exception, method_name: str) -> Dict:
        """
        统一的错误处理方法
        
        Args:
            exception: 捕获到的异常
            method_name: 调用出错的方法名
            
        Returns:
            Dict: 标准格式的错误响应
        """
        error_type = exception.__class__.__name__
        error_message = str(exception)
        
        # 记录错误，避免记录敏感信息
        logger.error(f"方法 {method_name} 执行出错: {error_type} - {error_message}")
        
        # 根据错误类型提供更友好的错误信息
        if isinstance(exception, subprocess.TimeoutExpired):
            friendly_message = f"命令执行超时，请检查网络连接和SVN服务器状态"
        elif "authorization failed" in error_message.lower():
            friendly_message = "认证失败，请检查用户名和密码是否正确"
        elif "connection refused" in error_message.lower():
            friendly_message = "连接被拒绝，请检查SVN服务器地址是否正确"
        else:
            friendly_message = error_message
            
        return {
            "success": False,
            "error": friendly_message,
            "error_type": error_type
        }
        
    def _process_paths(self, paths: List[str]) -> tuple[List[str], List[str]]:
        """
        处理路径列表，进行安全检查和规范化。
        
        Args:
            paths: 原始路径列表
            
        Returns:
            Tuple: (安全有效路径列表, 无效路径列表)
        """
        safe_paths = []
        invalid_paths = []
        
        for path in paths:
            # 跳过空路径
            if not path or not path.strip():
                logger.warning("⚠️ 空路径被忽略")
                invalid_paths.append(path)
                continue
                
            # 判断是否为远程URL
            is_remote_url = path.startswith(('http://', 'https://', 'svn://'))
            
            # 对于本地路径，检查是否存在
            if not is_remote_url and not os.path.exists(path):
                # 在测试环境中，可能使用模拟路径，不记录警告
                if os.environ.get('PYTEST_CURRENT_TEST') is None:
                    logger.warning(f"⚠️ 本地路径不存在: {path}")
                invalid_paths.append(path)
                continue
            
            # 规范化路径（仅对本地路径）
            if is_remote_url:
                # 对于远程URL，保持原样但确保安全
                if ".." in path.split('/'):
                    logger.warning(f"⚠️  远程URL包含相对引用，可能不安全: {path}")
                    invalid_paths.append(path)
                    continue
                safe_paths.append(path)
            else:
                # 对于本地路径，进行规范化
                normalized_path = os.path.normpath(path)
                if ".." in normalized_path.split(os.sep):
                    logger.warning(f"⚠️  路径包含相对引用，可能不安全: {path}")
                    invalid_paths.append(path)
                    continue
                safe_paths.append(normalized_path)
        
        return safe_paths, invalid_paths
        
    def _get_safe_error_message(self, error_message: str) -> str:
        """
        安全处理错误消息，过滤敏感信息。
        
        Args:
            error_message: 原始错误消息
            
        Returns:
            str: 过滤后的安全错误消息
        """
        # 替换敏感信息
        safe_message = error_message
        
        # 过滤密码
        if hasattr(self, 'password') and self.password:
            safe_message = safe_message.replace(self.password, "******")
        
        # 过滤其他可能的敏感信息
        if hasattr(self, 'username') and self.username:
            safe_message = safe_message.replace(self.username, "[USERNAME]")
        
        return safe_message
    
    def _get_cache(self, key: str) -> Any:
        """
        获取缓存数据。
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果缓存不存在或已过期则返回None
        """
        # 检查缓存是否存在
        if key not in self._cache or key not in self._cache_timestamps:
            return None
        
        # 检查缓存是否过期
        current_time = time.time()
        if current_time - self._cache_timestamps[key] > self.cache_ttl:
            # 删除过期缓存
            del self._cache[key]
            del self._cache_timestamps[key]
            return None
        
        logger.debug(f"📤 从缓存获取: {key}")
        return self._cache[key]
    
    def _set_cache(self, key: str, value: Any) -> None:
        """
        设置缓存数据。
        
        Args:
            key: 缓存键
            value: 要缓存的值
        """
        current_time = time.time()
        self._cache[key] = value
        self._cache_timestamps[key] = current_time
        logger.debug(f"📥 设置缓存: {key}")
    
    def _clear_cache(self) -> None:
        """
        清除所有缓存数据。
        """
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("🧹 所有缓存已清除")
    
    def _invalidate_cache(self, key_pattern: str) -> None:
        """
        使匹配特定模式的缓存失效。
        
        Args:
            key_pattern: 要匹配的缓存键模式
        """
        keys_to_remove = []
        for key in self._cache.keys():
            if key_pattern in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
        
        if keys_to_remove:
            logger.info(f"🔄 已使 {len(keys_to_remove)} 个缓存失效")
    
    # ========== 工作区管理功能 ==========
    
    def register_workspace(self, workspace_path: str, workspace_name: Optional[str] = None) -> bool:
        """
        注册工作区到缓存中以便快速访问。
        
        Args:
            workspace_path: 工作区路径
            workspace_name: 可选的工作区名称，如果不提供则使用路径的最后一部分
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 验证路径是否存在
            if not os.path.exists(workspace_path):
                logger.error(f"❌ 工作区路径不存在: {workspace_path}")
                return False
            
            # 规范化路径
            normalized_path = os.path.normpath(workspace_path)
            
            # 如果未提供名称，使用路径的最后一部分
            if not workspace_name:
                workspace_name = os.path.basename(normalized_path)
            
            # 注册工作区
            self._workspace_cache[workspace_name] = {
                "path": normalized_path,
                "registered_at": time.time(),
                "last_accessed": time.time()
            }
            
            logger.info(f"✅ 成功注册工作区 '{workspace_name}': {normalized_path}")
            return True
        except Exception as e:
            self._handle_error(e, "register_workspace")
            return False
    
    def get_workspace(self, workspace_name: str) -> Optional[str]:
        """
        获取已注册工作区的路径。
        
        Args:
            workspace_name: 工作区名称
            
        Returns:
            str: 工作区路径，如果工作区不存在则返回None
        """
        try:
            if workspace_name in self._workspace_cache:
                # 更新最后访问时间
                self._workspace_cache[workspace_name]["last_accessed"] = time.time()
                return self._workspace_cache[workspace_name]["path"]
            
            logger.warning(f"⚠️ 未找到工作区: {workspace_name}")
            return None
        except Exception as e:
            self._handle_error(e, "get_workspace")
            return None
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的工作区。
        
        Returns:
            List[Dict]: 工作区信息列表
        """
        try:
            workspaces = []
            for name, info in self._workspace_cache.items():
                workspaces.append({
                    "name": name,
                    "path": info["path"],
                    "registered_at": info["registered_at"],
                    "last_accessed": info["last_accessed"]
                })
            
            # 按最后访问时间排序
            workspaces.sort(key=lambda x: x["last_accessed"], reverse=True)
            return workspaces
        except Exception as e:
            self._handle_error(e, "list_workspaces")
            return []
    
    def unregister_workspace(self, workspace_name: str) -> bool:
        """
        取消注册工作区。
        
        Args:
            workspace_name: 工作区名称
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if workspace_name in self._workspace_cache:
                del self._workspace_cache[workspace_name]
                logger.info(f"✅ 已取消注册工作区: {workspace_name}")
                return True
            
            logger.warning(f"⚠️ 未找到要取消注册的工作区: {workspace_name}")
            return False
        except Exception as e:
            self._handle_error(e, "unregister_workspace")
            return False
    
    def get_workspace_status(self, workspace_name: str) -> Optional[List[Dict[str, str]]]:
        """
        获取指定工作区的状态。
        
        Args:
            workspace_name: 工作区名称
            
        Returns:
            List[Dict]: 工作区状态信息，如果工作区不存在则返回None
        """
        workspace_path = self.get_workspace(workspace_name)
        if workspace_path:
            return self.svn_status(workspace_path)
        return None
    
    def _check_svn_available(self) -> bool:
        """
        检查SVN命令行工具是否可用
        
        Returns:
            bool: SVN命令行工具是否可用
        """
        try:
            result = subprocess.run(
                ["svn", "--version", "--quiet"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True if sys.platform == 'win32' else False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _ensure_tool_available(self) -> bool:
        """
        确保SVN工具可用
        
        Returns:
            bool: SVN工具是否可用
        """
        return self.svn_available
    
    def get_toolkit_info(self) -> Dict[str, Any]:
        """
        获取SVN工具包信息
        
        Returns:
            Dict[str, Any]: 工具包信息字典，包含SVN版本、可用性等信息
        """
        try:
            # 获取SVN版本信息
            result = self._run_svn_command(['--version', '--quiet'])
            version = result.get('stdout', '').strip() if result.get('success') else '未知'
            
            return {
                'toolkit_name': 'SVNToolkit',
                'platform_name': self.PLATFORM_NAME,
                'svn_available': self.svn_available,
                'svn_version': version,
                'base_url': self.base_url,
                'credentials_provided': bool(self.username and self.password)
            }
        except Exception as e:
            return {
                'toolkit_name': 'SVNToolkit',
                'platform_name': self.PLATFORM_NAME,
                'svn_available': self.svn_available,
                'error': str(e)
            }
    
    def validate_credentials(self) -> bool:
        """
        验证SVN凭证是否有效
        
        Returns:
            bool: 凭证是否有效
        """
        if not self.svn_available:
            return False
        
        # 如果没有提供凭证，认为是匿名访问
        if not (self.username and self.password):
            return True
        
        # 尝试使用svn info命令来验证凭证
        try:
            if self.base_url:
                result = self._run_svn_command(['info', self.base_url])
                # 如果返回成功或者错误不是关于认证的，都认为凭证有效
                if result.get('success') or '认证失败' not in result.get('stderr', ''):
                    return True
                return False
            # 如果没有base_url，我们至少验证凭证格式是否正确
            return True
        except Exception:
            return False
    
    def _run_svn_command(self, command: List[str], capture_output: bool = True) -> Dict:
        """
        运行SVN命令并返回结果
        
        Args:
            command: 要运行的命令列表
            capture_output: 是否捕获输出
            
        Returns:
            Dict: 包含结果的字典
        """
        if not self.svn_available:
            return self._handle_error(Exception("SVN命令行工具不可用"), "_run_svn_command")
        
        # 添加认证信息和非交互模式
        full_command = ["svn"] + command
        
        # 安全记录命令（不含密码）
        safe_command = full_command.copy()
        
        if self.username:
            full_command.extend(["--username", self.username])
            safe_command.extend(["--username", self.username])
        if self.password:
            full_command.extend(["--password", self.password])
            safe_command.extend(["--password", "******"])
        
        full_command.append("--non-interactive")
        full_command.append("--trust-server-cert")
        safe_command.append("--non-interactive")
        safe_command.append("--trust-server-cert")
        
        # 使用安全的日志记录，不包含密码
        logger.debug(f"执行SVN命令: {' '.join(safe_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=capture_output,
                text=True,
                shell=True if sys.platform == 'win32' else False,
                timeout=self.timeout
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout if capture_output else None,
                "stderr": result.stderr if capture_output else None,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return self._handle_error(subprocess.TimeoutExpired(
                self.timeout, full_command), "_run_svn_command")
        except Exception as e:
            return self._handle_error(e, "_run_svn_command")
    
    def _get_full_url(self, url_or_path: str) -> str:
        """
        获取完整的SVN URL，如果提供的是相对路径且设置了base_url，则自动组合。
        
        Args:
            url_or_path: 可能是完整URL或相对路径
            
        Returns:
            str: 完整的SVN URL
        """
        # 检查是否已经是完整URL
        if url_or_path.startswith(("http://", "https://", "svn://", "file://")):
            return url_or_path
        
        # 如果提供了base_url且不是空字符串，则组合成完整URL
        if self.base_url:
            # 确保base_url以/结尾，且避免双斜杠
            base = self.base_url.rstrip('/')
            path = url_or_path.lstrip('/')
            return f"{base}/{path}"
        
        # 如果没有base_url，就返回原始路径
        return url_or_path
        
    def svn_checkout(self, repo_url: str, local_path: str, revision: Optional[int] = None) -> bool:
        """
        检出SVN仓库。
        
        Args:
            repo_url: SVN仓库URL（可以是完整URL或相对于base_url的路径）
            local_path: 本地检出路径
            revision: 指定的版本号，默认为HEAD
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取完整的仓库URL
            full_repo_url = self._get_full_url(repo_url)
            
            # 确保本地路径存在
            os.makedirs(local_path, exist_ok=True)
            
            cmd = ["checkout"]
            
            if revision:
                cmd.extend(["-r", str(revision)])
            
            cmd.extend([full_repo_url, local_path])
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功检出仓库: {repo_url} 到 {local_path}")
                # 使相关缓存失效
                self._invalidate_cache(f"svn_info:{local_path}")
                self._invalidate_cache(f"svn_status:{local_path}")
                return True
            else:
                logger.error(f"❌ 检出失败: {result.get('stderr', result.get('error', '未知错误'))}")
                return False
        except Exception as e:
            self._handle_error(e, "svn_checkout")
            return False
    
    # 继续添加其他SVN操作方法
    def svn_update(self, local_path: str, revision: Optional[int] = None) -> bool:
        """
        更新SVN工作副本。
        
        Args:
            local_path: 本地工作副本路径
            revision: 指定的版本号，默认为HEAD
            
        Returns:
            bool: 操作是否成功
        """
        try:
            cmd = ["update"]
            
            if revision:
                cmd.extend(["-r", str(revision)])
            
            cmd.append(local_path)
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功更新工作副本: {local_path}")
                # 使相关缓存失效
                self._invalidate_cache(f"svn_info:{local_path}")
                self._invalidate_cache(f"svn_status:{local_path}")
                return True
            else:
                logger.error(f"❌ 更新失败: {result.get('stderr', result.get('error', '未知错误'))}")
                return False
        except Exception as e:
            self._handle_error(e, "svn_update")
            return False
    
    def svn_info(self, url_or_path: str) -> Optional[Dict[str, str]]:
        """
        获取SVN仓库或工作副本的信息。
        
        Args:
            url_or_path: SVN仓库URL（可以是完整URL或相对于base_url的路径）或本地工作副本路径
        
        Returns:
            Dict: 包含SVN信息的字典，如果失败则返回None。
                  字典同时包含英文键名和对应的中文键名，确保兼容性。
        """
        try:
            # 性能优化：使用缓存机制
            cache_key = f"svn_info:{url_or_path}"
            cached_result = self._get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"🔄 从缓存返回svn_info结果: {url_or_path}")
                return cached_result
            # 如果是URL格式，则使用完整URL；如果是本地路径，则直接使用
            if url_or_path.startswith(('http://', 'https://', 'svn://', 'file://')):
                full_path = self._get_full_url(url_or_path)
            else:
                # 检查是否为本地路径（存在的目录或文件）
                if os.path.exists(url_or_path):
                    full_path = url_or_path
                else:
                    # 否则视为相对URL路径
                    full_path = self._get_full_url(url_or_path)
            
            cmd = ["info", full_path]
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                info = {}
                output = result["stdout"]
                
                try:
                    # 中英文键名映射表
                    key_mapping = {
                        'URL': ['URL', 'URL地址'],
                        'Revision': ['Revision', '版本'],
                        'Repository Root': ['Repository Root', '版本库根'],
                        'Repository UUID': ['Repository UUID', '版本库 UUID'],
                        'Last Changed Rev': ['Last Changed Rev', '最后修改的版本'],
                        'Last Changed Author': ['Last Changed Author', '最后修改的作者'],
                        'Last Changed Date': ['Last Changed Date', '最后修改的时间'],
                        'Path': ['Path', '路径'],
                        'Relative URL': ['Relative URL', '相对URL'],
                        'Node Kind': ['Node Kind', '节点种类']
                    }
                    
                    # 存储原始解析的信息
                    original_info = {}
                    
                    # 解析SVN info输出
                    for line in output.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            original_info[key] = value
                    
                    # 创建包含中英文键名的结果字典
                    for en_key, possible_keys in key_mapping.items():
                        for possible_key in possible_keys:
                            if possible_key in original_info:
                                info[en_key] = original_info[possible_key]
                                break
                    
                    # 保留所有原始键，确保不丢失信息
                    for key, value in original_info.items():
                        if key not in info:
                            info[key] = value
                    
                    logger.info(f"✅ 成功获取信息: {url_or_path}, 收集到 {len(info)} 个信息项")
                    # 设置缓存
                    cache_key = f"svn_info:{url_or_path}"
                    self._set_cache(cache_key, info)
                    return info
                    
                except Exception as e:
                    logger.error(f"❌ 解析SVN信息时出错: {str(e)}")
                    # 如果解析出错，仍然尝试返回收集到的部分信息
                    return info if info else None
            else:
                logger.error(f"❌ 获取信息失败: {result.get('stderr', result.get('error', '未知错误'))}")
                return None
        except Exception as e:
            self._handle_error(e, "svn_info")
            return None
    
    def svn_log(self, url_or_path: str, limit: int = 10, revision_range: Optional[str] = None) -> List[Dict]:
        """
        获取SVN提交日志。
        
        Args:
            url_or_path: SVN仓库URL（可以是完整URL或相对于base_url的路径）或本地工作副本路径
            limit: 返回的最大日志条目数
            revision_range: 版本范围，格式为"{start}:{end}"
        
        Returns:
            List[Dict]: 包含提交日志信息的列表，每个元素包含作者、日期、消息和修订版本号
        """
        try:
            # 性能优化：使用缓存机制
            cache_key = f"svn_log:{url_or_path}:{limit}:{revision_range or 'all'}"
            cached_result = self._get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"🔄 从缓存返回svn_log结果: {url_or_path}, 限制: {limit}")
                return cached_result
            # 如果是URL格式，则使用完整URL；如果是本地路径，则直接使用
            if url_or_path.startswith(('http://', 'https://', 'svn://', 'file://')):
                full_path = self._get_full_url(url_or_path)
            else:
                # 检查是否为本地路径（存在的目录或文件）
                if os.path.exists(url_or_path):
                    full_path = url_or_path
                else:
                    # 否则视为相对URL路径
                    full_path = self._get_full_url(url_or_path)
            
            cmd = ["log", "--limit", str(limit)]
            
            if revision_range:
                cmd.extend(["-r", revision_range])
            
            # 使用--xml参数获取结构化输出，便于解析
            cmd.extend(["--xml", full_path])
            
            result = self._run_svn_command(cmd)
            logs = []
            
            if result["success"]:
                output = result["stdout"]
                
                # 简单的XML解析
                import re
                
                # 正则表达式匹配日志条目
                entry_pattern = re.compile(r'<logentry [^>]*revision="([^"]+)"[^>]*>(.*?)</logentry>', re.DOTALL)
                for match in entry_pattern.finditer(output):
                    revision = match.group(1)
                    entry_content = match.group(2)
                    
                    # 提取作者（安全处理）
                    author_match = re.search(r'<author>(.*?)</author>', entry_content)
                    author = author_match.group(1).strip() if author_match else ''
                    
                    # 提取日期
                    date_match = re.search(r'<date>(.*?)</date>', entry_content)
                    date = date_match.group(1) if date_match else ''
                    
                    # 提取消息（安全处理，避免日志中包含敏感信息）
                    message_match = re.search(r'<msg>(.*?)</msg>', entry_content, re.DOTALL)
                    message = message_match.group(1).strip() if message_match else ''
                    
                    logs.append({
                        'revision': revision,
                        'author': author,
                        'date': date,
                        'message': message
                    })
                
                logger.info(f"✅ 成功获取日志: {url_or_path}")
                # 设置缓存
                cache_key = f"svn_log:{url_or_path}:{limit}:{revision_range or 'all'}"
                self._set_cache(cache_key, logs)
            else:
                logger.error(f"❌ 获取日志失败: {result.get('stderr', result.get('error', '未知错误'))}")
            
            return logs
        except Exception as e:
            error_info = self._handle_error(e, "svn_log")
            logger.error(f"❌ 获取日志过程中发生异常: {error_info.get('error')}")
            return []
    
    def svn_commit(self, local_path: str, message: str, include_paths: Optional[List[str]] = None) -> bool:
        """
        提交SVN工作副本的更改。
        
        Args:
            local_path: 本地工作副本路径
            message: 提交消息
            include_paths: 要包含在提交中的特定路径列表
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 安全检查提交信息，避免可能的命令注入
            if not isinstance(message, str) or len(message.strip()) == 0:
                logger.error("❌ 提交信息不能为空")
                return False
            
            # 安全检查本地路径
            if not os.path.exists(local_path):
                logger.error(f"❌ 本地路径不存在: {local_path}")
                return False
            
            cmd = ["commit", "-m", message[:500]]  # 限制提交信息长度，避免过长
            
            if include_paths:
                # 安全验证路径
                safe_paths = []
                for path in include_paths:
                    # 安全检查路径，防止路径遍历攻击
                    if ".." in path:
                        logger.warning(f"⚠️  跳过可能不安全的路径: {path}")
                        continue
                    full_path = os.path.normpath(os.path.join(local_path, path))
                    # 确保路径仍在本地工作副本内
                    if os.path.commonpath([local_path, full_path]) != local_path:
                        logger.warning(f"⚠️  跳过超出工作副本的路径: {full_path}")
                        continue
                    safe_paths.append(full_path)
                
                if safe_paths:
                    cmd.extend(safe_paths)
                else:
                    cmd.append(local_path)
            else:
                cmd.append(local_path)
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                # 尝试从输出中提取修订版本号
                output = result["stdout"]
                rev_match = re.search(r'Committed revision (\d+)\.', output)
                revision = rev_match.group(1) if rev_match else 'unknown'
                
                logger.info(f"✅ 成功提交更改，修订版本: {revision}")
                # 缓存失效，确保后续查询获取最新状态
                self._invalidate_cache(f"svn_info:{local_path}")
                self._invalidate_cache(f"svn_status:{local_path}")
                self._invalidate_cache("svn_log")
                return True
            else:
                # 使用辅助方法处理错误信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 提交失败: {safe_error_msg}")
                return False
        except Exception as e:
            error_info = self._handle_error(e, "svn_commit")
            logger.error(f"❌ 提交过程中发生异常: {error_info.get('error')}")
            return False
    
    def svn_add(self, paths: List[str]) -> bool:
        """
        将文件或目录添加到SVN版本控制。
        
        Args:
            paths: 要添加的文件或目录路径列表
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 使用辅助方法进行路径安全检查和规范化
            safe_paths, invalid_paths = self._process_paths(paths)
            
            if not safe_paths:
                logger.error("❌ 没有有效的路径可供添加")
                return False
            
            # 批量处理优化：将大型列表分批处理，避免命令行过长
            batch_size = 100  # 每批处理的文件数
            all_successful = True
            
            for i in range(0, len(safe_paths), batch_size):
                batch_paths = safe_paths[i:i + batch_size]
                
                cmd = ["add"] + batch_paths
                
                result = self._run_svn_command(cmd)
                
                if result["success"]:
                    logger.info(f"✅ 成功添加批处理 {i//batch_size + 1}: {len(batch_paths)} 个文件/目录")
                else:
                    all_successful = False
                    # 使用辅助方法过滤错误信息中的敏感内容
                    error_msg = result.get('stderr', result.get('error', '未知错误'))
                    safe_error_msg = self._get_safe_error_message(error_msg)
                    logger.error(f"❌ 批处理 {i//batch_size + 1} 添加失败: {safe_error_msg}")
            
            # 批量操作后使相关缓存失效
            self._invalidate_cache("svn_status")
            
            if invalid_paths:
                logger.warning(f"⚠️ 有 {len(invalid_paths)} 个路径因验证失败未被添加")
            
            return all_successful
        except Exception as e:
            error_info = self._handle_error(e, "svn_add")
            logger.error(f"❌ 添加过程中发生异常: {error_info.get('error')}")
            return False
    
    def svn_delete(self, paths: List[str]) -> bool:
        """
        从SVN版本控制中删除文件或目录。
        
        Args:
            paths: 要删除的文件或目录路径列表
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 使用辅助方法处理路径
            safe_paths, invalid_paths = self._process_paths(paths)
            
            if not safe_paths:
                logger.error("❌ 没有有效的路径可供删除")
                return False
            
            cmd = ["delete"] + safe_paths
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功删除文件/目录: {safe_paths}")
                # 缓存失效，确保后续查询获取最新状态
                for path in safe_paths:
                    self._invalidate_cache(f"svn_info:{path}")
                    self._invalidate_cache(f"svn_status:{os.path.dirname(path) or '.'}")
                self._invalidate_cache("svn_log")
                
                if invalid_paths:
                    logger.warning(f"⚠️ 有 {len(invalid_paths)} 个路径因验证失败未被删除")
                
                return True
            else:
                # 使用辅助方法处理错误信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 删除失败: {safe_error_msg}")
                return False
        except Exception as e:
            error_info = self._handle_error(e, "svn_delete")
            logger.error(f"❌ 删除过程中发生异常: {error_info.get('error')}")
            return False
    
    def svn_status(self, local_path: str) -> List[Dict[str, str]]:
        """
        获取SVN工作副本的状态。
        
        Args:
            local_path: 本地工作副本路径
            
        Returns:
            List[Dict]: 状态信息列表
        """
        # 性能优化：使用缓存机制
        cache_key = f"svn_status:{os.path.normpath(local_path)}"
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"🔄 从缓存返回svn_status结果: {local_path}")
            return cached_result
            
        cmd = ["status", local_path]
        result = self._run_svn_command(cmd)
        
        statuses = []
        
        if result["success"]:
            output = result["stdout"]
            
            # 定义状态码的含义
            status_meanings = {
                'A': '添加',
                'C': '冲突',
                'D': '删除',
                'I': '忽略',
                'M': '修改',
                'R': '替换',
                'X': '外部定义',
                '?': '未版本控制',
                '!': '丢失',
                '~': '类型冲突'
            }
            
            # 解析SVN status输出
            for line in output.split('\n'):
                if line.strip():
                    status_code = line[0].strip() if len(line) > 0 else ''
                    path = line[1:].strip() if len(line) > 1 else ''
                    
                    status_info = {
                        'path': path,
                        'status_code': status_code
                    }
                    
                    # 添加状态含义（如果已知）
                    if status_code in status_meanings:
                        status_info['status_text'] = status_meanings[status_code]
                    
                    statuses.append(status_info)
            
            logger.info(f"✅ 成功获取状态: {local_path}")
            # 设置缓存
            self._set_cache(cache_key, statuses)
        else:
            logger.error(f"❌ 获取状态失败: {result.get('stderr', result.get('error', '未知错误'))}")
        
        return statuses
    
    def svn_add_all(self, local_path: str) -> bool:
        """
        添加工作副本中的所有未版本控制文件。
        
        Args:
            local_path: 本地工作副本路径
            
        Returns:
            bool: 操作是否成功
        """
        # 获取所有未版本控制的文件（状态码为'?'）
        statuses = self.svn_status(local_path)
        
        # 过滤出未版本控制的文件
        unversioned_paths = [s['path'] for s in statuses if s.get('status_code') == '?']
        
        if not unversioned_paths:
            logger.info(f"ℹ️  没有发现需要添加的未版本控制文件: {local_path}")
            return True
        
        # 添加这些文件
        return self.svn_add(unversioned_paths)
    
    def svn_revert(self, paths: List[str]) -> bool:
        """
        撤销对工作副本的本地修改。
        
        Args:
            paths: 要撤销修改的文件或目录路径列表
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 使用辅助方法进行路径安全检查和规范化
            safe_paths, invalid_paths = self._process_paths(paths)
            
            if not safe_paths:
                logger.error("❌ 没有有效的路径可供撤销修改")
                return False
            
            cmd = ["revert"] + safe_paths
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功撤销修改: {safe_paths}")
                # 缓存失效，确保后续查询获取最新状态
                for path in safe_paths:
                    self._invalidate_cache(f"svn_info:{path}")
                    self._invalidate_cache(f"svn_status:{os.path.dirname(path) or '.'}")
                self._invalidate_cache("svn_log")
                return True
            else:
                # 使用辅助方法过滤错误信息中的敏感内容
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 撤销修改失败: {safe_error_msg}")
                return False
        except Exception as e:
            # 使用统一错误处理
            error_response = self._handle_error(e, 'svn_revert')
            logger.error(f"❌ 撤销修改发生异常: {error_response['error']}")
            return False

    # ========= 分支管理功能 =========
    def svn_copy(self, src_path: str, dest_path: str, message: str = "Create branch/tag") -> Dict[str, Any]:
        """
        创建分支或标签（SVN通过copy实现）。
        
        Args:
            src_path: 源路径（可以是完整URL或相对于base_url的路径或本地路径）
            dest_path: 目标路径（通常是URL，可以是完整URL或相对于base_url的路径）
            message: 提交消息
            
        Returns:
            Dict: 包含成功状态和修订版本信息的字典
        """
        cmd = ["copy", "-m", message]
        # 获取完整的源路径和目标路径
        # 如果是URL格式，则使用完整URL；如果是本地路径，则直接使用
        if src_path.startswith(('http://', 'https://', 'svn://', 'file://')):
            full_src_path = self._get_full_url(src_path)
        else:
            # 检查是否为本地路径（存在的目录或文件）
            if os.path.exists(src_path):
                full_src_path = src_path
            else:
                # 否则视为相对URL路径
                full_src_path = self._get_full_url(src_path)
        
        full_dest_path = self._get_full_url(dest_path)
        cmd.extend([full_src_path, full_dest_path])
        result = self._run_svn_command(cmd)
        
        if result["success"]:
            # 尝试从输出中提取修订版本号
            output = result["stdout"]
            rev_match = re.search(r'Committed revision (\d+)\.', output)
            revision = rev_match.group(1) if rev_match else 'unknown'
            
            logger.info(f"✅ 成功创建分支/标签: {src_path} -> {dest_path}, 修订版本: {revision}")
            # 缓存失效，确保后续查询获取最新状态
            self._invalidate_cache(f"svn_info:{src_path}")
            self._invalidate_cache(f"svn_info:{dest_path}")
            self._invalidate_cache("svn_log")
            # 分支/标签列表缓存也需要失效
            self._invalidate_cache("svn_list_branches")
            self._invalidate_cache("svn_list_tags")
            return {
                "success": True,
                "revision": revision,
                "message": f"成功创建分支/标签"
            }
        else:
            error_msg = result.get('stderr', result.get('error', '未知错误'))
            logger.error(f"❌ 创建分支/标签失败: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "command": cmd
            }
    
    def svn_list_branches(self, repo_url: str) -> List[str]:
        """
        列出仓库中的所有分支。
        
        Args:
            repo_url: 仓库根URL（可以是完整URL或相对于base_url的路径）
            
        Returns:
            List[str]: 分支URL列表
        """
        # 性能优化：使用缓存机制
        cache_key = f"svn_list_branches:{repo_url}"
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"🔄 从缓存返回分支列表: {repo_url}")
            return cached_result
            
        # 获取完整的仓库URL
        full_repo_url = self._get_full_url(repo_url)
        # SVN通常使用标准的目录结构: /branches/ 包含分支
        branches_url = f"{full_repo_url.rstrip('/')}/branches"
        
        cmd = ["list", branches_url]
        result = self._run_svn_command(cmd)
        
        branches = []
        
        if result["success"]:
            output = result["stdout"]
            # 解析输出，每行一个分支名称
            for line in output.strip().split('\n'):
                if line.strip().endswith('/'):  # SVN列表中的目录以/结尾
                    branch_name = line.strip()
                    branches.append(f"{branches_url}/{branch_name}")
            
            logger.info(f"✅ 成功列出分支: {repo_url}, 找到 {len(branches)} 个分支")
        else:
            logger.warning(f"⚠️  列出分支失败，可能是标准分支目录不存在: {result.get('stderr', '')}")
            # 尝试使用info命令获取仓库根信息，然后检查结构
            info = self.svn_info(repo_url)
            if info:
                logger.info(f"仓库信息: {info.get('URL', '未知')}")
        
        # 设置缓存
        cache_key = f"svn_list_branches:{repo_url}"
        self._set_cache(cache_key, branches)
        return branches
    
    def svn_list_tags(self, repo_url: str) -> List[str]:
        """
        列出仓库中的所有标签。
        
        Args:
            repo_url: 仓库根URL（可以是完整URL或相对于base_url的路径）
            
        Returns:
            List[str]: 标签URL列表
        """
        # 性能优化：使用缓存机制
        cache_key = f"svn_list_tags:{repo_url}"
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"🔄 从缓存返回标签列表: {repo_url}")
            return cached_result
            
        # 获取完整的仓库URL
        full_repo_url = self._get_full_url(repo_url)
        # SVN通常使用标准的目录结构: /tags/ 包含标签
        tags_url = f"{full_repo_url.rstrip('/')}/tags"
        
        cmd = ["list", tags_url]
        result = self._run_svn_command(cmd)
        
        tags = []
        
        if result["success"]:
            output = result["stdout"]
            # 解析输出，每行一个标签名称
            for line in output.strip().split('\n'):
                if line.strip().endswith('/'):  # SVN列表中的目录以/结尾
                    tag_name = line.strip()
                    tags.append(f"{tags_url}/{tag_name}")
            
            logger.info(f"✅ 成功列出标签: {repo_url}, 找到 {len(tags)} 个标签")
        else:
            logger.warning(f"⚠️  列出标签失败，可能是标准标签目录不存在: {result.get('stderr', '')}")
        
        # 设置缓存
        cache_key = f"svn_list_tags:{repo_url}"
        self._set_cache(cache_key, tags)
        return tags
    
    # ========= 属性管理功能 =========
    def svn_propset(self, prop_name: str, prop_value: str, paths: List[str], recurse: bool = False) -> Dict[str, Any]:
        """
        设置SVN属性。
        
        Args:
            prop_name: 属性名称
            prop_value: 属性值
            paths: 要设置属性的路径列表
            recurse: 是否递归设置子目录
            
        Returns:
            Dict: 操作结果字典
        """
        try:
            # 使用辅助方法处理路径
            safe_paths, invalid_paths = self._process_paths(paths)
            
            if not safe_paths:
                logger.error("❌ 没有有效的路径可供设置属性")
                return {
                    "success": False,
                    "error": "没有有效的路径可供设置属性",
                    "property": prop_name
                }
            
            cmd = ["propset", prop_name, prop_value]
            
            if recurse:
                cmd.append("--recursive")
            
            cmd.extend(safe_paths)
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功设置属性 '{prop_name}' 到 {safe_paths}")
                
                # 使相关缓存失效
                for path in safe_paths:
                    self._invalidate_cache(f"svn_info:{path}")
                    self._invalidate_cache(f"svn_status:{os.path.dirname(path) or '.'}")
                
                return {
                    "success": True,
                    "message": f"成功设置属性 '{prop_name}'"
                }
            else:
                # 使用辅助方法处理错误信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 设置属性失败: {safe_error_msg}")
                return {
                    "success": False,
                    "error": safe_error_msg,
                    "property": prop_name
                }
        except Exception as e:
            error_info = self._handle_error(e, "svn_propset")
            logger.error(f"❌ 设置属性过程中发生异常: {error_info.get('error')}")
            return {
                "success": False,
                "error": error_info.get('error'),
                "property": prop_name
            }
    
    def svn_propget(self, prop_name: str, path: str, recurse: bool = False) -> Optional[Dict[str, str]]:
        """
        获取SVN属性值。
        
        Args:
            prop_name: 属性名称
            path: 要获取属性的路径
            recurse: 是否递归获取子目录
            
        Returns:
            Dict: 属性值字典，如果是递归模式，键为路径，值为属性值；
                 如果非递归模式，返回包含单个键值对的字典
        """
        try:
            # 使用辅助方法处理路径
            safe_paths, invalid_paths = self._process_paths([path])
            if not safe_paths:
                # 在测试环境中不记录警告
                if os.environ.get('PYTEST_CURRENT_TEST') is None:
                    logger.warning(f"⚠️ 无效路径: {path}")
                return None
            
            normalized_path = safe_paths[0]
            
            # 性能优化：使用缓存机制
            cache_key = f"svn_propget:{prop_name}:{normalized_path}:{recurse}"
            cached_result = self._get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"🔄 从缓存返回svn_propget结果: {prop_name}@{normalized_path}")
                return cached_result
            
            cmd = ["propget", prop_name, normalized_path]
            
            if recurse:
                cmd.append("--recursive")
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                output = result["stdout"]
                properties = {}
                
                if recurse:
                    # 递归模式输出格式: path - value
                    for line in output.strip().split('\n'):
                        if ' - ' in line:
                            p, val = line.split(' - ', 1)
                            properties[p.strip()] = val.strip()
                else:
                    # 非递归模式直接返回值
                    properties[normalized_path] = output.strip()
                
                logger.info(f"✅ 成功获取属性 '{prop_name}' from {normalized_path}")
                
                # 设置缓存
                self._set_cache(cache_key, properties)
                
                return properties
            else:
                # 使用辅助方法处理错误信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 获取属性失败: {safe_error_msg}")
                return None
        except Exception as e:
            error_info = self._handle_error(e, "svn_propget")
            logger.error(f"❌ 获取属性过程中发生异常: {error_info.get('error')}")
            return None
    
    def svn_proplist(self, path: str, recurse: bool = False) -> Optional[Dict[str, Dict[str, str]]]:
        """
        列出路径上的所有属性。
        
        Args:
            path: 要列出属性的路径
            recurse: 是否递归列出子目录
            
        Returns:
            Dict: 嵌套字典，键为路径，值为属性名和属性值的字典
        """
        try:
            # 使用辅助方法处理路径
            safe_paths, invalid_paths = self._process_paths([path])
            if not safe_paths:
                logger.warning(f"⚠️ 无效路径: {path}")
                return None
            
            normalized_path = safe_paths[0]
            
            # 性能优化：使用缓存机制
            cache_key = f"svn_proplist:{normalized_path}:{recurse}"
            cached_result = self._get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"🔄 从缓存返回svn_proplist结果: {normalized_path}")
                return cached_result
            
            cmd = ["proplist", "--verbose", normalized_path]
            
            if recurse:
                cmd.append("--recursive")
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                output = result["stdout"]
                all_properties = {}
                current_path = None
                properties = {}
                
                for line in output.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 检查是否是新路径的开始
                    if line.startswith("Properties on"):
                        # 保存前一个路径的属性（如果有）
                        if current_path and properties:
                            all_properties[current_path] = properties.copy()
                            properties.clear()
                        
                        # 提取新路径
                        # 格式: "Properties on 'path':" 或 "Properties on path:"
                        if "'" in line:
                            current_path = line.split("'", 1)[1].split("'", 1)[0]
                        else:
                            current_path = line.split('Properties on ', 1)[1].rstrip(':')
                    elif ':' in line and current_path:
                        # 属性行，格式: "property-name : property-value"
                        prop_parts = line.split(':', 1)
                        if len(prop_parts) == 2:
                            prop_name = prop_parts[0].strip()
                            prop_value = prop_parts[1].strip()
                            properties[prop_name] = prop_value
                
                # 别忘了最后一个路径
                if current_path and properties:
                    all_properties[current_path] = properties
                
                logger.info(f"✅ 成功列出属性 from {normalized_path}")
                
                # 设置缓存
                self._set_cache(cache_key, all_properties)
                
                return all_properties
            else:
                # 使用辅助方法处理错误信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 列出属性失败: {safe_error_msg}")
                return None
        except Exception as e:
            error_info = self._handle_error(e, "svn_proplist")
            logger.error(f"❌ 列出属性过程中发生异常: {error_info.get('error')}")
            return None
    
    def svn_propdel(self, prop_name: str, paths: List[str], recurse: bool = False) -> Dict[str, Any]:
        """
        删除SVN属性。
        
        Args:
            prop_name: 要删除的属性名称
            paths: 要删除属性的路径列表
            recurse: 是否递归删除子目录中的属性
            
        Returns:
            Dict: 操作结果字典
        """
        try:
            # 使用辅助方法处理路径
            safe_paths, invalid_paths = self._process_paths(paths)
            
            if not safe_paths:
                logger.error("❌ 没有有效的路径可供删除属性")
                return {
                    "success": False,
                    "error": "没有有效的路径可供删除属性",
                    "property": prop_name
                }
            
            cmd = ["propdel", prop_name]
            
            if recurse:
                cmd.append("--recursive")
            
            cmd.extend(safe_paths)
            
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功删除属性 '{prop_name}' from {safe_paths}")
                
                # 使相关缓存失效
                for path in safe_paths:
                    self._invalidate_cache(f"svn_info:{path}")
                    self._invalidate_cache(f"svn_status:{os.path.dirname(path) or '.'}")
                    self._invalidate_cache(f"svn_propget:{prop_name}:{path}:{recurse}")
                    self._invalidate_cache(f"svn_propget:{prop_name}:{path}:{not recurse}")
                
                return {
                    "success": True,
                    "message": f"成功删除属性 '{prop_name}'"
                }
            else:
                # 使用辅助方法处理错误信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = self._get_safe_error_message(error_msg)
                logger.error(f"❌ 删除属性失败: {safe_error_msg}")
                return {
                    "success": False,
                    "error": safe_error_msg,
                    "property": prop_name
                }
        except Exception as e:
            error_info = self._handle_error(e, "svn_propdel")
            logger.error(f"❌ 删除属性过程中发生异常: {error_info.get('error')}")
            return {
                "success": False,
                "error": error_info.get('error'),
                "property": prop_name
            }
    
    # ========= 冲突解决辅助功能 =========
    def svn_resolved(self, paths: List[str]) -> Dict[str, Any]:
        """
        标记冲突已解决。
        
        Args:
            paths: 要标记为已解决的文件路径列表
            
        Returns:
            Dict: 操作结果字典
        """
        try:
            # 使用辅助方法处理路径
            safe_paths, invalid_paths = self._process_paths(paths)
            
            if not safe_paths:
                logger.error("❌ 没有有效的路径可供标记冲突已解决")
                return {
                    "success": False,
                    "error": "没有有效的路径可供标记冲突已解决"
                }
            
            cmd = ["resolved"] + safe_paths
            result = self._run_svn_command(cmd)
            
            if result["success"]:
                logger.info(f"✅ 成功标记冲突已解决: {safe_paths}")
                
                # 使相关缓存失效
                for path in safe_paths:
                    self._invalidate_cache(f"svn_info:{path}")
                    self._invalidate_cache(f"svn_status:{os.path.dirname(path) or '.'}")
                
                return {
                    "success": True,
                    "message": "成功标记冲突已解决"
                }
            else:
                # 安全记录错误，避免记录敏感信息
                error_msg = result.get('stderr', result.get('error', '未知错误'))
                safe_error_msg = error_msg.replace(self.password or "", "******")
                logger.error(f"❌ 标记冲突已解决失败: {safe_error_msg}")
                return {
                    "success": False,
                    "error": safe_error_msg
                }
        except Exception as e:
            error_info = self._handle_error(e, "svn_resolved")
            logger.error(f"❌ 标记冲突已解决过程中发生异常: {error_info.get('error')}")
            return {
                "success": False,
                "error": error_info.get('error')
            }
    
    def get_repository_info(self, repository_path: str) -> Dict[str, Any]:
        """
        获取仓库信息
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            Dict[str, Any]: 包含仓库信息的字典
        """
        info = self.svn_info(repository_path)
        if info:
            return info
        return {"exists": False, "error": "获取仓库信息失败"}
    
    def is_repository_exist(self, repository_path: str) -> bool:
        """
        检查仓库是否存在
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            bool: 仓库是否存在
        """
        info = self.svn_info(repository_path)
        return info is not None
    
    def create_repository(self, repository_path: str, **kwargs) -> bool:
        """
        创建新仓库
        
        Args:
            repository_path: 仓库路径或标识符
            **kwargs: 其他创建参数
                - structure: 是否创建标准目录结构(trunk, branches, tags)
                - template_url: 用于复制的模板仓库URL
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 检查仓库是否已存在
            if self.is_repository_exist(repository_path):
                logger.warning(f"仓库已存在: {repository_path}")
                return False
                
            # 获取完整URL
            full_url = self._get_full_url(repository_path)
            
            # 检查是否提供了模板URL
            template_url = kwargs.get('template_url')
            if template_url:
                # 通过复制现有仓库来创建新仓库
                full_template_url = self._get_full_url(template_url)
                message = kwargs.get('message', 'Create repository from template')
                result = self.svn_copy(full_template_url, full_url, message)
                return result.get('success', False)
            else:
                # SVN服务器端创建通常需要svnadmin命令，这里尝试通过标准方式创建
                # 首先创建一个临时本地目录作为工作副本
                import tempfile
                import shutil
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 创建基本的SVN仓库结构（如果指定）
                    create_structure = kwargs.get('structure', True)
                    if create_structure:
                        # 创建trunk, branches, tags目录
                        os.makedirs(os.path.join(temp_dir, 'trunk'), exist_ok=True)
                        os.makedirs(os.path.join(temp_dir, 'branches'), exist_ok=True)
                        os.makedirs(os.path.join(temp_dir, 'tags'), exist_ok=True)
                        
                        # 创建一个README文件
                        with open(os.path.join(temp_dir, 'trunk', 'README.md'), 'w') as f:
                            f.write(f"# {os.path.basename(repository_path)}")
                    
                    # 注意：客户端不能直接创建SVN仓库，需要服务器端支持
                    # 这里提供一个清晰的错误消息，指导用户
                    logger.error(
                        f"无法直接创建SVN仓库 '{full_url}'。SVN仓库创建需要:")
                    logger.error("1. 在SVN服务器上使用'svnadmin create'命令")
                    logger.error("2. 或者通过SVN服务器的Web界面创建")
                    logger.error("3. 或者使用--template_url参数从现有仓库复制")
                    return False
        except Exception as e:
            logger.error(f"创建仓库失败: {str(e)}")
            return False
    
    def clone_or_checkout(self, source_path: str, local_path: str, **kwargs) -> bool:
        """
        克隆或检出仓库
        
        Args:
            source_path: 源仓库路径或URL
            local_path: 本地路径
            **kwargs: 其他参数（如分支、版本等）
            
        Returns:
            bool: 操作是否成功
        """
        # 适配现有svn_checkout方法
        revision = kwargs.get('revision')
        return self.svn_checkout(source_path, local_path, revision)
    
    def get_branches_or_tags(self, repository_path: str) -> List[str]:
        """
        获取仓库的分支或标签列表
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            List[str]: 分支或标签名称列表
        """
        # 适配现有分支列表方法
        try:
            branches = self.svn_list_branches(repository_path)
            tags = self.svn_list_tags(repository_path)
            return branches + tags
        except Exception as e:
            logger.error(f"获取分支和标签失败: {str(e)}")
            return []
    
    def get_latest_commit_info(self, repository_path: str) -> Dict[str, Any]:
        """
        获取最新提交信息
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            Dict[str, Any]: 包含提交信息的字典
        """
        # 适配现有日志方法，获取最新提交信息
        logs = self.svn_log(repository_path, limit=1)
        return logs[0] if logs else {"error": "获取提交信息失败"}
    
    def push_changes(self, local_path: str, remote_path: str, **kwargs) -> bool:
        """
        推送更改到远程仓库
        
        Args:
            local_path: 本地仓库路径
            remote_path: 远程仓库路径
            **kwargs: 其他推送参数
            
        Returns:
            bool: 推送是否成功
        """
        # 适配现有提交方法
        message = kwargs.get('message', 'Auto commit')
        return self.svn_commit(local_path, message)
    
    def get_tools(self) -> List[FunctionTool]:
        """获取SVN工具包支持的所有工具函数
        
        返回一个包含所有可用SVN操作工具的列表，包括统一接口方法、专用SVN操作方法、
        分支管理工具、属性管理工具、冲突解决工具。
        
        Returns:
            List[FunctionTool]: SVN工具函数列表
        """
        tools = [
            # 统一接口方法
            FunctionTool(func=self.get_repository_info),
            FunctionTool(func=self.is_repository_exist),
            FunctionTool(func=self.create_repository),
            FunctionTool(func=self.clone_or_checkout),
            FunctionTool(func=self.get_branches_or_tags),
            FunctionTool(func=self.get_latest_commit_info),
            FunctionTool(func=self.push_changes),
            # 原有专用方法
            FunctionTool(func=self.svn_checkout),
            FunctionTool(func=self.svn_update),
            FunctionTool(func=self.svn_info),
            FunctionTool(func=self.svn_log),
            FunctionTool(func=self.svn_commit),
            FunctionTool(func=self.svn_add),
            FunctionTool(func=self.svn_delete),
            FunctionTool(func=self.svn_status),
            FunctionTool(func=self.svn_add_all),
            FunctionTool(func=self.svn_revert),
            # 分支管理工具
            FunctionTool(func=self.svn_copy),
            FunctionTool(func=self.svn_list_branches),
            FunctionTool(func=self.svn_list_tags),
            # 属性管理工具
            FunctionTool(func=self.svn_propset),
            FunctionTool(func=self.svn_propget),
            FunctionTool(func=self.svn_proplist),
            FunctionTool(func=self.svn_propdel),
            # 冲突解决工具
            FunctionTool(func=self.svn_resolved)
        ]
        return tools


def create_svn_toolkit(
    username: Optional[str] = None, 
    password: Optional[str] = None,
    base_url: Optional[str] = None
) -> SVNToolkit:
    """
    创建一个基于命令行的SVNToolkit实例的辅助函数。
    
    Args:
        username: SVN用户名
        password: SVN密码
        base_url: SVN基础URL（包含端口号）
        
    Returns:
        SVNToolkit: 命令行SVN工具包实例
    """
    return SVNToolkit(username=username, password=password, base_url=base_url)