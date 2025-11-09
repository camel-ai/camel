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
版本控制系统相关类型定义

包含版本控制系统使用的所有枚举类型、数据类、异常类和强类型标识符。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Set, Tuple, Callable, Literal, Protocol
from datetime import datetime
import uuid


# 强类型标识符定义
@dataclass(frozen=True)
class RepoID:
    """仓库标识符"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RepoPath:
    """仓库路径"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CommitHash:
    """提交哈希值"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CommitSHA:
    """提交哈希值（别名）"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class IssueID:
    """问题/议题标识符"""
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PRID:
    """Pull Request/合并请求ID"""
    value: int

    def __str__(self) -> str:
        return str(self.value)


# 通用标识符别名
RepoIdentifier = Union[RepoID, RepoPath, str, int]
IssueIdentifier = Union[IssueID, int]
PRIdentifier = Union[PRID, int]


@dataclass(frozen=True)
class BranchName:
    """分支名称"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TagName:
    """标签名称"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class UserID:
    """用户标识符"""
    value: str

    def __str__(self) -> str:
        return self.value


# 数据类定义
@dataclass
class VersionControlConfig:
    """版本控制系统配置基础类"""
    # API请求的超时时间（秒）
    timeout: float = 30.0
    
    # API请求失败时的最大重试次数
    max_retries: int = 3
    
    # 重试间隔时间（秒）
    retry_delay: float = 1.0
    
    # 基础URL地址
    base_url: Optional[str] = None
    
    # 访问API所需的令牌
    access_token: Optional[str] = None
    
    # SSL验证选项
    verify_ssl: bool = True
    
    # 兼容旧版配置
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    
    def __post_init__(self):
        # 确保向后兼容，如果设置了旧版token字段，使用它的值
        if self.token is not None and self.access_token is None:
            self.access_token = self.token
        
        # 如果timeout是int类型，转换为float以匹配旧实现
        if isinstance(self.timeout, int):
            self.timeout = float(self.timeout)


# 异常类定义
class VersionControlError(Exception):
    """版本控制操作基础异常"""
    def __init__(self, message: str, error_code: Optional[int] = None, platform: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        self.platform = platform
        super().__init__(self.message)
    
    def __str__(self):
        platform_info = f"[{self.platform}] " if self.platform else ""
        code_info = f"(Code: {self.error_code}) " if self.error_code else ""
        return f"{platform_info}{code_info}{self.message}"


class AuthenticationError(VersionControlError):
    """认证失败异常"""
    pass


class RepositoryNotFoundError(VersionControlError):
    """仓库不存在异常"""
    pass


class RateLimitExceededError(VersionControlError):
    """速率限制超限异常"""
    
    def __init__(self, message: str, retry_after: Optional[float] = None, **kwargs):
        self.retry_after = retry_after  # 建议的重试等待时间（秒）
        super().__init__(message, **kwargs)


class PermissionDeniedError(VersionControlError):
    """权限不足异常"""
    pass


class ResourceNotFoundError(VersionControlError):
    """资源未找到异常"""
    pass


class OperationFailedError(VersionControlError):
    """操作失败异常"""
    pass


class VersionControlConnectionError(VersionControlError):
    """连接错误异常"""
    pass


# 同步结果类
class SyncResult:
    """同步操作的结果类"""
    
    def __init__(self,
                 success: bool,
                 message: str,
                 details: Optional[Dict[str, Any]] = None,
                 errors: Optional[List[Exception]] = None,
                 changes: Optional[List[str]] = None,
                 sync_time: Optional[float] = None,
                 sync_duration: Optional[float] = None):
        self.success = success
        self.message = message
        self.details = details or {}
        self.errors = errors or []
        self.changes = changes or []
        self.sync_time = sync_time
        self.sync_duration = sync_duration
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{status}: {self.message}"
    
    def add_error(self, error: Exception) -> None:
        """添加错误到结果中。"""
        self.errors.append(error)
        if self.success:
            self.success = False
    
    def to_dict(self) -> Dict[str, Any]:
        """将结果转换为字典格式。"""
        return {
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "errors": [str(e) for e in self.errors],
            "changes": self.changes,
            "sync_time": self.sync_time,
            "sync_duration": self.sync_duration
        }


# 枚举类型定义
class GitPlatformType(Enum):
    """Git托管平台类型枚举"""
    GITHUB = "github"
    GITEA = "gitea"
    GITEE = "gitee"
    GITLAB = "gitlab"
    SVN = "svn"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"
    GOGS = "gogs"
    OTHER = "other"


class RepositoryPlatformType(Enum):
    """仓库平台类型枚举"""
    GITHUB = "github"
    GITEE = "gitee"
    GITLAB = "gitlab"
    SVN = "svn"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"


class ConflictResolutionStrategy(Enum):
    """冲突解决策略枚举"""
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    TIMESTAMP_BASED = "timestamp_based"
    FAIL = "fail"
    MERGE = "merge"
    ASK = "ask"


class SyncDirection(Enum):
    """同步方向枚举"""
    GIT_TO_SVN = "git_to_svn"  # Git到SVN
    SVN_TO_GIT = "svn_to_git"  # SVN到Git
    BIDIRECTIONAL = "bidirectional"  # 双向同步


# 仓库同步配置类
@dataclass
class RepositorySyncConfig:
    """仓库同步配置数据类"""
    config_id: str
    source_platform: RepositoryPlatformType
    target_platform: RepositoryPlatformType
    source_repo: str
    target_repo: str
    source_branch: str = "main"
    target_branch: str = "main"
    source_credentials: Dict[str, str] = field(default_factory=dict)
    target_credentials: Dict[str, str] = field(default_factory=dict)
    sync_tags: bool = True
    sync_releases: bool = True
    sync_wiki: bool = False
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    conflict_resolution_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.SOURCE_WINS
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    enabled: bool = True
    
    # 扩展配置，支持高级Git同步功能
    incremental_sync: bool = True  # 是否使用增量同步
    force_push: bool = False  # 是否强制推送
    allow_recreate: bool = False  # 是否允许重新创建仓库
    source_base_url: Optional[str] = None  # 自定义API基础URL（如自托管GitLab）
    target_base_url: Optional[str] = None  # 自定义API基础URL（如自托管GitLab）
    source_namespace: Optional[str] = None  # 源仓库命名空间（所有者）
    target_namespace: Optional[str] = None  # 目标仓库命名空间（所有者）
    max_retries: int = 3  # 操作失败重试次数
    backoff_factor: float = 2.0  # 退避因子，用于计算重试间隔
    timeout_seconds: int = 300  # 同步操作超时时间
    local_repo_path: Optional[str] = None  # 本地仓库路径，用于重用或调试
    cleanup_local: bool = True  # 同步完成后是否清理本地仓库


@dataclass
class GitSyncConfig:
    """Git同步配置数据类"""
    source_platform: GitPlatformType
    source_repo: str  # 格式: owner/repo 或完整URL
    target_platform: GitPlatformType
    target_repo: str  # 格式: owner/repo 或完整URL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_base_url: Optional[str] = None  # 自定义API基础URL（如自托管GitLab）
    source_namespace: Optional[str] = None  # 源仓库命名空间（所有者）
    target_base_url: Optional[str] = None  # 自定义API基础URL（如自托管GitLab）
    target_namespace: Optional[str] = None  # 目标仓库命名空间（所有者）
    target_configs: List[Dict[str, Any]] = field(default_factory=list)
    source_credentials: Dict[str, str] = field(default_factory=dict)
    target_credentials: Dict[str, str] = field(default_factory=dict)
    sync_branches: Union[str, List[str], Literal["all"]] = "main"  # 要同步的分支
    sync_tags: bool = True  # 是否同步标签
    incremental_sync: bool = True  # 是否使用增量同步
    force_push: bool = False  # 是否强制推送（谨慎使用）
    allow_recreate: bool = False  # 是否允许重新创建仓库
    conflict_resolution: Union[str, ConflictResolutionStrategy] = ConflictResolutionStrategy.SOURCE_WINS  # 冲突解决策略
    sync_prune: bool = True  # 是否删除远程已删除的分支/标签
    shallow_clone: bool = True  # 是否使用浅克隆提高性能
    clone_depth: int = 100  # 浅克隆深度
    timeout_seconds: int = 300  # 同步操作超时时间
    local_repo_path: Optional[str] = None  # 本地仓库路径，如果为None则使用临时目录
    cleanup_local: bool = True  # 同步完成后是否清理本地仓库
    max_retries: int = 3  # 操作失败时的最大重试次数

    def __post_init__(self):
        # 处理冲突解决策略的字符串输入
        if isinstance(self.conflict_resolution, str):
            try:
                self.conflict_resolution = ConflictResolutionStrategy(self.conflict_resolution.lower())
            except ValueError:
                # 如果字符串无效，使用默认策略
                self.conflict_resolution = ConflictResolutionStrategy.SOURCE_WINS

    @property
    def has_valid_targets(self) -> bool:
        """检查是否有有效的目标配置"""
        return bool(self.target_repo) or bool(self.target_configs)


@dataclass
class UnifiedSyncConfig:
    """统一同步配置数据类"""
    git_repo: str  # Git仓库URL或路径
    svn_repo: str  # SVN仓库URL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    git_branch: str = "main"  # Git分支
    git_credentials: Dict[str, str] = field(default_factory=dict)  # Git认证信息
    svn_credentials: Dict[str, str] = field(default_factory=dict)  # SVN认证信息 (username/password)
    sync_direction: SyncDirection = SyncDirection.GIT_TO_SVN  # 同步方向
    sync_tags: bool = True  # 是否同步Git标签到SVN
    sync_branches: Union[str, List[str]] = "main"  # 要同步的分支
    exclude_patterns: List[str] = field(default_factory=list)  # 排除的文件模式
    include_patterns: List[str] = field(default_factory=list)  # 包含的文件模式
    conflict_resolution: Union[str, ConflictResolutionStrategy] = ConflictResolutionStrategy.SOURCE_WINS  # 冲突解决策略
    force_push: bool = False  # 是否强制推送（用于Git）
    allow_recreate: bool = False  # 是否允许重新创建仓库
    incremental_sync: bool = True  # 是否使用增量同步
    shallow_clone: bool = True  # 是否使用浅克隆提高性能
    clone_depth: int = 100  # 浅克隆深度
    timeout_seconds: int = 300  # 同步操作超时时间
    local_repo_path: Optional[str] = None  # 本地仓库路径，如果为None则使用临时目录
    cleanup_local: bool = True  # 同步完成后是否清理本地仓库
    max_retries: int = 3  # 操作失败时的最大重试次数

    def __post_init__(self):
        # 处理冲突解决策略的字符串输入
        if isinstance(self.conflict_resolution, str):
            try:
                self.conflict_resolution = ConflictResolutionStrategy(self.conflict_resolution.lower())
            except ValueError:
                self.conflict_resolution = ConflictResolutionStrategy.SOURCE_WINS
        
        # 处理同步方向的字符串输入
        if isinstance(self.sync_direction, str):
            try:
                self.sync_direction = SyncDirection(self.sync_direction.lower())
            except ValueError:
                self.sync_direction = SyncDirection.GIT_TO_SVN

    def validate(self) -> List[str]:
        """验证配置的有效性"""
        errors = []
        
        if not self.git_repo:
            errors.append("Git仓库URL不能为空")
        
        if not self.svn_repo:
            errors.append("SVN仓库URL不能为空")
        
        if not self.git_branch:
            errors.append("Git分支不能为空")
        
        if self.timeout_seconds <= 0:
            errors.append("超时时间必须大于0")
        
        if self.max_retries < 0:
            errors.append("重试次数不能为负数")
        
        if self.clone_depth < 1:
            errors.append("克隆深度必须大于等于1")
        
        return errors

    def to_repository_sync_config(self) -> Dict:
        """转换为RepositorySyncConfig格式"""
        if self.sync_direction == SyncDirection.GIT_TO_SVN:
            return {
                "config_id": self.id,
                "source_platform": RepositoryPlatformType.GITHUB,  # 默认为GitHub，实际使用时需要根据URL判断
                "target_platform": RepositoryPlatformType.SVN,
                "source_repo": self.git_repo,
                "target_repo": self.svn_repo,
                "source_branch": self.git_branch,
                "target_branch": "trunk",  # SVN默认为trunk
                "source_credentials": self.git_credentials,
                "target_credentials": self.svn_credentials,
                "sync_tags": self.sync_tags,
                "exclude_patterns": self.exclude_patterns,
                "include_patterns": self.include_patterns,
                "conflict_resolution_strategy": self.conflict_resolution,
                "incremental_sync": self.incremental_sync,
                "force_push": self.force_push,
                "allow_recreate": self.allow_recreate,
                "timeout_seconds": self.timeout_seconds,
                "local_repo_path": self.local_repo_path,
                "cleanup_local": self.cleanup_local,
                "max_retries": self.max_retries
            }
        elif self.sync_direction == SyncDirection.SVN_TO_GIT:
            return {
                "config_id": self.id,
                "source_platform": RepositoryPlatformType.SVN,
                "target_platform": RepositoryPlatformType.GITHUB,  # 默认为GitHub，实际使用时需要根据URL判断
                "source_repo": self.svn_repo,
                "target_repo": self.git_repo,
                "source_branch": "trunk",  # SVN默认为trunk
                "target_branch": self.git_branch,
                "source_credentials": self.svn_credentials,
                "target_credentials": self.git_credentials,
                "sync_tags": self.sync_tags,
                "exclude_patterns": self.exclude_patterns,
                "include_patterns": self.include_patterns,
                "conflict_resolution_strategy": self.conflict_resolution,
                "incremental_sync": self.incremental_sync,
                "force_push": self.force_push,
                "allow_recreate": self.allow_recreate,
                "timeout_seconds": self.timeout_seconds,
                "local_repo_path": self.local_repo_path,
                "cleanup_local": self.cleanup_local,
                "max_retries": self.max_retries
            }
        else:  # BIDIRECTIONAL
            return {
                "config_id": self.id,
                "source_platform": RepositoryPlatformType.GITHUB,  # 默认为GitHub，实际使用时需要根据URL判断
                "target_platform": RepositoryPlatformType.SVN,
                "source_repo": self.git_repo,
                "target_repo": self.svn_repo,
                "source_branch": self.git_branch,
                "target_branch": "trunk",  # SVN默认为trunk
                "source_credentials": self.git_credentials,
                "target_credentials": self.svn_credentials,
                "sync_tags": self.sync_tags,
                "exclude_patterns": self.exclude_patterns,
                "include_patterns": self.include_patterns,
                "conflict_resolution_strategy": self.conflict_resolution,
                "incremental_sync": self.incremental_sync,
                "force_push": self.force_push,
                "allow_recreate": self.allow_recreate,
                "timeout_seconds": self.timeout_seconds,
                "local_repo_path": self.local_repo_path,
                "cleanup_local": self.cleanup_local,
                "max_retries": self.max_retries,
                "bidirectional": True
            }