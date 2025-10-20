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
GitSyncToolkit - 统一的Git仓库同步工具包

此模块整合了原GitSyncToolkit和RepoSyncToolkit的Git相关功能，提供统一的接口
用于跨平台(GitHub、Gitee、GitLab)的Git仓库同步。包含完整的冲突解决策略、
增量同步、配置管理和错误处理机制。

注意：不再保留对SVN的支持，仅专注于Git平台同步。
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Any, Callable, Literal
from functools import wraps

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.git_base_toolkit import GitBaseToolkit
from camel.toolkits.github_toolkit import GithubToolkit
from camel.toolkits.gitee_toolkit import GiteeToolkit
from camel.toolkits.gitlab_toolkit import GitLabToolkit

logger = logging.getLogger(__name__)


class GitPlatformType(Enum):
    """Git托管平台类型枚举。"""
    GITHUB = "github"
    GITEE = "gitee"
    GITLAB = "gitlab"


# 冲突解决策略枚举
class ConflictResolutionStrategy(Enum):
    """冲突解决策略枚举，适用于所有Git平台。"""
    SOURCE_WINS = "source_wins"             # 源仓库优先
    TARGET_WINS = "target_wins"             # 目标仓库优先
    ASK = "ask"                             # 询问用户
    MERGE = "merge"                         # 尝试自动合并
    TIMESTAMP_BASED = "timestamp_based"     # 基于最后提交时间决定


class SyncResult:
    """同步结果数据类。"""
    def __init__(self, success: bool, message: str, changes: List[str] = None, errors: List[str] = None):
        self.success = success
        self.message = message
        self.changes = changes or []
        self.errors = errors or []


@dataclass
class GitSyncConfig:
    """
    Git仓库同步配置数据类。
    
    支持指定单一权威源代码仓库，并向其他Git仓库进行单向同步。
    支持GitHub、Gitee、GitLab平台，并提供跨平台的冲突解决策略。
    """
    # 权威源代码仓库（必须指定）
    source_platform: GitPlatformType
    source_repo: str  # 格式: owner/repo 或完整URL
    source_base_url: Optional[str] = None  # 自定义API基础URL（如自托管GitLab）
    source_namespace: Optional[str] = None  # 源仓库命名空间（所有者）
    
    # 目标仓库列表（至少需要一个）
    target_configs: List[Dict[str, Any]] = field(default_factory=list)
    
    # 认证信息
    source_credentials: Dict[str, str] = field(default_factory=dict)
    
    # 同步配置
    sync_branches: Union[str, List[str], Literal["all"]] = "main"  # 要同步的分支
    sync_tags: bool = True  # 是否同步标签
    incremental_sync: bool = True  # 是否使用增量同步
    force_push: bool = False  # 是否强制推送（谨慎使用）
    allow_recreate: bool = False  # 是否允许重新创建仓库
    
    # 冲突解决配置
    conflict_resolution: Union[str, ConflictResolutionStrategy] = ConflictResolutionStrategy.SOURCE_WINS  # 冲突解决策略
    
    # 高级功能配置
    sync_prune: bool = True  # 是否删除远程已删除的分支/标签
    
    # 性能优化配置
    shallow_clone: bool = True  # 是否使用浅克隆提高性能
    clone_depth: int = 100  # 浅克隆深度
    timeout_seconds: int = 300  # 同步操作超时时间
    
    # 本地配置
    local_repo_path: Optional[str] = None  # 本地仓库路径，如果为None则使用临时目录
    cleanup_local: bool = True  # 同步完成后是否清理本地仓库
    
    # 错误处理配置
    max_retries: int = 3  # 操作失败时的最大重试次数
    
    def __post_init__(self):
        """初始化后从环境变量读取访问令牌。"""
        # 从环境变量读取源平台的访问令牌（如果未提供）
        if not self.source_credentials.get('access_token'):
            env_var_name = f"{self.source_platform.value.upper()}_ACCESS_TOKEN"
            env_token = os.environ.get(env_var_name)
            if env_token:
                self.source_credentials['access_token'] = env_token
        
        # 从环境变量读取目标平台的访问令牌（如果未提供）
        for target_config in self.target_configs:
            if not target_config.get('credentials', {}).get('access_token'):
                platform = target_config['platform']
                env_var_name = f"{platform.upper()}_ACCESS_TOKEN"
                env_token = os.environ.get(env_var_name)
                if env_token:
                    if 'credentials' not in target_config:
                        target_config['credentials'] = {}
                    target_config['credentials']['access_token'] = env_token
    
    @property
    def has_valid_targets(self) -> bool:
        """检查是否有有效的目标仓库。"""
        return len(self.target_configs) > 0
    
    def validate(self) -> List[str]:
        """验证配置有效性，返回错误列表。"""
        errors = []
        
        # 验证源平台
        if not isinstance(self.source_platform, GitPlatformType):
            errors.append(f"无效的源平台类型: {self.source_platform}")
        
        # 验证源仓库
        if not self.source_repo:
            errors.append("必须指定源仓库")
        
        # 验证源平台访问令牌
        if not self.source_credentials.get('access_token'):
            errors.append(f"缺少{self.source_platform.value}平台的访问令牌")
        
        # 验证目标仓库
        if not self.has_valid_targets:
            errors.append("必须至少指定一个目标仓库")
        else:
            # 验证每个目标仓库配置
            for i, target in enumerate(self.target_configs):
                if 'platform' not in target or 'repo' not in target:
                    errors.append(f"目标仓库配置 {i} 必须包含platform和repo字段")
                if 'platform' in target and target['platform'] not in [p.value for p in GitPlatformType]:
                    errors.append(f"目标仓库配置 {i} 包含无效的平台类型: {target['platform']}")
                if not target.get('credentials', {}).get('access_token'):
                    errors.append(f"目标仓库配置 {i} 缺少访问令牌")
        
        # 验证同步分支
        if not self.sync_branches:
            errors.append("必须指定至少一个同步分支")
        
        # 验证超时时间
        if self.timeout_seconds <= 0:
            errors.append("超时时间必须大于0")
        
        # 验证最大重试次数
        if self.max_retries < 0:
            errors.append("最大重试次数不能为负数")
        
        return errors


class GitSyncToolkit(BaseToolkit):
    """
    Git仓库同步工具包，支持跨平台Git仓库同步。
    
    利用GitBaseToolkit提供统一的接口，支持从单一权威源仓库同步到多个目标仓库。
    包含增量同步功能，改进的错误处理，以及对所有平台适用的冲突解决策略。
    """
    
    def __init__(self, timeout: Optional[float] = None, config_path: Optional[str] = None):
        """
        初始化Git同步工具包。
        
        Args:
            timeout: 操作超时时间（秒）
            config_path: 配置文件路径
        """
        super().__init__(timeout=timeout)
        
        # 配置存储
        self.configs: Dict[str, GitSyncConfig] = {}
        
        # 正在运行的同步任务
        self._running_syncs: Set[str] = set()
        
        # 工具包缓存 - 避免重复创建工具包实例
        self._toolkits: Dict[str, GitBaseToolkit] = {}
        
        # 同步历史记录 - 用于增量同步
        self._sync_history: Dict[str, Dict[str, str]] = {}
        self._history_file = os.path.join(os.path.expanduser("~"), ".camel_git_sync_history.json")
        
        # 配置文件路径
        self.config_path = config_path
        
        # 加载历史记录
        self._load_history()
        
        # 如果提供了配置文件，加载配置
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> None:
        """
        从配置文件加载同步配置。
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # 加载多个同步配置
            if 'sync_configs' in config_data:
                for sync_config in config_data['sync_configs']:
                    try:
                        # 转换冲突解决策略
                        conflict_resolution = sync_config.get('conflict_resolution', 'source_wins')
                        if isinstance(conflict_resolution, str):
                            conflict_resolution = ConflictResolutionStrategy(conflict_resolution)
                        
                        self.create_sync_config(
                            source_platform=sync_config['source_platform'],
                            source_repo=sync_config['source_repo'],
                            target_configs=sync_config['target_configs'],
                            source_credentials=sync_config.get('source_credentials', {}),
                            source_base_url=sync_config.get('source_base_url'),
                            source_namespace=sync_config.get('source_namespace'),
                            sync_branches=sync_config.get('sync_branches', 'main'),
                            sync_tags=sync_config.get('sync_tags', True),
                            incremental_sync=sync_config.get('incremental_sync', True),
                            force_push=sync_config.get('force_push', False),
                            allow_recreate=sync_config.get('allow_recreate', False),
                            conflict_resolution=conflict_resolution,
                            sync_prune=sync_config.get('sync_prune', True),
                            shallow_clone=sync_config.get('shallow_clone', True),
                            clone_depth=sync_config.get('clone_depth', 100),
                            timeout_seconds=sync_config.get('timeout_seconds', 300),
                            local_repo_path=sync_config.get('local_repo_path'),
                            cleanup_local=sync_config.get('cleanup_local', True),
                            max_retries=sync_config.get('max_retries', 3)
                        )
                    except Exception as e:
                        logger.error(f"加载同步配置失败: {str(e)}")
            
            # 加载全局凭证
            if 'credentials' in config_data:
                for platform, creds in config_data['credentials'].items():
                    # 设置环境变量作为备用
                    if 'access_token' in creds:
                        env_var_name = f"{platform.upper()}_ACCESS_TOKEN"
                        os.environ[env_var_name] = creds['access_token']
                        
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    def _load_history(self) -> None:
        """加载同步历史记录。"""
        try:
            if os.path.exists(self._history_file):
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    self._sync_history = json.load(f)
        except Exception as e:
            logger.warning(f"加载同步历史失败: {str(e)}")
    
    def _save_history(self) -> None:
        """保存同步历史记录。"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._history_file), exist_ok=True)
            
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(self._sync_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存同步历史失败: {str(e)}")
    
    def _generate_config_id(self, config: GitSyncConfig) -> str:
        """
        根据配置生成唯一的配置ID。
        
        Args:
            config: 同步配置
            
        Returns:
            str: 唯一的配置ID
        """
        source_str = f"{config.source_platform.value}_{config.source_repo.replace('/', '_')}"
        targets_str = "_to_".join([f"{t['platform']}_{t['repo'].replace('/', '_')}" for t in config.target_configs])
        return f"{source_str}_to_{targets_str}"
    
    def _validate_config(self, config: GitSyncConfig) -> None:
        """
        验证同步配置是否有效。
        
        Args:
            config: 同步配置
            
        Raises:
            ValueError: 如果配置无效
        """
        errors = config.validate()
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
    
    def _get_platform_toolkit(self, platform: str, **kwargs) -> GitBaseToolkit:
        """
        获取或创建平台工具包实例。
        
        Args:
            platform: 平台名称
            **kwargs: 额外参数，如access_token、base_url等
            
        Returns:
            GitBaseToolkit: 对应的平台工具包实例
        """
        # 创建缓存键
        cache_key = f"{platform}_{kwargs.get('base_url', kwargs.get('instance_name', 'default'))}"
        
        # 如果工具包已缓存，直接返回
        if cache_key in self._toolkits:
            return self._toolkits[cache_key]
        
        # 根据平台类型创建对应的工具包
        access_token = kwargs.get('access_token')
        base_url = kwargs.get('base_url')
        timeout = kwargs.get('timeout', self.timeout)
        
        if platform.lower() == "github":
            toolkit = GithubToolkit(
                access_token=access_token,
                timeout=timeout
            )
        elif platform.lower() == "gitee":
            toolkit = GiteeToolkit(
                access_token=access_token,
                timeout=timeout
            )
        elif platform.lower() == "gitlab":
            # 对于GitLab，使用instance_name而不是base_url
            instance_name = kwargs.get('instance_name', 'default')
            namespace = kwargs.get('namespace')
            verify_ssl = kwargs.get('verify_ssl', True)
            
            toolkit = GitLabToolkit(
                access_token=access_token,
                instance_name=instance_name,
                namespace=namespace,
                timeout=timeout,
                verify_ssl=verify_ssl
            )
        else:
            raise ValueError(f"不支持的平台: {platform}")
        
        # 缓存工具包
        self._toolkits[cache_key] = toolkit
        return toolkit
    
    def _execute_with_retry(self, func: Callable, max_retries: int = 3, backoff_factor: float = 2.0, **kwargs) -> Any:
        """
        带重试机制的函数执行，专门处理subprocess.run的编码问题和各种错误情况。
        
        Args:
            func: 要执行的函数
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            **kwargs: 传递给函数的参数
            
        Returns:
            Any: 函数执行结果
            
        Raises:
            Exception: 如果所有重试都失败
            ValueError: 如果参数无效
            KeyboardInterrupt: 如果用户中断操作
        """
        # 参数验证
        if max_retries < 1:
            raise ValueError("max_retries 必须大于等于 1")
        if backoff_factor <= 0:
            raise ValueError("backoff_factor 必须大于 0")
        
        last_error = None
        command_name = func.__name__ if hasattr(func, '__name__') else str(func)
        cmd_info = kwargs.get('cmd', kwargs.get('args', '未知命令'))
        logger.debug(f"准备执行: {command_name}, 命令: {cmd_info}")
        
        # 特殊处理subprocess.run函数，使用我们的安全包装器
        if func == subprocess.run:
            # 使用_safe_subprocess_run替代直接调用subprocess.run
            wrapped_func = self._safe_subprocess_run
            
            # 获取原始的check参数
            original_check = kwargs.pop('check', False)
            
            # 确保我们不会传递text=True参数
            if 'text' in kwargs:
                kwargs.pop('text')
            if 'universal_newlines' in kwargs:
                kwargs.pop('universal_newlines')
            
            # 直接使用kwargs调用wrapped_func，不需要额外的args
            for attempt in range(max_retries):
                try:
                    logger.debug(f"执行命令 (尝试 {attempt + 1}/{max_retries}): {cmd_info}")
                    result = wrapped_func(**kwargs)
                    logger.debug(f"命令执行完成，返回码: {result.returncode}")
                    
                    # 由于_safe_subprocess_run已经处理了编码，这里不需要再处理
                    # 检查返回码
                    if original_check and result.returncode != 0:
                        error_msg = f"命令执行失败，返回码: {result.returncode}"
                        logger.error(error_msg)
                        raise subprocess.CalledProcessError(
                            returncode=result.returncode,
                            cmd=cmd_info,
                            output=result.stdout,
                            stderr=result.stderr
                        )
                    
                    return result
                except Exception as e:
                    last_error = e
                    
                    # 判断是否为致命错误（不需要重试）
                    is_fatal_error = False
                    if isinstance(e, subprocess.CalledProcessError):
                        # 分析返回码，某些错误可能是致命的
                        # 例如权限错误、认证失败等通常返回码为128
                        if hasattr(e, 'returncode') and e.returncode == 128:
                            is_fatal_error = True
                            logger.error(f"致命错误: 权限问题或认证失败，返回码: {e.returncode}")
                    elif isinstance(e, (FileNotFoundError, PermissionError)):
                        is_fatal_error = True
                        logger.error(f"致命错误: {str(e)}")
                    
                    if is_fatal_error:
                        logger.error("检测到致命错误，停止重试")
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {str(e)}，{wait_time:.1f}秒后重试...")
                    # 记录错误详情，特别是编码错误
                    if isinstance(e, UnicodeDecodeError):
                        logger.error(f"编码错误详情: 位置={e.start}, 字节={e.object[e.start:e.start+10] if e.start+10 < len(e.object) else e.object[e.start:]}")
                    
                    # 允许用户中断重试等待
                    try:
                        time.sleep(wait_time)
                    except KeyboardInterrupt:
                        logger.error("用户中断重试")
                        raise
        else:
            # 对于非subprocess.run函数，使用标准重试逻辑
            for attempt in range(max_retries):
                try:
                    return func(**kwargs)
                except Exception as e:
                    last_error = e
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {str(e)}，{wait_time:.1f}秒后重试...")
                    
                    # 允许用户中断重试等待
                    try:
                        time.sleep(wait_time)
                    except KeyboardInterrupt:
                        logger.error("用户中断重试")
                        raise
        
        logger.error(f"所有 {max_retries} 次尝试都失败")
        # 记录最后错误的详细信息
        if isinstance(last_error, UnicodeDecodeError):
            logger.error(f"最终编码错误详情: 位置={last_error.start}, 字节={last_error.object[last_error.start:last_error.start+10] if last_error.start+10 < len(last_error.object) else last_error.object[last_error.start:]}")
        raise last_error
    
    def _safe_subprocess_run(self, cmd, cwd=None, check=False, capture_output=True, **kwargs):
        """
        安全的subprocess.run包装器，确保正确处理编码问题。
        
        Args:
            cmd: 要执行的命令
            cwd: 工作目录
            check: 是否检查返回码
            capture_output: 是否捕获输出
            **kwargs: 其他参数
            
        Returns:
            subprocess.CompletedProcess: 执行结果
        """
        # 确保不使用text=True
        if 'text' in kwargs:
            kwargs.pop('text')
        if 'universal_newlines' in kwargs:
            kwargs.pop('universal_newlines')
        
        # 确保总是捕获输出
        if capture_output:
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE
        
        logger.debug(f"执行命令: {cmd}，工作目录: {cwd}")
        
        # 执行命令
        result = subprocess.run(cmd, cwd=cwd, check=False, **kwargs)
        
        # 手动处理输出编码
        if hasattr(result, 'stdout') and result.stdout is not None:
            try:
                result.stdout = self._decode_output(result.stdout)
            except Exception as e:
                logger.error(f"解码stdout失败: {str(e)}")
                result.stdout = str(result.stdout)
        
        if hasattr(result, 'stderr') and result.stderr is not None:
            try:
                result.stderr = self._decode_output(result.stderr)
            except Exception as e:
                logger.error(f"解码stderr失败: {str(e)}")
                result.stderr = str(result.stderr)
        
        # 手动检查返回码
        if check and result.returncode != 0:
            error_msg = f"命令执行失败: {cmd}，返回码: {result.returncode}"
            logger.error(error_msg)
            logger.error(f"错误输出: {result.stderr}")
            raise subprocess.CalledProcessError(
                returncode=result.returncode,
                cmd=cmd,
                output=result.stdout,
                stderr=result.stderr
            )
        
        return result

    
    def _decode_output(self, output_data) -> str:
        """
        尝试使用多种编码解码输出，确保在各种环境下都能正常工作。
        
        Args:
            output_data: 要解码的数据（bytes或str）
            
        Returns:
            str: 解码后的字符串
        """
        # 首先检查输入类型，如果已经是字符串，直接返回
        if isinstance(output_data, str):
            logger.debug("输入已经是字符串，直接返回")
            return output_data
            
        # 如果是bytes，尝试解码
        elif isinstance(output_data, bytes):
            # 使用latin-1作为最安全的选项，因为它可以解码任何字节序列
            try:
                logger.debug(f"使用latin-1解码字节数据，长度: {len(output_data)}字节")
                return output_data.decode('latin-1')
            except Exception as e:
                logger.warning(f"latin-1解码失败: {str(e)}")
        
        # 最坏情况，直接转换为字符串
        logger.debug(f"所有解码尝试失败，使用str()转换")
        return str(output_data)
    
    def create_sync_config(
        self,
        source_platform: str,
        source_repo: str,
        target_configs: List[Dict[str, Any]],
        source_credentials: Optional[Dict[str, str]] = None,
        source_base_url: Optional[str] = None,
        source_namespace: Optional[str] = None,
        sync_branches: Union[str, List[str], Literal["all"]] = "main",
        sync_tags: bool = True,
        incremental_sync: bool = True,
        force_push: bool = False,
        allow_recreate: bool = False,
        conflict_resolution: Union[str, ConflictResolutionStrategy] = ConflictResolutionStrategy.SOURCE_WINS,
        sync_prune: bool = True,
        shallow_clone: bool = True,
        timeout_seconds: int = 300,
        local_repo_path: Optional[str] = None,
        cleanup_local: bool = True,
        max_retries: int = 3
    ) -> str:
        """
        创建一个新的Git仓库同步配置。
        
        Args:
            source_platform: 源平台类型 (github, gitee, gitlab)
            source_repo: 源仓库信息 (格式: owner/repo)
            target_configs: 目标仓库配置列表，每个配置包含platform和repo字段
            source_credentials: 源平台认证信息
            source_base_url: 源平台的自定义API基础URL
            source_namespace: 源仓库命名空间（所有者）
            sync_branches: 需要同步的分支
            sync_tags: 是否同步标签
            incremental_sync: 是否使用增量同步
            force_push: 是否强制推送
            allow_recreate: 是否允许重新创建仓库
            conflict_resolution: 冲突解决策略
            sync_prune: 是否删除远程已删除的分支/标签
            shallow_clone: 是否使用浅克隆
            timeout_seconds: 同步操作超时时间
            local_repo_path: 本地仓库路径
            cleanup_local: 同步完成后是否清理本地仓库
            max_retries: 操作失败时的最大重试次数
            
        Returns:
            str: 配置ID
        """
        # 验证并转换源平台类型
        try:
            platform = GitPlatformType(source_platform.lower())
        except ValueError:
            valid_platforms = ', '.join([p.value for p in GitPlatformType])
            raise ValueError(f"无效的源平台类型: {source_platform}。可用值: {valid_platforms}")
        
        # 验证目标仓库配置
        if not target_configs:
            raise ValueError("至少需要一个目标仓库配置")
        
        for i, target_config in enumerate(target_configs):
            # 验证必需字段
            if 'platform' not in target_config:
                raise ValueError(f"目标仓库配置 {i} 缺少必需的'platform'字段")
            if 'repo' not in target_config:
                raise ValueError(f"目标仓库配置 {i} 缺少必需的'repo'字段")
            
            # 验证平台类型
            try:
                GitPlatformType(target_config['platform'].lower())
            except ValueError:
                raise ValueError(f"目标仓库配置 {i} 包含无效的平台类型: {target_config['platform']}")
        
        # 转换冲突解决策略
        if isinstance(conflict_resolution, str):
            try:
                conflict_resolution = ConflictResolutionStrategy(conflict_resolution.lower())
            except ValueError:
                valid_strategies = ', '.join([s.value for s in ConflictResolutionStrategy])
                raise ValueError(f"无效的冲突解决策略: {conflict_resolution}。可用值: {valid_strategies}")
        
        # 创建配置
        config = GitSyncConfig(
            source_platform=platform,
            source_repo=source_repo,
            source_base_url=source_base_url,
            source_namespace=source_namespace,
            target_configs=target_configs,
            source_credentials=source_credentials or {},
            sync_branches=sync_branches,
            sync_tags=sync_tags,
            incremental_sync=incremental_sync,
            force_push=force_push,
            allow_recreate=allow_recreate,
            conflict_resolution=conflict_resolution,
            sync_prune=sync_prune,
            shallow_clone=shallow_clone,
            clone_depth=100,
            timeout_seconds=timeout_seconds,
            local_repo_path=local_repo_path,
            cleanup_local=cleanup_local,
            max_retries=max_retries
        )
        
        # 添加配置
        return self.add_sync_config(config)
    
    def add_sync_config(self, config: GitSyncConfig) -> str:
        """
        添加一个同步配置。
        
        Args:
            config: 同步配置
            
        Returns:
            str: 配置ID
        """
        # 验证配置
        self._validate_config(config)
        
        # 生成唯一的配置ID
        config_id = self._generate_config_id(config)
        
        # 保存配置
        self.configs[config_id] = config
        logger.info(f"已添加Git同步配置: {config_id}")
        
        # 保存到配置文件（如果指定了）
        if self.config_path:
            self.save_configs(self.config_path)
        
        return config_id
    
    def save_configs(self, config_path: str) -> None:
        """
        保存所有配置到文件。
        
        Args:
            config_path: 配置文件路径
        """
        try:
            config_data = {
                'sync_configs': [],
                'credentials': {}
            }
            
            # 保存同步配置
            for config in self.configs.values():
                sync_config_dict = {
                    'source_platform': config.source_platform.value,
                    'source_repo': config.source_repo,
                    'source_base_url': config.source_base_url,
                    'source_namespace': config.source_namespace,
                    'target_configs': config.target_configs,
                    'source_credentials': config.source_credentials,
                    'sync_branches': config.sync_branches,
                    'sync_tags': config.sync_tags,
                    'incremental_sync': config.incremental_sync,
                    'force_push': config.force_push,
                    'allow_recreate': config.allow_recreate,
                    'shallow_clone': config.shallow_clone,
                    'timeout_seconds': config.timeout_seconds,
                    'local_repo_path': config.local_repo_path,
                    'cleanup_local': config.cleanup_local
                }
                config_data['sync_configs'].append(sync_config_dict)
            
            # 保存凭证（从环境变量获取）
            for platform in GitPlatformType:
                env_var_name = f"{platform.value.upper()}_ACCESS_TOKEN"
                token = os.environ.get(env_var_name)
                if token:
                    config_data['credentials'][platform.value] = {'access_token': token}
            
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # 保存到文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"已保存配置到: {config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
    
    def remove_sync_config(self, config_id: str) -> bool:
        """
        移除指定的同步配置。
        
        Args:
            config_id: 配置ID
            
        Returns:
            bool: 是否成功移除
        """
        if config_id in self.configs:
            # 移除配置
            del self.configs[config_id]
            logger.info(f"已移除同步配置: {config_id}")
            
            # 如果有运行中的同步任务，等待其完成
            while config_id in self._running_syncs:
                logger.info(f"等待配置 {config_id} 的同步任务完成...")
                time.sleep(1)
            
            # 更新配置文件
            if self.config_path:
                self.save_configs(self.config_path)
            
            return True
        
        logger.warning(f"配置ID不存在: {config_id}")
        return False
    
    def get_config_list(self) -> List[Dict[str, Any]]:
        """
        获取所有同步配置的列表。
        
        Returns:
            List[Dict[str, Any]]: 配置列表
        """
        config_list = []
        for config_id, config in self.configs.items():
            config_list.append({
                'id': config_id,
                'source_platform': config.source_platform.value,
                'source_repo': config.source_repo,
                'target_count': len(config.target_configs),
                'incremental_sync': config.incremental_sync,
                'sync_branches': config.sync_branches
            })
        return config_list
    
    def get_sync_history(self, target_key: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """
        获取同步历史记录。
        
        Args:
            target_key: 可选的目标键，格式为 "platform:repo"
            
        Returns:
            Dict[str, Dict[str, str]]: 同步历史记录
        """
        if target_key:
            return {target_key: self._sync_history.get(target_key, {})}
        return self._sync_history
    
    def clear_sync_history(self, target_key: Optional[str] = None) -> None:
        """
        清除同步历史记录。
        
        Args:
            target_key: 可选的目标键，格式为 "platform:repo"
        """
        if target_key:
            if target_key in self._sync_history:
                del self._sync_history[target_key]
                logger.info(f"已清除目标 {target_key} 的同步历史")
        else:
            self._sync_history.clear()
            logger.info("已清除所有同步历史")
        
        self._save_history()
    
    def sync_repositories(self, config_id: str) -> SyncResult:
        """
        执行Git仓库同步操作。
        
        Args:
            config_id: 配置ID
            
        Returns:
            SyncResult: 同步结果
        """
        # 检查配置是否存在
        if config_id not in self.configs:
            return SyncResult(
                success=False,
                message=f"同步配置不存在: {config_id}",
                errors=[f"配置ID {config_id} 未找到"]
            )
        
        # 检查是否已经在同步
        if config_id in self._running_syncs:
            return SyncResult(
                success=False,
                message=f"同步任务已在运行中: {config_id}",
                errors=["该配置的同步任务已在进行中"]
            )
        
        config = self.configs[config_id]
        self._running_syncs.add(config_id)
        
        try:
            # 使用超时机制执行同步
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def sync_thread():
                try:
                    result = self._do_sync(config)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put(e)
            
            thread = threading.Thread(target=sync_thread)
            thread.daemon = True  # 将线程设置为守护线程，确保主程序退出时线程也会退出
            thread.start()
            thread.join(config.timeout_seconds)
            
            if thread.is_alive():
                logger.error(f"同步操作超时: {config.timeout_seconds}秒，正在清理资源")
                # 注意：Python中无法安全地强制终止线程，我们只能标记为超时并返回
                return SyncResult(
                    success=False,
                    message=f"同步操作超时: {config.timeout_seconds}秒",
                    errors=["同步操作超过配置的超时时间"]
                )
            
            # 获取结果
            result_item = result_queue.get_nowait()
            
            if isinstance(result_item, Exception):
                logger.error(f"同步线程发生错误: {str(result_item)}")
                return SyncResult(
                    success=False,
                    message=f"同步失败: {str(result_item)}",
                    errors=[str(result_item)]
                )
            
            return result_item
        finally:
            self._running_syncs.remove(config_id)
            # 保存历史记录
            self._save_history()
    
    def _do_sync(self, config: GitSyncConfig) -> SyncResult:
        """
        执行实际的同步操作。
        
        Args:
            config: 同步配置
            
        Returns:
            SyncResult: 同步结果
        """
        changes = []
        errors = []
        local_repo_path = None
        temp_dir = None  # 用于保存临时目录路径，以便在清理阶段使用
        
        try:
            logger.info(f"开始从 {config.source_platform.value}:{config.source_repo} 同步到 {len(config.target_configs)} 个目标仓库")
            logger.info(f"同步配置: 分支={config.sync_branches}, 标签={config.sync_tags}, 增量={config.incremental_sync}")
            
            # 创建临时目录或使用指定目录
            if config.local_repo_path:
                local_repo_path = config.local_repo_path
                os.makedirs(local_repo_path, exist_ok=True)
                logger.debug(f"使用指定的本地仓库路径: {local_repo_path}")
            else:
                temp_dir = tempfile.mkdtemp(prefix="camel_git_sync_")
                local_repo_path = os.path.join(temp_dir, os.path.basename(config.source_repo))
                logger.debug(f"创建临时目录: {temp_dir}")
            
            # 获取源平台工具包
            source_token = config.source_credentials.get('access_token')
            if not source_token:
                # 尝试从环境变量获取
                env_var_name = f"{config.source_platform.value.upper()}_ACCESS_TOKEN"
                source_token = os.environ.get(env_var_name)
                if not source_token:
                    raise ValueError(f"无法获取{config.source_platform.value}的访问令牌")
            
            # 准备工具包参数
            toolkit_kwargs = {
                'access_token': source_token,
                'timeout': self.timeout or config.timeout_seconds
            }
            
            # 根据平台类型添加特定参数
            if config.source_platform == GitPlatformType.GITLAB:
                toolkit_kwargs['instance_name'] = config.source_base_url or 'default'
                toolkit_kwargs['namespace'] = config.source_namespace
            elif config.source_platform in [GitPlatformType.GITHUB, GitPlatformType.GITEE] and config.source_base_url:
                toolkit_kwargs['base_url'] = config.source_base_url
            
            source_toolkit = self._get_platform_toolkit(
                config.source_platform.value,
                **toolkit_kwargs
            )
            
            # 克隆或更新源仓库
            local_repo = self._prepare_local_repo(local_repo_path, config, source_toolkit)
            if not local_repo:
                raise RuntimeError("准备本地仓库失败")
            
            # 同步到每个目标仓库
            success_count = 0
            for idx, target_config in enumerate(config.target_configs):
                target_platform = GitPlatformType(target_config['platform'])
                target_repo = target_config['repo']
                target_credentials = target_config.get('credentials', {})
                target_base_url = target_config.get('base_url')
                target_namespace = target_config.get('namespace', 'root')  # 默认为root
                
                logger.info(f"同步目标 {idx+1}/{len(config.target_configs)}: {target_platform.value}:{target_repo}")
                
                try:
                    # 获取目标平台工具包
                    target_token = target_credentials.get('access_token')
                    if not target_token:
                        # 尝试从环境变量获取
                        env_var_name = f"{target_platform.value.upper()}_ACCESS_TOKEN"
                        target_token = os.environ.get(env_var_name)
                        if not target_token:
                            raise ValueError(f"无法获取{target_platform.value}的访问令牌")
                    
                    # 准备目标工具包参数
                    target_kwargs = {
                        'access_token': target_token,
                        'timeout': self.timeout or config.timeout_seconds
                    }
                    
                    # 根据平台类型添加特定参数
                    if target_platform == GitPlatformType.GITLAB:
                        target_kwargs['instance_name'] = target_base_url or 'default'
                        target_kwargs['namespace'] = target_namespace
                        target_kwargs['verify_ssl'] = target_config.get('verify_ssl', True)
                    elif target_platform in [GitPlatformType.GITHUB, GitPlatformType.GITEE] and target_base_url:
                        target_kwargs['base_url'] = target_base_url
                    
                    # 获取目标平台工具包
                    target_toolkit = self._get_platform_toolkit(
                        target_platform.value,
                        **target_kwargs
                    )
                    
                    # 检查目标仓库是否存在，如果不存在则创建
                    repo_exists = target_toolkit.repository_exists(target_repo)
                    
                    if not repo_exists:
                        logger.info(f"目标仓库不存在，正在创建: {target_repo}")
                        # 从源仓库获取信息用于创建目标仓库
                        source_info = None
                        try:
                            source_info = source_toolkit.get_repository(config.source_repo)
                        except Exception as e:
                            logger.warning(f"获取源仓库信息失败: {str(e)}，使用默认设置创建目标仓库")
                        
                        # 创建仓库
                        create_kwargs = {
                            'description': getattr(source_info, 'description', '') if source_info else "",
                            'private': getattr(source_info, 'private', True) if source_info else True
                        }
                        
                        # 使用重试机制创建仓库
                        self._execute_with_retry(
                            func=target_toolkit.create_repository,
                            max_retries=config.max_retries,
                            repo_name=target_repo,
                            **create_kwargs
                        )
                        changes.append(f"已创建目标仓库: {target_repo}")
                    elif config.allow_recreate:
                        logger.warning(f"目标仓库已存在且allow_recreate=True，但目前不支持仓库重建")
                    
                    # 执行同步
                    target_changes = self._sync_to_git_platform(
                        local_repo,
                        target_platform,
                        target_repo,
                        target_credentials,
                        config,
                        target_toolkit
                    )
                    changes.extend(target_changes)
                    success_count += 1
                    
                except Exception as e:
                    error_msg = f"同步到 {target_platform.value}:{target_repo} 失败: {str(e)}"
                    logger.error(error_msg, exc_info=True)  # 使用exc_info=True记录完整堆栈
                    errors.append(error_msg)
            
            # 生成最终的成功消息
            success = len(errors) == 0
            message = f"Git同步完成: 成功同步到 {success_count}/{len(config.target_configs)} 个目标仓库，变更 {len(changes)} 项"
            
            return SyncResult(
                success=success,
                message=message,
                changes=changes,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"同步过程中发生错误: {str(e)}", exc_info=True)
            return SyncResult(
                success=False,
                message=f"同步失败: {str(e)}",
                errors=[str(e)]
            )
        finally:
            # 清理本地仓库（如果配置了）
            try:
                if config.cleanup_local and temp_dir:
                    logger.debug(f"开始清理临时目录: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {str(e)}")
    
    def _prepare_local_repo(self, repo_path: str, config: GitSyncConfig, source_toolkit: GitBaseToolkit) -> str:
        """
        准备本地仓库（克隆或更新）。
        
        Args:
            repo_path: 本地仓库路径
            config: 同步配置
            source_toolkit: 源平台工具包
            
        Returns:
            str: 本地仓库路径，如果失败则返回空字符串
        """
        try:
            # 确保目标目录存在
            os.makedirs(repo_path, exist_ok=True)
            
            # 获取克隆URL
            git_url = source_toolkit.get_clone_url(config.source_repo, use_token=True)
            
            # Git仓库处理
            git_dir = os.path.join(repo_path, '.git')
            if os.path.exists(git_dir):
                # 更新现有仓库
                try:
                    # 使用安全的方式执行git fetch
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'fetch', '--all', '--tags'],
                        cwd=repo_path,
                        check=True,
                        capture_output=True
                    )
                except Exception as e:
                    logger.error(f"Git fetch失败: {str(e)}")
                    return ""
                
                # 确定要同步的分支
                branches = config.sync_branches if isinstance(config.sync_branches, list) else [config.sync_branches]
                
                for branch in branches:
                    try:
                        # 切换到指定分支并重置，使用_execute_with_retry处理编码问题
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'checkout', branch], 
                            cwd=repo_path, 
                            check=True, 
                            capture_output=True
                        )
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'reset', '--hard', f'origin/{branch}'], 
                            cwd=repo_path, 
                            check=True, 
                            capture_output=True
                        )
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"切换分支 {branch} 失败: {e.stderr}")
            else:
                # 克隆新仓库
                clone_cmd = ['git', 'clone']
                if config.shallow_clone and not config.incremental_sync:
                    clone_cmd.extend(['--depth', '1'])
                
                # 如果是增量同步，克隆所有分支
                if config.incremental_sync:
                    clone_cmd.append('--mirror')
                else:
                    clone_cmd.extend([git_url, repo_path])
                
                try:
                    # 使用重试机制执行克隆
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=clone_cmd,
                        check=True,
                        capture_output=True
                    )
                    
                    # 如果是--mirror模式，需要转换为普通仓库
                    if config.incremental_sync:
                        # 重新初始化非裸仓库
                        with open(os.path.join(repo_path, '.git', 'config'), 'r') as f:
                            config_content = f.read()
                        
                        # 移除bare设置
                        config_content = config_content.replace('bare = true', 'bare = false')
                        
                        with open(os.path.join(repo_path, '.git', 'config'), 'w') as f:
                            f.write(config_content)
                        
                        # 检出工作区
                        branches = config.sync_branches if isinstance(config.sync_branches, list) else [config.sync_branches]
                        for branch in branches:
                            try:
                                # 使用_execute_with_retry来处理编码问题
                                self._execute_with_retry(
                                    func=subprocess.run,
                                    cmd=['git', 'checkout', branch],
                                    cwd=repo_path,
                                    check=True,
                                    capture_output=True
                                )
                            except Exception as e:
                                logger.warning(f"检出分支 {branch} 失败: {str(e)}")
                                continue
                except Exception as e:
                    logger.error(f"Git克隆失败: {str(e)}")
                    return ""
            
            return repo_path
            
        except Exception as e:
            logger.error(f"准备本地仓库时发生错误: {str(e)}")
            return ""
    
    def _sync_to_git_platform(
        self,
        local_repo: str,
        target_platform: GitPlatformType,
        target_repo: str,
        target_credentials: Dict[str, Any],
        config: GitSyncConfig,
        target_toolkit: GitBaseToolkit
    ) -> List[str]:
        """
        同步到Git平台（GitHub、Gitee、GitLab）。
        
        Args:
            local_repo: 本地仓库路径
            target_platform: 目标平台类型
            target_repo: 目标仓库
            target_credentials: 目标平台凭证
            config: 同步配置
            target_toolkit: 目标平台工具包
            
        Returns:
            List[str]: 同步的变更列表
        """
        changes = []
        platform_info = f"{target_platform.value}:{target_repo}"
        logger.info(f"开始同步到 {platform_info}")
        
        # 获取目标仓库克隆URL
        try:
            target_url = target_toolkit.get_clone_url(target_repo, use_token=True)
            logger.debug(f"目标仓库URL: {target_url.replace(target_credentials.get('access_token', ''), '***')}")
        except Exception as e:
            logger.error(f"获取目标仓库URL失败: {str(e)}")
            return changes
        
        # 添加远程仓库
        remote_name = f"target_{target_platform.value}_{target_repo.replace('/', '_')}"
        logger.debug(f"使用远程名称: {remote_name}")
        
        # 先尝试移除已存在的远程仓库（忽略错误）
        try:
            self._execute_with_retry(
                func=subprocess.run,
                cmd=['git', 'remote', 'remove', remote_name],
                cwd=local_repo,
                check=False,
                capture_output=True
            )
            logger.debug(f"已移除旧的远程仓库 {remote_name}")
        except Exception as e:
            logger.debug(f"移除远程仓库失败（可能不存在）: {str(e)}")
    
        # 添加新的远程仓库
        try:
            self._execute_with_retry(
                func=subprocess.run,
                cmd=['git', 'remote', 'add', remote_name, target_url],
                cwd=local_repo,
                check=True,
                capture_output=True
            )
            logger.debug(f"已添加远程仓库 {remote_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"添加远程仓库失败: {e.stderr}")
            return changes
        except Exception as e:
            logger.error(f"添加远程仓库时发生未知错误: {str(e)}")
            return changes
        
        # 获取历史同步记录键
        history_key = platform_info
        last_sync_commit = self._sync_history.get(history_key, {}).get('last_commit')
        logger.debug(f"历史同步记录: {last_sync_commit if last_sync_commit else '无'}")
        
        # 确定要同步的分支
        branches = config.sync_branches if isinstance(config.sync_branches, list) else [config.sync_branches]
        logger.info(f"准备同步分支: {', '.join(branches)}")
        
        # 先执行fetch操作，获取远程仓库的最新状态
        try:
            self._execute_with_retry(
                func=subprocess.run,
                cmd=['git', 'fetch', remote_name],
                cwd=local_repo,
                check=True,
                capture_output=True
            )
            logger.debug(f"已获取远程仓库 {remote_name} 的所有引用")
        except subprocess.CalledProcessError as e:
            logger.warning(f"获取远程仓库失败: {e.stderr}，将继续尝试同步个别分支")
        except Exception as e:
            logger.warning(f"获取远程仓库时发生错误: {str(e)}，将继续尝试同步个别分支")
        
        # 同步每个分支
        for branch in branches:
            try:
                # 检查分支是否存在
                result = self._execute_with_retry(
                    func=subprocess.run,
                    cmd=['git', 'show-ref', f'refs/heads/{branch}'],
                    cwd=local_repo,
                    capture_output=True
                )
                
                if result.returncode != 0:
                    logger.warning(f"分支 {branch} 不存在，跳过同步")
                    continue
                
                # 获取当前分支的最新提交
                result = self._execute_with_retry(
                    func=subprocess.run,
                    cmd=['git', 'rev-parse', branch],
                    cwd=local_repo,
                    check=True,
                    capture_output=True
                )
                current_commit = result.stdout.strip()
                logger.debug(f"本地分支 {branch} 的最新提交: {current_commit}")
                
                # 检查远程分支是否存在
                remote_branch_exists = False
                try:
                    result = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'show-ref', f'refs/remotes/{remote_name}/{branch}'],
                        cwd=local_repo,
                        capture_output=True
                    )
                    remote_branch_exists = result.returncode == 0
                    
                    if remote_branch_exists:
                        result = self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'rev-parse', f'refs/remotes/{remote_name}/{branch}'],
                            cwd=local_repo,
                            check=True,
                            capture_output=True
                        )
                        remote_commit = result.stdout.strip()
                        logger.debug(f"远程分支 {branch} 的最新提交: {remote_commit}")
                    else:
                        logger.debug(f"远程分支 {branch} 不存在")
                except Exception as e:
                    logger.warning(f"检查远程分支 {branch} 状态失败: {str(e)}")
                
                # 检查是否存在冲突（只有当远程分支存在时）
                conflict_exists = False
                if remote_branch_exists:
                    try:
                        # 更准确的冲突检测：检查提交历史关系
                        result = self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'merge-base', '--is-ancestor', f'refs/remotes/{remote_name}/{branch}', branch],
                            cwd=local_repo,
                            check=False,
                            capture_output=True
                        )
                        # 如果本地分支是远程分支的祖先，没有冲突
                        if result.returncode != 0:
                            # 检查远程分支是否是本地分支的祖先
                            result = self._execute_with_retry(
                                func=subprocess.run,
                                cmd=['git', 'merge-base', '--is-ancestor', branch, f'refs/remotes/{remote_name}/{branch}'],
                                cwd=local_repo,
                                check=False,
                                capture_output=True
                            )
                            # 如果都不是对方的祖先，则存在冲突
                            if result.returncode != 0:
                                conflict_exists = True
                                logger.warning(f"检测到分支 {branch} 的冲突，将应用冲突解决策略")
                    except Exception as e:
                        logger.warning(f"检查冲突时发生错误: {str(e)}")
                
                # 如果存在冲突，应用冲突解决策略
                if conflict_exists:
                    conflict_strategy = config.conflict_resolution
                    if isinstance(conflict_strategy, str):
                        conflict_strategy = ConflictResolutionStrategy(conflict_strategy)
                    
                    conflict_resolved = self._resolve_conflict(
                        local_repo, remote_name, branch, conflict_strategy
                    )
                    
                    if not conflict_resolved:
                        errors_msg = f"无法解决分支 {branch} 的冲突"
                        logger.error(errors_msg)
                        changes.append(f"警告: {errors_msg}")
                        continue
                
                # 准备推送命令
                if config.incremental_sync and last_sync_commit and last_sync_commit != current_commit:
                    # 只推送自上次同步以来的变更
                    push_cmd = ['git', 'push', remote_name, f'{last_sync_commit}..{branch}:{branch}']
                    if config.force_push:
                        push_cmd.append('--force-with-lease')  # 更安全的强制推送
                    logger.debug(f"执行增量推送: {last_sync_commit[:7]}..{current_commit[:7]} 到 {branch}")
                else:
                    # 全量同步
                    push_cmd = ['git', 'push', remote_name, f'{branch}:{branch}']
                    if config.force_push:
                        push_cmd.append('--force')
                    logger.debug(f"执行推送: {branch}")
                
                # 执行推送
                try:
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=push_cmd,
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    
                    # 更新同步历史
                    self._sync_history[history_key] = {
                        'last_commit': current_commit,
                        'last_sync': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'synced_branch': branch
                    }
                    
                    sync_msg = f"已同步分支 {branch} 到 {platform_info}"
                    logger.info(sync_msg)
                    changes.append(sync_msg)
                except subprocess.CalledProcessError as e:
                    error_msg = f"同步分支 {branch} 失败: {e.stderr}"
                    logger.error(error_msg)
                    # 如果是分支不存在的错误，可以尝试创建分支
                    if "not found" in e.stderr or "does not exist" in e.stderr:
                        try:
                            # 尝试推送分支（创建远程分支）
                            create_cmd = ['git', 'push', remote_name, f'{branch}:{branch}']
                            if config.force_push:
                                create_cmd.append('--force')
                            
                            self._execute_with_retry(
                                func=subprocess.run,
                                cmd=create_cmd,
                                cwd=local_repo,
                                check=True,
                                capture_output=True
                            )
                            create_msg = f"已创建并同步分支 {branch} 到 {platform_info}"
                            logger.info(create_msg)
                            changes.append(create_msg)
                            
                            # 更新同步历史
                            self._sync_history[history_key] = {
                                'last_commit': current_commit,
                                'last_sync': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'synced_branch': branch
                            }
                        except Exception as inner_e:
                            logger.error(f"创建分支 {branch} 失败: {str(inner_e)}")
                    # 检查是否是权限问题
                    elif "permission denied" in e.stderr.lower() or "unauthorized" in e.stderr.lower():
                        logger.error(f"权限错误: 检查目标平台的访问令牌是否有效")
                    else:
                        changes.append(f"错误: {error_msg}")
                except Exception as e:
                    logger.error(f"同步分支 {branch} 时发生未知错误: {str(e)}", exc_info=True)
                    changes.append(f"错误: 同步分支 {branch} 时发生未知错误")
            except Exception as e:
                logger.error(f"处理分支 {branch} 时发生错误: {str(e)}", exc_info=True)
        # 同步标签
        if config.sync_tags:
            try:
                # 获取本地标签列表
                result = self._execute_with_retry(
                    func=subprocess.run,
                    cmd=['git', 'tag'],
                    cwd=local_repo,
                    capture_output=True
                )
                local_tags = result.stdout.strip().split('\n') if result.stdout.strip() else []
                
                if local_tags:
                    # 推送所有标签
                    push_cmd = ['git', 'push', remote_name, '--tags']
                    if config.force_push:
                        push_cmd.append('--force')
                    
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=push_cmd,
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    tags_msg = f"已同步 {len(local_tags)} 个标签到 {platform_info}"
                    logger.info(tags_msg)
                    changes.append(tags_msg)
                else:
                    logger.debug(f"本地仓库没有标签，跳过标签同步")
            except subprocess.CalledProcessError as e:
                logger.error(f"同步标签失败: {e.stderr}")
            except Exception as e:
                logger.error(f"同步标签时发生未知错误: {str(e)}", exc_info=True)
        
        # 执行分支清理
        if config.sync_prune:
            try:
                # 清理远程已删除的分支
                result = self._execute_with_retry(
                    func=subprocess.run,
                    cmd=['git', 'remote', 'prune', remote_name, '--dry-run'],
                    cwd=local_repo,
                    check=False,
                    capture_output=True
                )
                
                # 检查是否有需要清理的分支
                if result.stdout and " pruning " in result.stdout:
                    # 实际执行清理
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'remote', 'prune', remote_name],
                        cwd=local_repo,
                        check=False,
                        capture_output=True
                    )
                    prune_msg = f"已清理远程已删除的分支和标签"
                    logger.info(prune_msg)
                    changes.append(prune_msg)
                else:
                    logger.debug(f"没有需要清理的远程分支")
            except Exception as e:
                logger.warning(f"清理远程已删除分支时发生错误: {str(e)}")
        
        logger.info(f"完成同步到 {platform_info}")
        return changes
    
    def simple_sync_repositories(
        self,
        source_platform: str,
        source_repo: str,
        target_configs: List[Dict[str, Any]],
        source_credentials: Optional[Dict[str, str]] = None,
        sync_branches: Union[str, List[str]] = "main",
        sync_tags: bool = True,
        shallow_clone: bool = True,
        local_repo_path: Optional[str] = None,
        conflict_resolution: Union[str, ConflictResolutionStrategy] = ConflictResolutionStrategy.SOURCE_WINS,
        force_push: bool = True
    ) -> SyncResult:
        """
        提供与原RepoSyncToolkit类似的简化同步接口，用于一次性同步操作。
        
        此方法将创建临时配置，执行同步，然后清理配置，适合不需要保存配置的简单同步场景。
        
        Args:
            source_platform: 源平台类型 (github, gitee, gitlab)
            source_repo: 源仓库信息 (格式: owner/repo)
            target_configs: 目标仓库配置列表，每个配置包含platform和repo字段
            source_credentials: 源平台认证信息
            sync_branches: 需要同步的分支
            sync_tags: 是否同步标签
            shallow_clone: 是否使用浅克隆
            local_repo_path: 本地仓库路径
            conflict_resolution: 冲突解决策略
            force_push: 是否强制推送
            
        Returns:
            SyncResult: 同步结果
        """
        # 创建临时配置
        config_id = self.create_sync_config(
            source_platform=source_platform,
            source_repo=source_repo,
            target_configs=target_configs,
            source_credentials=source_credentials,
            sync_branches=sync_branches,
            sync_tags=sync_tags,
            shallow_clone=shallow_clone,
            local_repo_path=local_repo_path,
            conflict_resolution=conflict_resolution,
            force_push=force_push,
            incremental_sync=False  # 简化版使用全量同步
        )
        
        try:
            # 执行同步
            result = self.sync_repositories(config_id)
            return result
        finally:
            # 清理临时配置
            self.remove_sync_config(config_id)

    def get_tools(self) -> List[FunctionTool]:
        """
        获取工具包中的所有工具。
        
        Returns:
            List[FunctionTool]: 工具列表
        """
        return [
            FunctionTool(
                func=self.create_sync_config,
                name="create_git_sync_config",
                description="创建一个新的Git仓库同步配置",
            ),
            FunctionTool(
                func=self.sync_repositories,
                name="sync_git_repositories",
                description="执行Git仓库同步操作",
            ),
            FunctionTool(
                func=self.remove_sync_config,
                name="remove_git_sync_config",
                description="移除指定的同步配置",
            ),
            FunctionTool(
                func=self.get_config_list,
                name="get_git_sync_configs",
                description="获取所有Git同步配置列表",
            ),
            FunctionTool(
                func=self.get_sync_history,
                name="get_git_sync_history",
                description="获取Git同步历史记录",
            ),
            FunctionTool(
                func=self.clear_sync_history,
                name="clear_git_sync_history",
                description="清除Git同步历史记录",
            ),
            FunctionTool(
                func=self.save_configs,
                name="save_git_sync_configs",
                description="保存Git同步配置到文件",
            ),
            FunctionTool(
                func=self.simple_sync_repositories,
                name="simple_sync_git_repositories",
                description="使用简化接口执行Git仓库同步操作",
            ),
        ]
    
    def _resolve_conflict(
        self,
        local_repo: str,
        remote_name: str,
        branch: str,
        strategy: ConflictResolutionStrategy
    ) -> bool:
        """
        根据指定的策略解决Git冲突。
        
        Args:
            local_repo: 本地仓库路径
            remote_name: 远程仓库名称
            branch: 分支名称
            strategy: 冲突解决策略
            
        Returns:
            bool: 是否成功解决冲突
        """
        conflict_info = f"{remote_name}/{branch}"
        logger.info(f"开始解决冲突: {conflict_info}, 策略: {strategy.name}")
        
        try:
            if strategy == ConflictResolutionStrategy.SOURCE_WINS:
                # 源仓库优先 - 直接使用本地分支强制推送
                logger.info(f"应用 SOURCE_WINS 策略: 源仓库变更优先")
                # 这里不直接推送，而是让上层函数处理推送逻辑
                return True
                
            elif strategy == ConflictResolutionStrategy.TARGET_WINS:
                # 目标仓库优先 - 使用远程分支覆盖本地分支
                logger.info(f"应用 TARGET_WINS 策略: 目标仓库变更优先")
                
                # 先确认远程分支存在
                try:
                    result = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'show-ref', f'refs/remotes/{remote_name}/{branch}'],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    logger.debug(f"确认远程分支 {conflict_info} 存在")
                except Exception as e:
                    logger.error(f"远程分支 {conflict_info} 不存在: {str(e)}")
                    return False
                
                # 更安全的实现：不直接检出远程分支，而是将远程分支合并到一个临时分支
                try:
                    # 创建临时分支名称
                    temp_branch = f"temp_resolve_{int(time.time())}"
                    
                    # 备份当前分支
                    current_branch = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    ).stdout.strip()
                    
                    # 切换到远程分支
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'checkout', f'refs/remotes/{remote_name}/{branch}', '-b', temp_branch],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    
                    # 强制推送到远程分支
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'push', remote_name, f'{temp_branch}:{branch}', '--force'],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    logger.info(f"已应用 TARGET_WINS 策略，使用远程分支覆盖本地变更")
                    
                    # 切回原始分支
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'checkout', current_branch],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    
                    # 删除临时分支
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'branch', '-D', temp_branch],
                        cwd=local_repo,
                        check=False,
                        capture_output=True
                    )
                    
                    return True
                except Exception as e:
                    logger.error(f"执行 TARGET_WINS 策略失败: {str(e)}")
                    # 确保切回原始分支
                    try:
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'checkout', branch],
                            cwd=local_repo,
                            check=True,
                            capture_output=True
                        )
                    except Exception:
                        pass
                    return False
                
            elif strategy == ConflictResolutionStrategy.MERGE:
                # 尝试自动合并
                logger.info(f"应用 MERGE 策略: 尝试自动合并变更")
                
                # 先检查当前工作区是否干净
                try:
                    status_result = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'status', '--porcelain'],
                        cwd=local_repo,
                        check=False,
                        capture_output=True
                    )
                    
                    if status_result.stdout.strip():
                        logger.warning(f"工作区不干净，先暂存更改")
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'stash', 'push', '-m', 'conflict_resolution_temp_stash'],
                            cwd=local_repo,
                            check=False,
                            capture_output=True
                        )
                        need_pop_stash = True
                    else:
                        need_pop_stash = False
                    
                    # 切换到正确的分支
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'checkout', branch],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    
                    # 尝试合并远程分支到本地分支
                    merge_result = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'merge', f'refs/remotes/{remote_name}/{branch}', '--no-edit'],
                        cwd=local_repo,
                        check=False,
                        capture_output=True
                    )
                    
                    if merge_result.returncode == 0:
                        logger.info(f"自动合并成功")
                        
                        # 如果有暂存的更改，尝试恢复
                        if need_pop_stash:
                            try:
                                self._execute_with_retry(
                                    func=subprocess.run,
                                    cmd=['git', 'stash', 'pop'],
                                    cwd=local_repo,
                                    check=False,
                                    capture_output=True
                                )
                            except Exception as pop_e:
                                logger.warning(f"恢复暂存的更改失败: {str(pop_e)}")
                        
                        return True
                    else:
                        # 合并失败，回滚
                        logger.warning(f"自动合并失败，返回码: {merge_result.returncode}，输出: {merge_result.stdout}\n{merge_result.stderr}")
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'merge', '--abort'],
                            cwd=local_repo,
                            check=False,
                            capture_output=True
                        )
                        
                        # 如果有暂存的更改，尝试恢复
                        if need_pop_stash:
                            try:
                                self._execute_with_retry(
                                    func=subprocess.run,
                                    cmd=['git', 'stash', 'pop'],
                                    cwd=local_repo,
                                    check=False,
                                    capture_output=True
                                )
                            except Exception as pop_e:
                                logger.warning(f"恢复暂存的更改失败: {str(pop_e)}")
                        
                        logger.warning(f"自动合并失败，默认使用 SOURCE_WINS 策略")
                        # 回退到源仓库优先策略
                        return True
                except KeyboardInterrupt:
                    logger.error("用户中断合并操作")
                    # 尝试中止可能的合并状态
                    try:
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'merge', '--abort'],
                            cwd=local_repo,
                            check=False,
                            capture_output=True
                        )
                    except Exception:
                        pass
                    return False
                except Exception as e:
                    logger.error(f"执行自动合并时发生错误: {str(e)}", exc_info=True)
                    # 尝试中止可能的合并状态
                    try:
                        self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'merge', '--abort'],
                            cwd=local_repo,
                            check=False,
                            capture_output=True
                        )
                    except Exception:
                        pass
                    return True
                    
            elif strategy == ConflictResolutionStrategy.TIMESTAMP_BASED:
                # 基于时间戳决定
                logger.info(f"应用 TIMESTAMP_BASED 策略: 基于提交时间决定")
                
                try:
                    # 获取本地分支最后提交时间
                    local_time_result = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'log', '-1', '--format=%ct', branch],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    )
                    local_time = local_time_result.stdout.strip()
                    local_human_time = self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'log', '-1', '--format=%Y-%m-%d %H:%M:%S', branch],
                        cwd=local_repo,
                        check=True,
                        capture_output=True
                    ).stdout.strip()
                    
                    # 获取远程分支最后提交时间
                    try:
                        remote_time_result = self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'log', '-1', '--format=%ct', f'{remote_name}/{branch}'],
                            cwd=local_repo,
                            check=True,
                            capture_output=True
                        )
                        remote_time = remote_time_result.stdout.strip()
                        remote_human_time = self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'log', '-1', '--format=%Y-%m-%d %H:%M:%S', f'{remote_name}/{branch}'],
                            cwd=local_repo,
                            check=True,
                            capture_output=True
                        ).stdout.strip()
                    except subprocess.CalledProcessError:
                        # 如果远程分支不存在，使用本地分支
                        logger.warning(f"远程分支 {conflict_info} 不存在，默认使用本地分支")
                        remote_time = '0'
                        remote_human_time = '不存在'
                    
                    # 比较时间戳
                    logger.debug(f"时间戳比较: 本地({local_human_time}) vs 远程({remote_human_time})")
                    if int(local_time) > int(remote_time):
                        logger.info(f"本地分支更新 ({local_human_time} > {remote_human_time})，使用本地变更")
                        return True
                    else:
                        logger.info(f"远程分支更新 ({remote_human_time} > {local_human_time})，使用远程变更")
                        
                        # 创建临时分支名称
                        temp_branch = f"temp_timestamp_{int(time.time())}"
                        
                        # 备份当前分支
                        current_branch = self._execute_with_retry(
                            func=subprocess.run,
                            cmd=['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                            cwd=local_repo,
                            check=True,
                            capture_output=True
                        ).stdout.strip()
                        
                        try:
                            # 切换到远程分支创建的临时分支
                            self._execute_with_retry(
                                func=subprocess.run,
                                cmd=['git', 'checkout', f'refs/remotes/{remote_name}/{branch}', '-b', temp_branch],
                                cwd=local_repo,
                                check=True,
                                capture_output=True
                            )
                            
                            # 强制推送到远程分支
                            self._execute_with_retry(
                                func=subprocess.run,
                                cmd=['git', 'push', remote_name, f'{temp_branch}:{branch}', '--force'],
                                cwd=local_repo,
                                check=True,
                                capture_output=True
                            )
                            
                            # 切回原始分支
                            self._execute_with_retry(
                                func=subprocess.run,
                                cmd=['git', 'checkout', current_branch],
                                cwd=local_repo,
                                check=True,
                                capture_output=True
                            )
                            
                            # 删除临时分支
                            self._execute_with_retry(
                                func=subprocess.run,
                                cmd=['git', 'branch', '-D', temp_branch],
                                cwd=local_repo,
                                check=False,
                                capture_output=True
                            )
                            
                            return True
                        except Exception as e:
                            logger.error(f"应用远程分支时发生错误: {str(e)}")
                            # 确保切回原始分支
                            try:
                                self._execute_with_retry(
                                    func=subprocess.run,
                                    cmd=['git', 'checkout', current_branch],
                                    cwd=local_repo,
                                    check=True,
                                    capture_output=True
                                )
                            except Exception:
                                pass
                            return False
                except Exception as e:
                    logger.error(f"执行 TIMESTAMP_BASED 策略时发生错误: {str(e)}")
                    return False
                    
            elif strategy == ConflictResolutionStrategy.ASK:
                # 询问用户（在自动化环境中默认使用SOURCE_WINS）
                logger.warning(f"ASK 策略在自动化环境中不可用，默认使用 SOURCE_WINS 策略")
                return True
                
            else:
                logger.error(f"未知的冲突解决策略: {strategy}")
                return False
                
        except KeyboardInterrupt:
            logger.error("用户中断冲突解决操作")
            return False
        except Exception as e:
            logger.error(f"解决冲突时发生错误: {str(e)}", exc_info=True)
            # 确保仓库处于干净状态
            try:
                # 检查是否处于合并状态
                if os.path.exists(os.path.join(local_repo, '.git', 'MERGE_HEAD')):
                    self._execute_with_retry(
                        func=subprocess.run,
                        cmd=['git', 'merge', '--abort'],
                        cwd=local_repo,
                        check=False,
                        capture_output=True
                    )
            except Exception:
                pass
            return False
        
        logger.info(f"冲突解决完成: {conflict_info}")