# GitSyncToolkit

GitSyncToolkit是一个强大的跨平台Git仓库同步工具包，支持在GitHub、Gitee、GitLab等不同Git平台之间进行代码同步。它提供了灵活的配置管理、冲突解决策略和同步历史记录功能，可以轻松实现代码的多平台备份和同步。

## 核心功能

- 支持跨平台同步（GitHub、Gitee、GitLab）
- 灵活的配置管理（创建、保存、删除同步配置）
- 多种冲突解决策略
- 增量同步和全量同步支持
- 同步历史记录追踪
- 分支和标签同步
- 安全的凭证管理（环境变量读取）

## 类定义

```python
class GitSyncToolkit(BaseToolkit):
    """
    Git仓库跨平台同步工具包
    
    用于在不同Git平台（GitHub、Gitee、GitLab）之间同步仓库，
    支持配置管理、冲突解决和同步历史记录。
    """
    
    def __init__(self, timeout: Optional[float] = None, config_path: Optional[str] = None):
        """
        初始化Git同步工具包
        
        Args:
            timeout: 操作超时时间（秒）
            config_path: 配置文件路径
        """
```

## 枚举类型

### GitPlatformType

```python
class GitPlatformType(str, Enum):
    """Git平台类型枚举"""
    GITHUB = "github"
    GITEE = "gitee"
    GITLAB = "gitlab"
```

### ConflictResolutionStrategy

```python
class ConflictResolutionStrategy(str, Enum):
    """冲突解决策略枚举"""
    SOURCE_WINS = "source_wins"  # 源仓库优先
    TARGET_WINS = "target_wins"  # 目标仓库优先
    MERGE = "merge"  # 尝试自动合并
    TIMESTAMP_BASED = "timestamp_based"  # 基于时间戳决定
    ASK = "ask"  # 询问用户（在自动化环境中默认使用SOURCE_WINS）
```

## 数据类

### GitSyncConfig

```python
@dataclass
class GitSyncConfig:
    """Git同步配置数据类"""
    source_platform: GitPlatformType  # 源平台类型
    source_repo: str  # 源仓库信息
    target_configs: List[Dict[str, Any]]  # 目标仓库配置列表
    source_credentials: Dict[str, Any] = field(default_factory=dict)  # 源平台凭证
    source_base_url: Optional[str] = None  # 源平台的自定义API基础URL
    source_namespace: Optional[str] = None  # 源仓库命名空间
    sync_branches: Union[str, List[str]] = "main"  # 需要同步的分支
    sync_tags: bool = True  # 是否同步标签
    incremental_sync: bool = False  # 是否使用增量同步
    force_push: bool = False  # 是否强制推送
    allow_recreate: bool = False  # 是否允许重新创建仓库
    conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.SOURCE_WINS  # 冲突解决策略
    sync_prune: bool = True  # 是否删除远程已删除的分支/标签
    shallow_clone: bool = True  # 是否使用浅克隆
    clone_depth: int = 100  # 克隆深度
    timeout_seconds: int = 300  # 同步操作超时时间
    local_repo_path: Optional[str] = None  # 本地仓库路径
    cleanup_local: bool = True  # 同步完成后是否清理本地仓库
    max_retries: int = 3  # 操作失败时的最大重试次数
```

### SyncResult

```python
@dataclass
class SyncResult:
    """同步结果数据类"""
    success: bool  # 是否成功
    message: str  # 结果消息
    changes: List[str] = field(default_factory=list)  # 变更列表
    errors: List[str] = field(default_factory=list)  # 错误列表
```

## 主要方法

### 创建同步配置

```python
def create_sync_config(
    self,
    source_platform: str,
    source_repo: str,
    target_configs: List[Dict[str, Any]],
    source_credentials: Optional[Dict[str, Any]] = None,
    source_base_url: Optional[str] = None,
    source_namespace: Optional[str] = None,
    sync_branches: Union[str, List[str]] = "main",
    sync_tags: bool = True,
    incremental_sync: bool = False,
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
    创建一个新的Git仓库同步配置
    
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
```

### 添加同步配置

```python
def add_sync_config(self, config: GitSyncConfig) -> str:
    """
    添加一个同步配置
    
    Args:
        config: 同步配置
        
    Returns:
        str: 配置ID
    """
```

### 执行同步

```python
def sync_repositories(self, config_id: str) -> SyncResult:
    """
    执行Git仓库同步操作
    
    Args:
        config_id: 配置ID
        
    Returns:
        SyncResult: 同步结果
    """
```

### 简化同步接口

```python
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
    提供与原RepoSyncToolkit类似的简化同步接口，用于一次性同步操作
    
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
```

### 配置管理

```python
def remove_sync_config(self, config_id: str) -> bool:
    """
    移除指定的同步配置
    
    Args:
        config_id: 配置ID
        
    Returns:
        bool: 是否成功移除
    """

def get_config_list(self) -> List[Dict[str, Any]]:
    """
    获取所有同步配置的列表
    
    Returns:
        List[Dict[str, Any]]: 配置列表
    """

def save_configs(self, config_path: str) -> None:
    """
    保存所有配置到文件
    
    Args:
        config_path: 配置文件路径
    """
```

### 同步历史管理

```python
def get_sync_history(self, target_key: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    获取同步历史记录
    
    Args:
        target_key: 可选的目标键，格式为 "platform:repo"
        
    Returns:
        Dict[str, Dict[str, str]]: 同步历史记录
    """

def clear_sync_history(self, target_key: Optional[str] = None) -> None:
    """
    清除同步历史记录
    
    Args:
        target_key: 可选的目标键，格式为 "platform:repo"
    """
```

### 获取工具列表

```python
def get_tools(self) -> List[FunctionTool]:
    """
    获取工具包中的所有工具
    
    Returns:
        List[FunctionTool]: 工具列表
    """
```

## 使用示例

```python
from camel.toolkits.git_sync_toolkit import GitSyncToolkit

# 初始化工具包
sync_toolkit = GitSyncToolkit()

# 创建同步配置
config_id = sync_toolkit.create_sync_config(
    source_platform="github",
    source_repo="owner/source-repo",
    target_configs=[
        {"platform": "gitee", "repo": "owner/target-repo"},
        {"platform": "gitlab", "repo": "owner/target-repo"}
    ],
    sync_branches=["main", "develop"],
    sync_tags=True,
    conflict_resolution="source_wins"
)

# 执行同步
result = sync_toolkit.sync_repositories(config_id)
print(f"同步{'成功' if result.success else '失败'}: {result.message}")

# 使用简化接口进行一次性同步
result = sync_toolkit.simple_sync_repositories(
    source_platform="github",
    source_repo="owner/another-repo",
    target_configs=[{"platform": "gitee", "repo": "owner/target-repo"}],
    sync_branches="main"
)
```

## 注意事项

1. 确保已设置正确的环境变量以访问各Git平台的API令牌：
   - GitHub: `GITHUB_ACCESS_TOKEN`
   - Gitee: `GITEE_ACCESS_TOKEN`
   - GitLab: `GITLAB_ACCESS_TOKEN`

2. 对于私有仓库，请确保提供的凭证具有适当的访问权限。

3. 在使用增量同步时，请注意正确设置冲突解决策略。

4. 强制推送可能会覆盖目标仓库中的更改，请谨慎使用。