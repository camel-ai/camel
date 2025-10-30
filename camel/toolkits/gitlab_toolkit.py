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

import logging
import os
import time
import yaml
import warnings
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Union, Any, Callable, TypeVar

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.git_base_toolkit import GitBaseToolkit
from camel.utils import MCPServer, dependencies_required

logger = logging.getLogger(__name__)

# NewType pattern for strong typing
T = TypeVar('T')

class NewType:
    """A simple implementation of NewType pattern for strong typing."""
    
    def __class_getitem__(cls, params):
        if not isinstance(params, tuple) or len(params) != 2:
            raise TypeError("NewType expects two parameters: name and type")
        name, base_type = params
        
        class TypedValue:
            def __init__(self, value):
                if not isinstance(value, base_type):
                    raise TypeError(f"Expected {base_type.__name__}, got {type(value).__name__}")
                self._value = value
            
            def __repr__(self):
                return f"{name}({self._value!r})"
            
            def __eq__(self, other):
                if isinstance(other, TypedValue):
                    return self._value == other._value
                return self._value == other
            
            def __hash__(self):
                return hash(self._value)
            
            @property
            def value(self):
                return self._value
        
        TypedValue.__name__ = name
        TypedValue.__qualname__ = f"{cls.__qualname__}[{name}, {base_type.__name__}]"
        return TypedValue

# Strongly typed identifiers
ProjectID = NewType['ProjectID', int]
ProjectPath = NewType['ProjectPath', str]
IssueIID = NewType['IssueIID', int]
MR_IID = NewType['MR_IID', int]
Namespace = NewType['Namespace', str]
InstanceName = NewType['InstanceName', str]

# Type aliases for backward compatibility and flexibility
ProjectIdentifier = Union[ProjectID, ProjectPath, str, int]
IssueIdentifier = Union[IssueIID, int]
MRIdentifier = Union[MR_IID, int]

import os
from dataclasses import dataclass, field
from typing import Optional
import re

@dataclass(frozen=True)
class GitLabInstanceConfig:
    """
    配置GitLab实例的连接参数。
    
    该数据类存储与GitLab实例交互所需的所有配置信息，支持官方GitLab.com和自托管实例。
    使用frozen=True确保配置一旦创建不可修改，提高安全性和一致性。
    """
    
    # GitLab实例的基础URL地址
    url: str = field(default="https://gitlab.com", metadata={"description": "GitLab实例的基础URL地址，默认为官方GitLab.com"})
    
    # 访问GitLab API的身份验证令牌
    token: str = field(default="", metadata={"description": "访问GitLab API所需的个人访问令牌或OAuth令牌"})
    
    # API请求的超时时间（秒）
    timeout: Optional[float] = field(default=None, metadata={"description": "API请求的超时时间（秒），None表示使用gitlab库默认值"})
    
    # API请求失败时的最大重试次数
    max_retries: int = field(default=3, metadata={"description": "API请求失败时的最大重试次数，用于处理临时性网络问题或限流"})
    
    # 重试间隔时间（秒）
    retry_delay: float = field(default=1.0, metadata={"description": "重试请求之间的延迟时间（秒），可减少重试风暴风险"})
    
    # SSL验证选项
    verify_ssl: bool = field(default=True, metadata={"description": "是否验证SSL证书，自托管实例可能需要设置为False"})
    
    def __post_init__(self) -> None:
        """
        初始化后的验证方法，确保配置参数的有效性。
        
        验证URL格式是否正确，可选择性地验证token是否提供。
        对于不可变数据类，使用object.__setattr__来修改字段值。
        """
        # 标准化URL，确保以http://或https://开头且不包含尾部斜杠
        if hasattr(self, 'url') and self.url:
            normalized_url = self._normalize_url(self.url)
            if normalized_url != self.url:
                object.__setattr__(self, 'url', normalized_url)
            
        # 验证URL格式
        if not self._is_valid_url(self.url):
            raise ValueError(f"Invalid GitLab URL format: {self.url}. Must start with http:// or https://")
    
    def _normalize_url(self, url: str) -> str:
        """标准化URL格式，移除尾部斜杠。"""
        return url.rstrip('/')
    
    def _is_valid_url(self, url: str) -> bool:
        """
        验证URL格式是否有效。
        
        使用正则表达式检查URL是否以http://或https://开头，
        并且包含有效的域名格式。
        """
        url_pattern = re.compile(r'^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z0-9.-]+)+(:\d+)?/?')
        return bool(url_pattern.match(url))
    
    def validate(self, require_token: bool = True) -> None:
        """
        全面验证配置的有效性。
        
        Args:
            require_token: 是否要求提供token。某些只读操作可能不需要token。
            
        Raises:
            ValueError: 如果配置无效，例如URL格式错误或缺少必需的token。
        """
        # 再次验证URL（确保即使绕过__post_init__也能验证）
        if not self._is_valid_url(self.url):
            raise ValueError(f"Invalid GitLab URL format: {self.url}")
        
        # 根据需要验证token
        if require_token and not self.token:
            raise ValueError("GitLab access token is required for this operation")
        
        # 验证其他数值参数
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        
        if self.retry_delay <= 0:
            raise ValueError("retry_delay must be positive")
        
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive if provided")
    
    @classmethod
    def from_environment(cls, prefix: str = "GITLAB_") -> 'GitLabInstanceConfig':
        """
        从环境变量加载GitLab实例配置。
        
        支持的环境变量（可通过prefix自定义前缀）：
        - {prefix}URL: GitLab实例URL
        - {prefix}TOKEN: GitLab访问令牌
        - {prefix}TIMEOUT: 请求超时时间（浮点数）
        - {prefix}MAX_RETRIES: 最大重试次数（整数）
        - {prefix}RETRY_DELAY: 重试延迟时间（浮点数）
        - {prefix}VERIFY_SSL: 是否验证SSL证书（布尔值或字符串"true"/"false"）
        
        Args:
            prefix: 环境变量前缀，默认为"GITLAB_"
            
        Returns:
            基于环境变量创建的GitLabInstanceConfig实例
            
        Example:
            # 假设环境变量中有GITLAB_URL和GITLAB_TOKEN
            config = GitLabInstanceConfig.from_environment()
        """
        # 构建环境变量键名
        url_key = f"{prefix}URL"
        token_key = f"{prefix}TOKEN"
        timeout_key = f"{prefix}TIMEOUT"
        max_retries_key = f"{prefix}MAX_RETRIES"
        retry_delay_key = f"{prefix}RETRY_DELAY"
        verify_ssl_key = f"{prefix}VERIFY_SSL"
        
        # 从环境变量获取值，使用默认值处理缺失的环境变量
        url = os.environ.get(url_key, "https://gitlab.com")
        token = os.environ.get(token_key, "")
        
        # 转换数值类型，处理缺失或无效值
        timeout = None
        if timeout_key in os.environ:
            try:
                timeout = float(os.environ[timeout_key])
            except ValueError:
                logger.warning(f"Invalid value for {timeout_key}, using default")
        
        max_retries = 3
        if max_retries_key in os.environ:
            try:
                max_retries = int(os.environ[max_retries_key])
            except ValueError:
                logger.warning(f"Invalid value for {max_retries_key}, using default")
        
        retry_delay = 1.0
        if retry_delay_key in os.environ:
            try:
                retry_delay = float(os.environ[retry_delay_key])
            except ValueError:
                logger.warning(f"Invalid value for {retry_delay_key}, using default")
        
        # 处理布尔值类型的SSL验证选项
        verify_ssl = True
        if verify_ssl_key in os.environ:
            verify_ssl_value = os.environ[verify_ssl_key].lower()
            verify_ssl = verify_ssl_value not in ("false", "0", "no", "n", "f")
        
        # 创建并返回配置实例
        return cls(
            url=url,
            token=token,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            verify_ssl=verify_ssl
        )

class GitLabInstanceManager:
    """A manager for multiple GitLab instances."""
    
    _instances: Dict[str, Any] = {}
    _configs: Dict[str, GitLabInstanceConfig] = {}
    _default_instance_name: str = "default"
    
    @classmethod
    @dependencies_required('gitlab')
    def register_instance(cls, name: str, config: GitLabInstanceConfig) -> None:
        """Register a new GitLab instance.
        
        Args:
            name: The name of the instance.
            config: The configuration for the instance.
        """
        import gitlab
        
        # 验证配置的有效性
        config.validate()
        
        # Create and store the GitLab instance
        gl = gitlab.Gitlab(
            url=config.url,
            private_token=config.token,
            timeout=config.timeout,
            ssl_verify=config.verify_ssl  # 使用新添加的SSL验证选项
        )
        
        # Test the connection
        try:
            gl.auth()
            cls._instances[name] = gl
            cls._configs[name] = config
            logger.info(f"Successfully registered GitLab instance: {name}")
        except Exception as e:
            logger.error(f"Failed to register GitLab instance {name}: {str(e)}")
            raise
    
    @classmethod
    def get_instance(cls, name: str = None) -> Any:
        """Get a registered GitLab instance.
        
        Args:
            name: The name of the instance. If None, use the default instance.
        
        Returns:
            The GitLab instance.
        
        Raises:
            KeyError: If the instance is not registered.
        """
        instance_name = name or cls._default_instance_name
        if instance_name not in cls._instances:
            raise KeyError(f"GitLab instance '{instance_name}' not registered")
        return cls._instances[instance_name]
    
    @classmethod
    def get_config(cls, name: str = None) -> GitLabInstanceConfig:
        """Get the configuration for a registered GitLab instance.
        
        Args:
            name: The name of the instance. If None, use the default instance.
        
        Returns:
            The configuration for the instance.
        
        Raises:
            KeyError: If the instance is not registered.
        """
        instance_name = name or cls._default_instance_name
        if instance_name not in cls._configs:
            raise KeyError(f"GitLab instance '{instance_name}' not registered")
        return cls._configs[instance_name]
    
    @classmethod
    def unregister_instance(cls, name: str) -> None:
        """Unregister a GitLab instance.
        
        Args:
            name: The name of the instance to unregister.
        """
        if name in cls._instances:
            del cls._instances[name]
            del cls._configs[name]
            logger.info(f"Unregistered GitLab instance: {name}")
    
    @classmethod
    def set_default_instance(cls, name: str) -> None:
        """Set the default GitLab instance.
        
        Args:
            name: The name of the instance to set as default.
        
        Raises:
            KeyError: If the instance is not registered.
        """
        if name not in cls._instances:
            raise KeyError(f"GitLab instance '{name}' not registered")
        cls._default_instance_name = name
        logger.info(f"Set default GitLab instance to: {name}")
    
    @classmethod
    def load_from_config_file(cls, config_path: str) -> None:
        """Load GitLab instances from a YAML configuration file.
        
        Args:
            config_path: The path to the YAML configuration file.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        instances = config_data.get('instances', {})
        for name, instance_config in instances.items():
            config = GitLabInstanceConfig(**instance_config)
            cls.register_instance(name, config)
        
        # Set default instance if specified
        if 'default_instance' in config_data:
            cls.set_default_instance(config_data['default_instance'])
    
    @classmethod
    def load_from_environment(cls) -> None:
        """Load GitLab instances from environment variables.
        
        Environment variables format:
        - GITLAB_INSTANCE_<NAME>_URL: The URL for the instance
        - GITLAB_INSTANCE_<NAME>_TOKEN: The token for the instance
        - GITLAB_INSTANCE_<NAME>_TIMEOUT: Optional timeout for the instance
        - GITLAB_DEFAULT_INSTANCE: Optional name of the default instance
        """
        # Load default instance name
        default_instance = os.environ.get('GITLAB_DEFAULT_INSTANCE', 'default')
        
        # Load instance configurations
        instances = {}
        for key, value in os.environ.items():
            if key.startswith('GITLAB_INSTANCE_') and key.endswith('_URL'):
                name = key[len('GITLAB_INSTANCE_'):-len('_URL')].lower()
                if name not in instances:
                    instances[name] = {'url': value}
                else:
                    instances[name]['url'] = value
            
            if key.startswith('GITLAB_INSTANCE_') and key.endswith('_TOKEN'):
                name = key[len('GITLAB_INSTANCE_'):-len('_TOKEN')].lower()
                if name not in instances:
                    instances[name] = {'token': value}
                else:
                    instances[name]['token'] = value
            
            if key.startswith('GITLAB_INSTANCE_') and key.endswith('_TIMEOUT'):
                name = key[len('GITLAB_INSTANCE_'):-len('_TIMEOUT')].lower()
                try:
                    timeout = float(value)
                    if name not in instances:
                        instances[name] = {'timeout': timeout}
                    else:
                        instances[name]['timeout'] = timeout
                except ValueError:
                    logger.warning(f"Invalid timeout value for instance {name}: {value}")
        
        # Register instances
        for name, config_data in instances.items():
            if 'token' in config_data:  # Only register if we have a token
                config = GitLabInstanceConfig(**config_data)
                try:
                    cls.register_instance(name, config)
                except Exception as e:
                    logger.error(f"Failed to register instance {name} from environment: {e}")
        
        # Set default instance
        if default_instance in cls._instances:
            cls.set_default_instance(default_instance)
    
    @classmethod
    def with_rate_limit_retry(cls, instance_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with rate limit retry logic.
        
        Args:
            instance_name: The name of the GitLab instance.
            func: The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.
        
        Returns:
            The result of the function.
        
        Raises:
            Exception: If the function fails after retries.
        """
        import gitlab
        
        config = cls.get_config(instance_name)
        retries = 0
        
        while retries <= config.max_retries:
            try:
                return func(*args, **kwargs)
            except gitlab.exceptions.GitlabRateLimitError as e:
                retries += 1
                if retries > config.max_retries:
                    raise
                
                # Calculate backoff time with jitter
                backoff_time = config.retry_delay * (2 ** (retries - 1)) * (0.5 + 0.5 * (retries % 2))
                logger.warning(f"Rate limit exceeded for instance {instance_name}. Retrying in {backoff_time:.2f}s...")
                time.sleep(backoff_time)
            except Exception as e:
                # For other errors, check if they might be related to rate limiting
                if "rate limit" in str(e).lower() or "quota exceeded" in str(e).lower():
                    retries += 1
                    if retries > config.max_retries:
                        raise
                    
                    backoff_time = config.retry_delay * (2 ** (retries - 1))
                    logger.warning(f"Possible rate limit error for instance {instance_name}. Retrying in {backoff_time:.2f}s...")
                    time.sleep(backoff_time)
                else:
                    raise


@MCPServer()
class GitLabToolkit(GitBaseToolkit):
    r"""A class representing a toolkit for interacting with GitLab
    repositories.

    This class provides methods for retrieving open issues, retrieving
        specific issues, and creating merge requests in a GitLab repository.

    Args:
        access_token (str, optional): The access token to authenticate with
            GitLab. If not provided, it will be obtained using the
            `get_gitlab_access_token` method.
        instance_name (str, optional): The name of the GitLab instance to use.
            Defaults to 'default'.
        namespace (str, optional): The default namespace to use for operations.
            Defaults to None.
        timeout (float, optional): The timeout for API requests.
            Defaults to None.
    """
    
    PLATFORM_NAME = "gitlab"

    @dependencies_required('gitlab')
    def __init__(
        self,
        access_token: Optional[str] = None,
        instance_name: str = 'default',
        namespace: Optional[str] = None,
        timeout: Optional[float] = None,
        verify_ssl: bool = True,
    ) -> None:
        r"""Initializes a new instance of the GitLabToolkit class.

        Args:
            access_token (str, optional): The access token to authenticate
                with GitLab. If not provided, it will be obtained using the
                `get_gitlab_access_token` method.
            instance_name (str, optional): The name of the GitLab instance to use.
                Defaults to 'default'.
            namespace (str, optional): The default namespace to use for operations.
                Defaults to None.
            timeout (float, optional): The timeout for API requests.
                Defaults to None.
            verify_ssl (bool, optional): Whether to verify SSL certificates.
                Defaults to True.
        """
        super().__init__(timeout=timeout)
        self.instance_name = instance_name
        self.namespace = namespace
        
        # Register a default instance if access_token is provided
        if access_token is not None:
            config = GitLabInstanceConfig(
                url="https://gitlab.com",
                token=access_token,
                timeout=timeout,
                verify_ssl=verify_ssl
            )
            # Try to register the instance if it doesn't exist
            try:
                GitLabInstanceManager.get_instance(instance_name)
            except KeyError:
                GitLabInstanceManager.register_instance(instance_name, config)
        elif instance_name == 'default':
            # Try to load from environment if default instance is not registered
            try:
                GitLabInstanceManager.get_instance('default')
            except KeyError:
                GitLabInstanceManager.load_from_environment()

    def _initialize_client(self):
        """初始化GitLab客户端，实现GitBaseToolkit的抽象方法"""
        # 客户端初始化在__init__方法中已经处理，但为了符合抽象接口，这里做一些验证
        try:
            # 确保实例管理器中有对应的实例
            GitLabInstanceManager.get_instance(self.instance_name)
        except KeyError:
            # 如果实例不存在，尝试从环境变量加载
            GitLabInstanceManager.load_from_environment()
    
    def get_repository(self, repo_name: str) -> Any:
        """获取GitLab仓库对象，实现GitBaseToolkit的抽象方法"""
        gitlab_instance = GitLabInstanceManager.get_instance(self.instance_name)
        owner, name = self._parse_repo_name(repo_name)
        
        # 构建完整的项目路径
        full_path = f"{owner}/{name}"
        
        try:
            return gitlab_instance.projects.get(full_path)
        except Exception as e:
            raise Exception(f"获取GitLab仓库失败: {str(e)}")
    
    def create_repository(self, repo_name: str, **kwargs) -> dict:
        """在GitLab上创建新仓库，实现GitBaseToolkit的抽象方法"""
        gitlab_instance = GitLabInstanceManager.get_instance(self.instance_name)
        owner, name = self._parse_repo_name(repo_name)
        
        # 设置默认参数
        description = kwargs.get('description', '')
        private = kwargs.get('private', True)
        auto_init = kwargs.get('auto_init', True)
        
        try:
            # 如果指定了namespace(owner)，使用它
            if owner:
                # 获取namespace对象
                try:
                    namespace = gitlab_instance.namespaces.get(owner)
                    # 在指定namespace下创建项目
                    project = gitlab_instance.projects.create({
                        'name': name,
                        'namespace_id': namespace.id,
                        'description': description,
                        'visibility': 'private' if private else 'public',
                        'auto_init': auto_init
                    })
                except Exception:
                    # 如果namespace不存在，尝试在用户名下创建
                    project = gitlab_instance.projects.create({
                        'name': name,
                        'description': description,
                        'visibility': 'private' if private else 'public',
                        'auto_init': auto_init
                    })
            else:
                # 在当前用户下创建项目
                project = gitlab_instance.projects.create({
                    'name': name,
                    'description': description,
                    'visibility': 'private' if private else 'public',
                    'auto_init': auto_init
                })
            
            return {
                'name': project.path_with_namespace,
                'url': project.web_url,
                'clone_url': project.ssh_url_to_repo if project.ssh_url_to_repo else project.http_url_to_repo
            }
        except Exception as e:
            raise Exception(f"创建GitLab仓库失败: {str(e)}")
    
    def repository_exists(self, repo_name: str) -> bool:
        """检查GitLab仓库是否存在，实现GitBaseToolkit的抽象方法"""
        gitlab_instance = GitLabInstanceManager.get_instance(self.instance_name)
        owner, name = self._parse_repo_name(repo_name)
        full_path = f"{owner}/{name}"
        
        try:
            gitlab_instance.projects.get(full_path)
            return True
        except Exception:
            return False
    
    def get_clone_url(self, repo_name: str, use_token: bool = True) -> str:
        """获取GitLab仓库的克隆URL，实现GitBaseToolkit的抽象方法"""
        gitlab_instance = GitLabInstanceManager.get_instance(self.instance_name)
        
        try:
            # 获取仓库信息
            project = self.get_repository(repo_name)
            
            if use_token:
                # 构建带token的HTTP URL
                # 从配置中获取URL和token
                config = GitLabInstanceManager.get_config(self.instance_name)
                base_url = config.url.rstrip('/')
                token = config.token
                
                # 构建带token的HTTP URL
                owner, name = self._parse_repo_name(repo_name)
                return f"{base_url}/api/v4/projects/{owner}%2F{name}/repository/archive.tar.gz?private_token={token}"
            else:
                # 返回SSH URL或HTTP URL
                return project.ssh_url_to_repo if project.ssh_url_to_repo else project.http_url_to_repo
        except Exception as e:
            raise Exception(f"获取GitLab仓库克隆URL失败: {str(e)}")
    
    def get_branches(self, repo_name: str) -> List[str]:
        """获取GitLab仓库的分支列表，实现GitBaseToolkit的抽象方法"""
        try:
            project = self.get_repository(repo_name)
            branches = project.branches.list(all=True)
            return [branch.name for branch in branches]
        except Exception as e:
            raise Exception(f"获取GitLab仓库分支失败: {str(e)}")
    
    def _get_default_owner(self) -> str:
        """获取默认的仓库拥有者，实现GitBaseToolkit的抽象方法"""
        # 根据用户要求，将GitLab项目默认放在root命名空间下
        return "root" if not self.namespace else self.namespace
    
    def handle_rate_limit(self, func):
        """处理GitLab的速率限制，重写GitBaseToolkit的方法"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return GitLabInstanceManager.with_rate_limit_retry(
                self.instance_name, func, *args, **kwargs
            )
        return wrapper

    def gitlab_create_merge_request(
        self,
        project_id: ProjectIdentifier,
        file_path: str,
        new_content: str,
        mr_title: str,
        body: str,
        branch_name: str,
        instance_name: Optional[str] = None,
    ) -> str:
        r"""Creates a merge request.

        This function creates a merge request in specified repository, which
        updates a file in the specific path with new content. The merge request
        description contains information about the issue title and number.

        Args:
            project_id: The ID or path of the GitLab project.
            file_path: The path of the file to be updated in the
                repository.
            new_content: The specified new content of the specified file.
            mr_title: The title of the issue that is solved by this merge
                request.
            body: The commit message for the merge request.
            branch_name: The name of the branch to create and submit the
                merge request from.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A formatted report of whether the merge request was created
                successfully or not.
        """
        def create_mr():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            default_branch = project.default_branch
            
            # Get the file on the default branch
            try:
                file = project.files.get(file_path=file_path, ref=default_branch)
                file_content = file.content
            except Exception as e:
                return f"Failed to get file: {e!s}"
            
            # Create a new branch
            try:
                # Get the default branch's commit SHA
                default_branch_commit = project.commits.get(default_branch)
                
                # Create the new branch
                project.branches.create({
                    'branch': branch_name,
                    'ref': default_branch_commit.id
                })
            except Exception as e:
                if "Branch already exists" in str(e):
                    logger.warning(f"Branch {branch_name} already exists. Continuing with the existing branch.")
                else:
                    return f"Failed to create branch: {e!s}"
            
            # Update the file on the new branch
            try:
                project.files.update(
                    file_path=file_path,
                    branch=branch_name,
                    content=new_content,
                    commit_message=body
                )
            except Exception as e:
                return f"Failed to update file: {e!s}"
            
            # Create the merge request
            try:
                mr = project.mergerequests.create({
                    'source_branch': branch_name,
                    'target_branch': default_branch,
                    'title': mr_title,
                    'description': body
                })
                
                if mr is not None:
                    return f"Title: {mr.title}\n" f"Description: {mr.description}\n" f"Merge Request ID: {mr.iid}\n" f"Web URL: {mr.web_url}\n"
                else:
                    return "Failed to create merge request."
            except Exception as e:
                return f"Failed to create merge request: {e!s}"
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, create_mr
        )

    def gitlab_get_issue_list(
        self, 
        project_id: Optional[ProjectIdentifier] = None,
        namespace: Optional[str] = None,
        state: Literal["opened", "closed", "all"] = "all",
        instance_name: Optional[str] = None
    ) -> List[Dict[str, object]]:
        r"""Retrieves issues from the GitLab project or namespace.

        Args:
            project_id: The ID or path of the GitLab project. If None, uses namespace.
            namespace: The namespace to retrieve issues from. If None and project_id is None,
                uses the namespace specified during initialization.
            state: The state of issues to retrieve. (default: :obj:`all`)
                Options are:
                - "opened": Retrieve only open issues.
                - "closed": Retrieve only closed issues.
                - "all": Retrieve all issues, regardless of state.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A list of dictionaries where each dictionary contains the issue iid and title.

        Raises:
            ValueError: If neither project_id nor namespace is provided and no default namespace is set.
        """
        def get_issues():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            
            if project_id is not None:
                # Project-specific issues
                project = gitlab_instance.projects.get(project_id)
                issues = project.issues.list(state=state, as_list=False)
            else:
                # Namespace issues
                current_namespace = namespace or self.namespace
                if not current_namespace:
                    raise ValueError("Either project_id or namespace must be provided, or a default namespace must be set during initialization")
                
                # Get namespace object
                namespaces = gitlab_instance.namespaces.list(search=current_namespace)
                if not namespaces:
                    raise ValueError(f"Namespace '{current_namespace}' not found")
                
                # Get issues for all projects in the namespace
                issues = []
                for ns in namespaces:
                    if ns.path == current_namespace:
                        # Get all projects in the namespace
                        projects = gitlab_instance.projects.list(namespace_id=ns.id, as_list=False)
                        # Get issues for each project
                        for project in projects:
                            project_issues = project.issues.list(state=state, as_list=False)
                            issues.extend(project_issues)
                        break
            
            issues_info = []
            for issue in issues:
                issues_info.append({"iid": issue.iid, "title": issue.title, "project_id": issue.project_id})
            
            return issues_info
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, get_issues
        )

    def gitlab_get_issue_content(
        self,
        project_id: ProjectIdentifier,
        issue_iid: IssueIdentifier,
        instance_name: Optional[str] = None
    ) -> str:
        r"""Retrieves the content of a specific issue by its iid.

        Args:
            project_id: The ID or path of the GitLab project.
            issue_iid: The iid of the issue to retrieve.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            Issue content details.
        """
        def get_issue_content():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            try:
                project = gitlab_instance.projects.get(project_id)
                issue = project.issues.get(issue_iid)
                return issue.description
            except Exception as e:
                return f"can't get Issue iid {issue_iid}: {e!s}"
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, get_issue_content
        )

    def gitlab_get_merge_request_list(
        self,
        project_id: Optional[ProjectIdentifier] = None,
        namespace: Optional[str] = None,
        state: Literal["opened", "closed", "merged", "all"] = "all",
        instance_name: Optional[str] = None
    ) -> List[Dict[str, object]]:
        r"""Retrieves merge requests from the GitLab project or namespace.

        Args:
            project_id: The ID or path of the GitLab project. If None, uses namespace.
            namespace: The namespace to retrieve merge requests from. If None and project_id is None,
                uses the namespace specified during initialization.
            state: The state of merge requests to retrieve. (default: :obj:`all`)
                Options are:
                - "opened": Retrieve only open merge requests.
                - "closed": Retrieve only closed merge requests.
                - "merged": Retrieve only merged merge requests.
                - "all": Retrieve all merge requests, regardless of state.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A list of dictionaries where each dictionary contains the merge request iid and title.

        Raises:
            ValueError: If neither project_id nor namespace is provided and no default namespace is set.
        """
        def get_merge_requests():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            
            if project_id is not None:
                # Project-specific merge requests
                project = gitlab_instance.projects.get(project_id)
                merge_requests = project.mergerequests.list(state=state, as_list=False)
            else:
                # Namespace merge requests
                current_namespace = namespace or self.namespace
                if not current_namespace:
                    raise ValueError("Either project_id or namespace must be provided, or a default namespace must be set during initialization")
                
                # Get namespace object
                namespaces = gitlab_instance.namespaces.list(search=current_namespace)
                if not namespaces:
                    raise ValueError(f"Namespace '{current_namespace}' not found")
                
                # Get merge requests for all projects in the namespace
                merge_requests = []
                for ns in namespaces:
                    if ns.path == current_namespace:
                        # Get all projects in the namespace
                        projects = gitlab_instance.projects.list(namespace_id=ns.id, as_list=False)
                        # Get merge requests for each project
                        for project in projects:
                            project_mrs = project.mergerequests.list(state=state, as_list=False)
                            merge_requests.extend(project_mrs)
                        break
            
            merge_requests_info = []
            for mr in merge_requests:
                merge_requests_info.append({"iid": mr.iid, "title": mr.title, "project_id": mr.project_id})
            
            return merge_requests_info
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, get_merge_requests
        )

    def gitlab_get_merge_request_code(
        self,
        project_id: ProjectIdentifier,
        mr_iid: MRIdentifier,
        instance_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        r"""Retrieves the code changes of a specific merge request.

        Args:
            project_id: The ID or path of the GitLab project.
            mr_iid: The iid of the merge request to retrieve (project-internal unique).
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A list of dictionaries where each dictionary contains the file name and the corresponding code changes (diff).
        """
        def get_merge_request_code():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            # Retrieve the specific merge request
            mr = project.mergerequests.get(mr_iid)

            # Collect the file changes from the merge request
            files_changed = []
            # Returns the files and their changes in the merge request
            changes = mr.changes()['changes']
            for file_change in changes:
                files_changed.append({
                    "filename": file_change['old_path'] if 'old_path' in file_change else file_change['new_path'],
                    "patch": file_change['diff']  # The code diff or changes
                })

            return files_changed
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, get_merge_request_code
        )

    def gitlab_get_merge_request_comments(
        self,
        project_id: ProjectIdentifier,
        mr_iid: MRIdentifier,
        instance_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        r"""Retrieves the comments from a specific merge request.

        Args:
            project_id: The ID or path of the GitLab project.
            mr_iid: The iid of the merge request to retrieve (project-internal unique).
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A list of dictionaries where each dictionary contains the user ID and the comment body.
        """
        def get_merge_request_comments():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            # Retrieve the specific merge request
            mr = project.mergerequests.get(mr_iid)

            # Collect the comments from the merge request
            comments = []
            # Returns all the comments in the merge request
            for comment in mr.notes.list():
                comments.append({"user": comment.author['username'], "body": comment.body})

            return comments
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, get_merge_request_comments
        )

    def gitlab_get_all_file_paths(
        self,
        project_id: ProjectIdentifier,
        path: str = "",
        instance_name: Optional[str] = None
    ) -> List[str]:
        r"""Recursively retrieves all file paths in the GitLab project.

        Args:
            project_id: The ID or path of the GitLab project.
            path: The repository path to start the traversal from.
                empty string means starts from the root directory.
                (default: :obj:`""`)
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A list of file paths within the specified directory structure.
        """
        def get_all_file_paths_recursive(current_path):
            files = []
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            # Retrieves all contents of the current directory
            contents = project.repository_tree(path=current_path, all=True)

            for item in contents:
                if item['type'] == 'tree':
                    # If it's a directory, recursively retrieve its file paths
                    files.extend(get_all_file_paths_recursive(item['path']))
                else:
                    # If it's a file, add its path to the list
                    files.append(item['path'])
            return files
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, lambda: get_all_file_paths_recursive(path)
        )

    def gitlab_retrieve_file_content(
        self,
        project_id: ProjectIdentifier,
        file_path: str,
        instance_name: Optional[str] = None
    ) -> str:
        r"""Retrieves the content of a file from the GitLab project.

        Args:
            project_id: The ID or path of the GitLab project.
            file_path: The path of the file to retrieve.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            The decoded content of the file.
        """
        def retrieve_file_content():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            try:
                file = project.files.get(file_path=file_path, ref=project.default_branch)
                import base64
                return base64.b64decode(file.content).decode()
            except Exception as e:
                raise ValueError(f"Failed to retrieve file content: {e!s}")
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, retrieve_file_content
        )

    def gitlab_create_webhook(
        self,
        project_id: ProjectIdentifier,
        url: str,
        events: Optional[List[str]] = None,
        push_events: bool = True,
        push_events_branch_filter: str = '*',
        merge_requests_events: bool = True,
        tag_push_events: bool = True,
        enable_ssl_verification: bool = True,
        token: Optional[str] = None,
        instance_name: Optional[str] = None
    ) -> Dict[str, Any]:
        r"""Creates a webhook for the specified GitLab project.

        Args:
            project_id: The ID or path of the GitLab project.
            url: The URL to which the webhook will send data.
            events: List of event names to trigger the webhook. If None, uses default events.
            push_events: Whether to trigger the webhook for push events.
            push_events_branch_filter: Branch filter for push events. Default '*' (all branches).
            merge_requests_events: Whether to trigger the webhook for merge request events.
            tag_push_events: Whether to trigger the webhook for tag push events.
            enable_ssl_verification: Whether to verify SSL certificates.
            token: Secret token for webhook authentication.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A dictionary with webhook information if successful, or error message if failed.
        """
        def create_webhook():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            # Prepare webhook data
            webhook_data = {
                'url': url,
                'push_events': push_events,
                'push_events_branch_filter': push_events_branch_filter,
                'merge_requests_events': merge_requests_events,
                'tag_push_events': tag_push_events,
                'enable_ssl_verification': enable_ssl_verification,
            }
            
            # Add token if provided
            if token:
                webhook_data['token'] = token
            
            # Create webhook
            try:
                webhook = project.hooks.create(webhook_data)
                return {
                    'id': webhook.id,
                    'url': webhook.url,
                    'created_at': webhook.created_at,
                    'events': {
                        'push_events': webhook.push_events,
                        'merge_requests_events': webhook.merge_requests_events,
                        'tag_push_events': webhook.tag_push_events
                    }
                }
            except Exception as e:
                return {'error': f"Failed to create webhook: {str(e)}"}
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, create_webhook
        )

    def gitlab_list_webhooks(
        self,
        project_id: ProjectIdentifier,
        instance_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        r"""Lists all webhooks for the specified GitLab project.

        Args:
            project_id: The ID or path of the GitLab project.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A list of dictionaries containing webhook information.
        """
        def list_webhooks():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            try:
                webhooks = project.hooks.list(all=True)
                return [
                    {
                        'id': hook.id,
                        'url': hook.url,
                        'created_at': hook.created_at,
                        'events': {
                            'push_events': hook.push_events,
                            'merge_requests_events': hook.merge_requests_events,
                            'tag_push_events': hook.tag_push_events
                        },
                        'enable_ssl_verification': hook.enable_ssl_verification
                    }
                    for hook in webhooks
                ]
            except Exception as e:
                return [{'error': f"Failed to list webhooks: {str(e)}"}]
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, list_webhooks
        )

    def gitlab_delete_webhook(
        self,
        project_id: ProjectIdentifier,
        webhook_id: int,
        instance_name: Optional[str] = None
    ) -> Dict[str, str]:
        r"""Deletes a specific webhook from the GitLab project.

        Args:
            project_id: The ID or path of the GitLab project.
            webhook_id: The ID of the webhook to delete.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A dictionary with status message.
        """
        def delete_webhook():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            try:
                project.hooks.delete(webhook_id)
                return {'status': 'success', 'message': f'Webhook {webhook_id} deleted successfully'}
            except Exception as e:
                return {'status': 'error', 'message': f'Failed to delete webhook: {str(e)}'}
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, delete_webhook
        )

    def gitlab_update_webhook(
        self,
        project_id: ProjectIdentifier,
        webhook_id: int,
        url: Optional[str] = None,
        events: Optional[Dict[str, bool]] = None,
        push_events_branch_filter: Optional[str] = None,
        enable_ssl_verification: Optional[bool] = None,
        token: Optional[str] = None,
        instance_name: Optional[str] = None
    ) -> Dict[str, Any]:
        r"""Updates an existing webhook in the GitLab project.

        Args:
            project_id: The ID or path of the GitLab project.
            webhook_id: The ID of the webhook to update.
            url: The new URL for the webhook (if updating).
            events: Dictionary of event flags to update.
            push_events_branch_filter: New branch filter for push events.
            enable_ssl_verification: New SSL verification setting.
            token: New secret token for webhook authentication.
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A dictionary with updated webhook information if successful, or error message if failed.
        """
        def update_webhook():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            try:
                # Get existing webhook
                webhook = project.hooks.get(webhook_id)
                
                # Prepare update data
                update_data = {}
                if url is not None:
                    update_data['url'] = url
                
                if events:
                    update_data.update(events)
                
                if push_events_branch_filter is not None:
                    update_data['push_events_branch_filter'] = push_events_branch_filter
                
                if enable_ssl_verification is not None:
                    update_data['enable_ssl_verification'] = enable_ssl_verification
                
                if token is not None:
                    update_data['token'] = token
                
                # Update webhook
                webhook.save(update_data)
                
                return {
                    'id': webhook.id,
                    'url': webhook.url,
                    'created_at': webhook.created_at,
                    'events': {
                        'push_events': webhook.push_events,
                        'merge_requests_events': webhook.merge_requests_events,
                        'tag_push_events': webhook.tag_push_events
                    },
                    'enable_ssl_verification': webhook.enable_ssl_verification
                }
            except Exception as e:
                return {'error': f"Failed to update webhook: {str(e)}"}
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, update_webhook
        )

    def gitlab_test_webhook(
        self,
        project_id: ProjectIdentifier,
        webhook_id: int,
        event_name: str = 'push_events',
        instance_name: Optional[str] = None
    ) -> Dict[str, Any]:
        r"""Tests a webhook by sending a sample event to the webhook URL.

        Args:
            project_id: The ID or path of the GitLab project.
            webhook_id: The ID of the webhook to test.
            event_name: The type of event to test (push_events, merge_requests_events, etc.).
            instance_name: The name of the GitLab instance to use.
                If None, uses the instance specified during initialization.

        Returns:
            A dictionary with test result information.
        """
        def test_webhook():
            gitlab_instance = GitLabInstanceManager.get_instance(instance_name or self.instance_name)
            project = gitlab_instance.projects.get(project_id)
            
            try:
                webhook = project.hooks.get(webhook_id)
                result = webhook.test(event_name)
                return {
                    'status': 'success',
                    'event_name': event_name,
                    'result': result
                }
            except Exception as e:
                return {'status': 'error', 'message': f'Failed to test webhook: {str(e)}'}
        
        # Execute with rate limit retry
        return GitLabInstanceManager.with_rate_limit_retry(
            instance_name or self.instance_name, test_webhook
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            A list of FunctionTool objects representing the functions in the toolkit.
        """
        # 获取GitBaseToolkit中的基础工具
        tools = super().get_tools()
        
        # 添加特定于GitLab的工具
        tools.extend([
            FunctionTool(self.gitlab_create_merge_request),
            FunctionTool(self.gitlab_get_issue_list),
            FunctionTool(self.gitlab_get_issue_content),
            FunctionTool(self.gitlab_get_merge_request_list),
            FunctionTool(self.gitlab_get_merge_request_code),
            FunctionTool(self.gitlab_get_merge_request_comments),
            FunctionTool(self.gitlab_get_all_file_paths),
            FunctionTool(self.gitlab_retrieve_file_content),
            FunctionTool(self.gitlab_create_webhook),
            FunctionTool(self.gitlab_list_webhooks),
            FunctionTool(self.gitlab_delete_webhook),
            FunctionTool(self.gitlab_update_webhook),
            FunctionTool(self.gitlab_test_webhook),
        ])
        
        return tools

    # Deprecated method aliases for backward compatibility (if needed in future)
    def create_merge_request(self, *args, **kwargs):
        r"""Deprecated: Use gitlab_create_merge_request instead."""
        warnings.warn(
            "create_merge_request is deprecated. Use "
            "gitlab_create_merge_request instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_create_merge_request(*args, **kwargs)

    def get_issue_list(self, project_id: str, state: Literal["opened", "closed", "all"] = "all"):
        r"""Deprecated: Use gitlab_get_issue_list instead."""
        warnings.warn(
            "get_issue_list is deprecated. Use gitlab_get_issue_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_get_issue_list(project_id=project_id, state=state)

    def get_issue_content(self, project_id: str, issue_iid: int):
        r"""Deprecated: Use gitlab_get_issue_content instead."""
        warnings.warn(
            "get_issue_content is deprecated. Use "
            "gitlab_get_issue_content instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_get_issue_content(project_id=project_id, issue_iid=issue_iid)

    def get_merge_request_list(self, project_id: str, state: Literal["opened", "closed", "merged", "all"] = "all"):
        r"""Deprecated: Use gitlab_get_merge_request_list instead."""
        warnings.warn(
            "get_merge_request_list is deprecated. "
            "Use gitlab_get_merge_request_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_get_merge_request_list(project_id=project_id, state=state)

    def get_merge_request_code(self, project_id: str, mr_iid: int):
        r"""Deprecated: Use gitlab_get_merge_request_code instead."""
        warnings.warn(
            "get_merge_request_code is deprecated. Use "
            "gitlab_get_merge_request_code instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_get_merge_request_code(project_id=project_id, mr_iid=mr_iid)

    def get_merge_request_comments(self, project_id: str, mr_iid: int):
        r"""Deprecated: Use gitlab_get_merge_request_comments instead."""
        warnings.warn(
            "get_merge_request_comments is deprecated. "
            "Use gitlab_get_merge_request_comments instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_get_merge_request_comments(project_id=project_id, mr_iid=mr_iid)

    def get_all_file_paths(self, project_id: str, path: str = ""):
        r"""Deprecated: Use gitlab_get_all_file_paths instead."""
        warnings.warn(
            "get_all_file_paths is deprecated. Use "
            "gitlab_get_all_file_paths instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_get_all_file_paths(project_id=project_id, path=path)

    def retrieve_file_content(self, project_id: str, file_path: str):
        r"""Deprecated: Use gitlab_retrieve_file_content instead."""
        warnings.warn(
            "retrieve_file_content is deprecated. "
            "Use gitlab_retrieve_file_content instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.gitlab_retrieve_file_content(project_id=project_id, file_path=file_path)