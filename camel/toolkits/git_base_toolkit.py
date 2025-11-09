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
import sys
import logging
import subprocess
from typing import Dict, List, Optional, Tuple, Any, TypeVar, Generic, overload, Callable, Union
from functools import wraps
from abc import ABC, abstractmethod

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.version_control_base_toolkit import VersionControlBaseToolkit
from camel.toolkits import FunctionTool

# 导入版本控制类型和错误类
from camel.types.version_control import (
    RepoID, RepoPath, BranchName, CommitSHA, 
    RepositoryNotFoundError, AuthenticationError,
    OperationFailedError, ResourceNotFoundError,
    SyncResult, VersionControlConnectionError
)

logger = get_logger(__name__)

# 定义Git相关的强类型
RepoName: TypeVar = str
BranchName: TypeVar = str

class GitBaseToolkit(VersionControlBaseToolkit):
    """
    Git平台工具包的抽象基类，定义统一的接口
    
    为不同Git平台（如GitHub、Gitee、GitLab）提供统一的接口，使上层应用可以通过一致的方式
    与不同的Git平台进行交互，而不需要关心具体平台的实现细节。
    """
    
    # 平台名称，由子类实现
    PLATFORM_NAME: str = "generic"
    
    def __init__(self, access_token: Optional[str] = None, timeout: Optional[float] = None):
        """
        初始化Git工具包
        
        Args:
            access_token: 访问平台API所需的令牌，如果不提供，将尝试从环境变量获取
            timeout: API请求的超时时间（秒）
            
        Raises:
            AuthenticationError: 如果认证失败
            OperationFailedError: 如果初始化失败
        """
        super().__init__(timeout=timeout)
        self.access_token = access_token
        self._client = None
        
        # 尝试从环境变量获取访问令牌
        if not self.access_token:
            self._try_get_token_from_env()
        
        # 初始化客户端
        self._initialize_client()
    
    def _try_get_token_from_env(self) -> None:
        """
        尝试从环境变量获取访问令牌
        子类应该实现此方法，根据具体平台从对应的环境变量获取令牌
        """
        pass
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """
        初始化平台客户端
        
        由子类实现，用于创建与特定Git平台通信的客户端实例
        
        Raises:
            AuthenticationError: 如果认证失败
            OperationFailedError: 如果客户端初始化失败
        """
        raise NotImplementedError("子类必须实现_initialize_client方法")
    
    def get_repository_info(self, repository_path: Union[str, RepoID]) -> Dict[str, Any]:
        """
        获取仓库信息
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            Dict[str, Any]: 包含仓库信息的字典
        """
        # 尝试使用get_repository获取仓库对象并转换为字典
        try:
            repo = self.get_repository(repository_path)
            # 这是一个基本实现，子类应该提供更具体的实现
            return {"name": str(repository_path), "exists": True}
        except RepositoryNotFoundError:
            return {"name": str(repository_path), "exists": False}
        except Exception as e:
            logger.error(f"获取仓库信息失败: {str(e)}")
            return {"name": str(repository_path), "exists": False, "error": str(e)}
    
    @abstractmethod
    def get_repository(self, repo_name: Union[str, RepoID]) -> Any:
        """
        获取仓库对象
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或RepoID对象
            
        Returns:
            仓库对象，具体类型由子类实现决定
            
        Raises:
            RepositoryNotFoundError: 如果仓库不存在
            OperationFailedError: 如果获取仓库失败
        """
        raise NotImplementedError("子类必须实现get_repository方法")
    
    def create_repository(self, repository_path: Union[str, RepoID], **kwargs) -> bool:
        """
        创建新仓库
        
        Args:
            repository_path: 仓库路径或标识符
            **kwargs: 其他创建参数
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 调用子类实现的_create_repository方法
            result = self._create_repository(repository_path, **kwargs)
            return True
        except OperationFailedError:
            raise
        except Exception as e:
            logger.error(f"创建仓库失败: {str(e)}")
            return False
    
    @abstractmethod
    def _create_repository(self, repo_name: Union[str, RepoID], **kwargs) -> Dict[str, Any]:
        """
        创建新仓库（内部实现，由子类重写）
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或RepoID对象
            **kwargs: 其他创建仓库时可能需要的参数
                - description: 仓库描述
                - private: 是否为私有仓库
                - auto_init: 是否自动初始化仓库
                - ...
                
        Returns:
            包含仓库信息的字典，必须包含以下键：
                - name: 仓库全名
                - url: 仓库的Web访问URL
                - clone_url: 仓库的克隆URL
                
        Raises:
            OperationFailedError: 如果创建仓库失败
        """
        raise NotImplementedError("子类必须实现_create_repository方法")
        
    def clone_or_checkout(self, source_path: Union[str, RepoID], local_path: str, **kwargs) -> bool:
        """
        克隆或检出仓库
        
        Args:
            source_path: 源仓库路径或标识符
            local_path: 本地路径
            **kwargs: 其他参数（如分支、版本等）
            
        Returns:
            bool: 操作是否成功
            
        Raises:
            RepositoryNotFoundError: 如果仓库不存在
            OperationFailedError: 如果克隆或检出失败
        """
        try:
            branch = kwargs.get('branch')
            tag = kwargs.get('tag')
            logger.debug(f"尝试克隆/检出仓库: {source_path} 到 {local_path}")
            
            # 检查本地路径是否已存在
            if os.path.exists(local_path):
                # 如果已存在，尝试检出指定分支
                logger.info(f"本地路径已存在，尝试检出分支: {branch or '默认分支'}")
                return self._checkout_existing_repo(local_path, branch)
            else:
                # 克隆仓库
                clone_url = self.get_clone_url(source_path)
                logger.info(f"克隆仓库到 {local_path}")
                return self._clone_repo(clone_url, local_path, branch)
        except RepositoryNotFoundError:
            raise
        except Exception as e:
            logger.error(f"克隆/检出仓库失败: {str(e)}")
            raise OperationFailedError(f"克隆/检出仓库失败: {str(e)}")
    
    def _clone_repo(self, clone_url: str, local_path: str, branch: Optional[str] = None) -> bool:
        """
        执行git clone命令
        
        Args:
            clone_url: 克隆URL
            local_path: 本地路径
            branch: 分支名称
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 创建父目录
            os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
            
            # 构建git clone命令
            cmd = ['git', 'clone']
            if branch:
                cmd.extend(['-b', branch])
            cmd.extend([clone_url, local_path])
            
            # 执行命令
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True)
            logger.info(f"成功克隆仓库到 {local_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone失败: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"克隆仓库时发生错误: {str(e)}")
            return False
    
    def _checkout_existing_repo(self, local_path: str, branch: Optional[str] = None) -> bool:
        """
        检出已有仓库的分支
        
        Args:
            local_path: 本地仓库路径
            branch: 分支名称
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 确保在仓库目录中
            original_dir = os.getcwd()
            os.chdir(local_path)
            
            # 拉取最新代码
            subprocess.run(['git', 'pull'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 如果指定了分支，检出该分支
            if branch:
                subprocess.run(['git', 'checkout', branch], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(['git', 'pull', 'origin', branch], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            os.chdir(original_dir)
            logger.info(f"成功检出仓库分支: {branch or '默认分支'}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git操作失败: {e.stderr}")
            os.chdir(original_dir)
            return False
        except Exception as e:
            logger.error(f"检出仓库时发生错误: {str(e)}")
            os.chdir(original_dir)
            return False
    
    def get_branches_or_tags(self, repository_path: Union[str, RepoID]) -> Dict[str, List[str]]:
        """
        获取仓库的分支和标签信息
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            Dict[str, List[str]]: 包含branches和tags列表的字典
            
        Raises:
            RepositoryNotFoundError: 如果仓库不存在
            OperationFailedError: 如果获取分支和标签失败
        """
        try:
            # 获取分支信息
            branches = self.get_branches(repository_path)
            
            # 获取标签信息
            tags = self._get_tags(repository_path)
            
            return {
                'branches': branches,
                'tags': tags
            }
        except RepositoryNotFoundError:
            raise
        except Exception as e:
            logger.error(f"获取分支和标签失败: {str(e)}")
            raise OperationFailedError(f"获取分支和标签失败: {str(e)}")
    
    def _get_tags(self, repo_id: Union[str, RepoID]) -> List[str]:
        """
        获取仓库的标签列表
        子类应该实现此方法
        
        Args:
            repo_id: 仓库标识符
            
        Returns:
            List[str]: 标签名称列表
        """
        return []
    
    @abstractmethod
    def get_latest_commit_info(self, repository_path: Union[str, RepoID], branch: Optional[str] = None) -> Dict[str, Any]:
        """
        获取最新提交信息
        
        Args:
            repository_path: 仓库路径或标识符
            branch: 分支名称，默认为None（使用默认分支）
            
        Returns:
            Dict[str, Any]: 包含提交信息的字典
            
        Raises:
            RepositoryNotFoundError: 如果仓库不存在
            OperationFailedError: 如果获取提交信息失败
        """
        raise NotImplementedError("子类必须实现get_latest_commit_info方法")
    
    def push_changes(self, local_path: str, remote_path: Union[str, RepoID] = None, **kwargs) -> bool:
        """
        推送更改到远程仓库
        
        Args:
            local_path: 本地仓库路径
            remote_path: 远程仓库路径（可选）
            **kwargs: 其他推送参数，包括message（提交信息）和branch（分支名称）
            
        Returns:
            bool: 推送是否成功
            
        Raises:
            OperationFailedError: 如果推送失败
        """
        try:
            message = kwargs.get('message', 'Auto commit')
            branch = kwargs.get('branch')
            username = kwargs.get('username')
            email = kwargs.get('email')
            
            logger.debug(f"尝试推送更改: 从 {local_path} 到 {remote_path or '默认远程'}")
            
            original_dir = os.getcwd()
            os.chdir(local_path)
            
            # 设置用户名和邮箱（如果提供）
            if username:
                subprocess.run(['git', 'config', 'user.name', username], check=True)
            if email:
                subprocess.run(['git', 'config', 'user.email', email], check=True)
            
            # 暂存所有更改
            subprocess.run(['git', 'add', '.'], check=True)
            
            # 提交更改
            subprocess.run(['git', 'commit', '-m', message], check=True)
            
            # 推送更改
            if branch:
                subprocess.run(['git', 'push', 'origin', branch], check=True)
            else:
                subprocess.run(['git', 'push', 'origin'], check=True)
            
            os.chdir(original_dir)
            logger.info(f"成功推送更改到 {branch or '默认分支'}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git操作失败: {e.stderr}")
            if 'original_dir' in locals():
                os.chdir(original_dir)
            raise OperationFailedError(f"推送更改失败: {e.stderr}")
        except Exception as e:
            logger.error(f"推送更改时发生错误: {str(e)}")
            if 'original_dir' in locals():
                os.chdir(original_dir)
            raise OperationFailedError(f"推送更改失败: {str(e)}")
    
    def is_repository_exist(self, repository_path: Union[str, RepoID]) -> bool:
        """
        检查仓库是否存在
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            bool: 仓库是否存在
        """
        try:
            # 尝试获取仓库信息，如果成功则仓库存在
            self.get_repository(repository_path)
            return True
        except RepositoryNotFoundError:
            return False
        except Exception as e:
            logger.error(f"检查仓库是否存在时出错: {str(e)}")
            return False
    
    def repository_exists(self, repository_path: Union[str, RepoID]) -> bool:
        """
        检查仓库是否存在（向后兼容方法）
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            bool: 仓库是否存在
        """
        return self.is_repository_exist(repository_path)
    
    @abstractmethod
    def get_clone_url(self, repo_name: Union[str, RepoID], use_token: bool = True) -> str:
        """
        获取仓库克隆URL
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或RepoID对象
            use_token: 是否在URL中包含认证令牌
            
        Returns:
            可用于克隆仓库的URL
            
        Raises:
            RepositoryNotFoundError: 如果仓库不存在
        """
        raise NotImplementedError("子类必须实现get_clone_url方法")
    
    @abstractmethod
    def get_branches(self, repo_name: Union[str, RepoID]) -> List[str]:
        """
        获取仓库分支列表
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或RepoID对象
            
        Returns:
            仓库所有分支名称的列表
            
        Raises:
            RepositoryNotFoundError: 如果仓库不存在
            OperationFailedError: 如果获取分支列表失败
        """
        raise NotImplementedError("子类必须实现get_branches方法")
    
    @abstractmethod
    def list_repositories(self, **kwargs) -> List[Dict[str, Any]]:
        """
        列出用户或组织的仓库
        
        Args:
            **kwargs: 其他可能的参数
                - owner: 所有者名称（用户或组织）
                - per_page: 每页返回的仓库数量
                - page: 页码
                - ...
                
        Returns:
            List[Dict[str, Any]]: 仓库信息列表
            
        Raises:
            OperationFailedError: 如果列出仓库失败
        """
        raise NotImplementedError("子类必须实现list_repositories方法")
    
    def handle_rate_limit(self, func):
        """
        处理速率限制的装饰器基类实现
        
        子类可以重写这个方法以实现特定平台的速率限制处理逻辑
        
        Args:
            func: 要装饰的函数
            
        Returns:
            装饰后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 基类提供通用实现，子类可以重写
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 通用错误处理
                logger.error(f"{self.PLATFORM_NAME}操作失败: {str(e)}")
                raise
        return wrapper
    
    def _parse_repo_name(self, repo_name: Union[str, RepoID]) -> Tuple[str, str]:
        """
        解析仓库名为(owner, name)格式
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或RepoID对象
            
        Returns:
            (owner, repo_name)元组
            
        Raises:
            ValueError: 如果仓库标识符格式错误
        """
        if isinstance(repo_name, RepoID):
            return repo_name.owner, repo_name.name
        
        parts = str(repo_name).split('/')
        if len(parts) == 2:
            return parts[0], parts[1]
        # 默认实现，需要子类根据实际情况重写
        return self._get_default_owner(), str(repo_name)
    
    @abstractmethod
    def _get_default_owner(self) -> str:
        """
        获取默认的仓库拥有者
        
        由子类实现，用于确定当只提供仓库名而不提供拥有者时的默认拥有者
        
        Returns:
            默认拥有者名称
        """
        raise NotImplementedError("子类必须实现_get_default_owner方法")
    
    @abstractmethod
    def _test_credentials(self) -> bool:
        """
        测试凭证是否有效
        
        由子类实现，用于验证访问令牌是否有效
        
        Returns:
            bool: 如果凭证有效则返回True，否则返回False
        """
        raise NotImplementedError("子类必须实现_test_credentials方法")
    
    def get_platform_name(self) -> str:
        """
        获取平台名称
        
        Returns:
            平台名称字符串
        """
        return self.PLATFORM_NAME
    
    def _ensure_tool_available(self) -> bool:
        """
        确保Git工具可用

        Returns:
            bool: Git工具是否可用
        """
        try:
            result = subprocess.run(
                ["git", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True if sys.platform == 'win32' else False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def get_toolkit_info(self) -> Dict[str, Any]:
        """
        获取Git工具包信息
        
        Returns:
            Dict[str, Any]: 工具包信息字典，包含Git版本、可用性等信息
        """
        try:
            # 获取Git版本信息
            result = subprocess.run(
                ["git", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True if sys.platform == 'win32' else False,
                text=True
            )
            
            version = result.stdout.strip() if result.returncode == 0 else '未知'
            
            return {
                'toolkit_name': 'GitBaseToolkit',
                'platform_name': self.PLATFORM_NAME,
                'git_available': self._ensure_tool_available(),
                'git_version': version,
                'credentials_provided': bool(self.access_token),
                'timeout': self.timeout
            }
        except Exception as e:
            return {
                'toolkit_name': 'GitBaseToolkit',
                'platform_name': self.PLATFORM_NAME,
                'git_available': False,
                'error': str(e)
            }
    
    def validate_credentials(self) -> bool:
        """
        验证Git凭证是否有效
        
        Returns:
            bool: 凭证是否有效
        """
        if not self._ensure_tool_available():
            return False
        
        # 对于Git，我们只验证凭证格式是否正确
        # 实际的凭证验证通常在执行具体操作时进行
        if self.access_token:
            # 检查access_token是否为非空字符串
            return isinstance(self.access_token, str) and len(self.access_token.strip()) > 0
        
        # 如果没有提供凭证，认为是匿名访问
        return True
    
    def get_tools(self) -> Dict[str, Callable]:
        """
        获取所有可用的工具方法
        
        Returns:
            Dict[str, Callable]: 工具方法字典
        """
        # 获取基类的工具方法
        tools = super().get_tools()
        
        # 添加Git特有工具方法
        git_tools = {
            'get_repository': self.get_repository,
            'get_repository_info': self.get_repository_info,
            'create_repository': self.create_repository,
            'get_clone_url': self.get_clone_url,
            'get_branches': self.get_branches,
            'list_repositories': self.list_repositories,
            'clone_or_checkout': self.clone_or_checkout,
            'get_branches_or_tags': self.get_branches_or_tags,
            'get_latest_commit_info': self.get_latest_commit_info,
            'push_changes': self.push_changes,
            'is_repository_exist': self.is_repository_exist,
            'repository_exists': self.repository_exists,
            'validate_credentials': self.validate_credentials,
            'get_toolkit_info': self.get_toolkit_info,
            'get_platform_name': self.get_platform_name
        }
        
        # 合并工具方法
        tools.update(git_tools)
        return tools