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
import time
import logging
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Literal, NewType, Optional, Union, overload, Tuple

import requests
from typing_extensions import TypeAlias

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.git_base_toolkit import GitBaseToolkit

logger = get_logger(__name__)

# 强类型定义
GiteeProjectId: TypeAlias = Union[int, str]
GiteeIssueIid: TypeAlias = int
GiteePullRequestIid: TypeAlias = int
GiteeCommitId: TypeAlias = str
GiteeUserId: TypeAlias = Union[int, str]
GiteeBranchName: TypeAlias = str

# 项目标识符类，用于区分项目ID和路径
@dataclass
class GiteeProjectIdentifier:
    """表示Gitee项目的标识符，可以是项目ID或项目路径。"""
    value: Union[int, str]
    is_path: bool = False

    def __str__(self) -> str:
        return str(self.value)

# 环境变量相关常量
DEFAULT_GITEE_INSTANCE_NAME = "default"
DEFAULT_GITEE_URL = "https://gitee.com/api/v5"

# 错误处理
class GiteeError(Exception):
    """Gitee API相关的基础异常类。"""
    pass

class GiteeRateLimitError(GiteeError):
    """当触发Gitee API速率限制时抛出。"""
    pass

class GiteeAuthenticationError(GiteeError):
    """当Gitee认证失败时抛出。"""
    pass

class GiteeNotFoundError(GiteeError):
    """当请求的Gitee资源不存在时抛出。"""
    pass

# 实例配置数据类
@dataclass
class GiteeInstanceConfig:
    """Gitee实例的配置信息。"""
    name: str
    url: str
    token: str
    verify_ssl: bool = True
    default_namespace: Optional[str] = None

    def get_headers(self) -> Dict[str, str]:
        """获取用于API请求的HTTP头。"""
        return {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_environment(
        cls, instance_name: str = DEFAULT_GITEE_INSTANCE_NAME
    ) -> "GiteeInstanceConfig":
        """从环境变量加载Gitee实例配置。"""
        instance_var_prefix = f"{instance_name.upper()}_GITEE_" if instance_name != DEFAULT_GITEE_INSTANCE_NAME else "GITEE_"
        
        token = os.environ.get(f"{instance_var_prefix}TOKEN")
        if not token:
            raise GiteeAuthenticationError(f"环境变量中未找到Gitee令牌: {instance_var_prefix}TOKEN")
        
        url = os.environ.get(f"{instance_var_prefix}URL", DEFAULT_GITEE_URL)
        verify_ssl = os.environ.get(f"{instance_var_prefix}VERIFY_SSL", "True").lower() != "false"
        default_namespace = os.environ.get(f"{instance_var_prefix}DEFAULT_NAMESPACE")
        
        return cls(
            name=instance_name,
            url=url,
            token=token,
            verify_ssl=verify_ssl,
            default_namespace=default_namespace
        )

# Gitee实例管理器
class GiteeInstanceManager:
    """管理多个Gitee实例的配置和连接。"""
    
    _instances: Dict[str, GiteeInstanceConfig] = {}
    
    @classmethod
    def register_instance(cls, config: GiteeInstanceConfig) -> None:
        """注册一个新的Gitee实例配置。"""
        cls._instances[config.name] = config
        logger.info(f"已注册Gitee实例: {config.name}")
    
    @classmethod
    def get_instance(cls, instance_name: str = DEFAULT_GITEE_INSTANCE_NAME) -> GiteeInstanceConfig:
        """获取指定名称的Gitee实例配置。"""
        if instance_name not in cls._instances:
            try:
                # 尝试从环境变量加载
                config = GiteeInstanceConfig.from_environment(instance_name)
                cls.register_instance(config)
                return config
            except Exception as e:
                raise GiteeError(f"未找到Gitee实例配置: {instance_name}") from e
        return cls._instances[instance_name]
    
    @classmethod
    def get_all_instances(cls) -> Dict[str, GiteeInstanceConfig]:
        """获取所有已注册的Gitee实例配置。"""
        return cls._instances.copy()
    
    @classmethod
    def clear_instances(cls) -> None:
        """清除所有已注册的Gitee实例配置。"""
        cls._instances.clear()
        logger.info("已清除所有Gitee实例配置")
    
    @classmethod
    def with_rate_limit_retry(cls, max_retries: int = 5, base_delay: float = 1.0):
        """处理Gitee API速率限制的装饰器。"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return func(*args, **kwargs)
                    except GiteeRateLimitError as e:
                        retries += 1
                        if retries >= max_retries:
                            raise
                        delay = base_delay * (2 ** (retries - 1)) * (0.5 + 0.5 * (retries % 2))
                        logger.warning(f"触发Gitee API速率限制，{delay:.2f}秒后重试... (第{retries}次重试)")
                        time.sleep(delay)
                    except Exception:
                        raise
            return wrapper
        return decorator

# 工具包类
class GiteeToolkit(GitBaseToolkit):
    """Gitee API交互工具包，继承自GitBaseToolkit提供统一接口。"""
    
    PLATFORM_NAME = "gitee"
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        instance_name: str = DEFAULT_GITEE_INSTANCE_NAME,
        namespace: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """初始化Gitee工具包。"""
        # 初始化参数
        self.instance_name = instance_name
        self.namespace = namespace
        
        # 调用父类初始化
        super().__init__(access_token=access_token, timeout=timeout)
    
    def _initialize_client(self):
        """初始化Gitee客户端，GitBaseToolkit的抽象方法实现"""
        # 如果提供了访问令牌，创建并注册实例配置
        if self.access_token:
            config = GiteeInstanceConfig(
                name=self.instance_name,
                url=DEFAULT_GITEE_URL,
                token=self.access_token,
                default_namespace=self.namespace
            )
            GiteeInstanceManager.register_instance(config)
    
    def _get_config(self) -> GiteeInstanceConfig:
        """获取当前实例的配置。"""
        return GiteeInstanceManager.get_instance(self.instance_name)
    
    def _make_request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送Gitee API请求。"""
        config = self._get_config()
        url = f"{config.url}{endpoint}"
        headers = config.get_headers()
        
        # 统一处理参数
        if params is None:
            params = {}
        
        # 处理命名空间
        if self.namespace and "owner" not in params and "namespace" not in params:
            if method in ["GET", "DELETE"]:
                params["owner"] = self.namespace
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                verify=config.verify_ssl,
                timeout=self.timeout
            )
            
            # 检查状态码
            if response.status_code == 403 and "rate limit" in response.text.lower():
                raise GiteeRateLimitError(f"Gitee API速率限制: {response.text}")
            
            if response.status_code == 401:
                raise GiteeAuthenticationError(f"Gitee认证失败: {response.text}")
            
            if response.status_code == 404:
                raise GiteeNotFoundError(f"Gitee资源不存在: {response.text}")
            
            if response.status_code >= 400:
                raise GiteeError(f"Gitee API错误 (状态码: {response.status_code}): {response.text}")
            
            # 尝试解析JSON响应
            try:
                return response.json()
            except ValueError:
                # 如果不是JSON响应，返回文本
                return {"text": response.text}
                
        except requests.exceptions.RequestException as e:
            raise GiteeError(f"Gitee API请求失败: {str(e)}") from e
    
    # GitBaseToolkit 实现的方法
    @GiteeInstanceManager.with_rate_limit_retry()
    def get_repository(self, repo_name: str) -> Dict[str, Any]:
        """获取Gitee仓库信息，实现GitBaseToolkit的抽象方法"""
        owner, name = self._parse_repo_name(repo_name)
        repo_path = f"{owner}/{name}"
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{repo_path}"
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def create_repository(self, repo_name: str, **kwargs) -> dict:
        """在Gitee上创建新仓库，实现GitBaseToolkit的抽象方法"""
        owner, name = self._parse_repo_name(repo_name)
        
        # 检查仓库是否存在
        if self.repository_exists(repo_name):
            raise ValueError(f"仓库 {repo_name} 已存在")
        
        # 创建仓库
        url = f"{self._get_config().url}/user/repos"
        data = {
            "name": name,
            "path": name,
            "description": kwargs.get("description", ""),
            "private": kwargs.get("private", False),
            "auto_init": kwargs.get("auto_init", False)
        }
        
        # 如果指定了组织/命名空间
        if owner != self._get_current_user():
            url = f"{self._get_config().url}/orgs/{owner}/repos"
        
        response = self._make_request(
            method="POST",
            endpoint="/user/repos",
            data=data
        )
        
        return {
            "name": response["full_name"],
            "url": response["html_url"],
            "clone_url": response["clone_url"]
        }
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def repository_exists(self, repo_name: str) -> bool:
        """检查Gitee仓库是否存在，实现GitBaseToolkit的抽象方法"""
        try:
            self.get_repository(repo_name)
            return True
        except (GiteeNotFoundError, GiteeError):
            return False
    
    def get_clone_url(self, repo_name: str, use_token: bool = True) -> str:
        """获取带认证信息的仓库克隆URL，实现GitBaseToolkit的抽象方法"""
        config = self._get_config()
        if use_token:
            return f"https://{config.token}@gitee.com/{repo_name}.git"
        return f"https://gitee.com/{repo_name}.git"
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def get_branches(self, repo_name: str) -> List[str]:
        """获取Gitee仓库的所有分支，实现GitBaseToolkit的抽象方法"""
        owner, name = self._parse_repo_name(repo_name)
        repo_path = f"{owner}/{name}"
        
        branches = self._make_request(
            method="GET",
            endpoint=f"/repos/{repo_path}/branches"
        )
        
        return [branch["name"] for branch in branches]
    
    def _parse_repo_name(self, repo_name: str) -> Tuple[str, str]:
        """解析仓库名为(owner, name)格式，重写GitBaseToolkit方法"""
        parts = repo_name.split('/')
        if len(parts) == 2:
            return parts[0], parts[1]
        return (self.namespace or self._get_default_owner()), repo_name
    
    def _get_default_owner(self) -> str:
        """获取默认的仓库拥有者，实现GitBaseToolkit的抽象方法"""
        # 尝试获取当前用户作为默认拥有者
        try:
            return self._get_current_user()
        except Exception:
            # 如果获取失败，使用命名空间或抛出异常
            if self.namespace:
                return self.namespace
            raise GiteeError("无法确定默认的仓库拥有者，请提供完整的仓库路径或命名空间")
    
    def _get_current_user(self) -> str:
        """获取当前登录用户"""
        response = self._make_request(
            method="GET",
            endpoint="/user"
        )
        return response["login"]
    
    def handle_rate_limit(self, func):
        """处理速率限制的装饰器，重写GitBaseToolkit方法"""
        return GiteeInstanceManager.with_rate_limit_retry()(func)
    
    # 原有GiteeToolkit方法
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_create_merge_request(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        title: str,
        source_branch: str,
        target_branch: str,
        description: Optional[str] = None,
        assignee_id: Optional[GiteeUserId] = None
    ) -> Dict[str, Any]:
        """在Gitee上创建合并请求。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        data = {
            "title": title,
            "head": source_branch,
            "base": target_branch,
        }
        
        if description:
            data["body"] = description
        if assignee_id:
            data["assignee_id"] = assignee_id
        
        return self._make_request(
            method="POST",
            endpoint=f"/repos/{project_param}/pulls",
            data=data
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_issue_list(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        state: Optional[Literal["open", "closed", "all"]] = "open",
        page: int = 1,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """获取Gitee项目的Issue列表。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        params = {
            "state": state,
            "page": page,
            "per_page": per_page
        }
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/issues",
            params=params
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_issue_content(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        issue_iid: GiteeIssueIid
    ) -> Dict[str, Any]:
        """获取Gitee Issue的详细内容。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/issues/{issue_iid}"
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_merge_request_list(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        state: Optional[Literal["open", "closed", "merged", "all"]] = "open",
        page: int = 1,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """获取Gitee项目的合并请求列表。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        params = {
            "state": state,
            "page": page,
            "per_page": per_page
        }
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/pulls",
            params=params
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_merge_request_content(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        mr_iid: GiteePullRequestIid
    ) -> Dict[str, Any]:
        """获取Gitee合并请求的详细内容。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/pulls/{mr_iid}"
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_retrieve_file_content(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        file_path: str,
        ref: Optional[str] = "master"
    ) -> Dict[str, Any]:
        """获取Gitee仓库中文件的内容。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        params = {
            "ref": ref
        }
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/contents/{file_path}",
            params=params
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_all_file_paths(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        path: str = "",
        ref: Optional[str] = "master"
    ) -> List[str]:
        """递归获取Gitee仓库中的所有文件路径。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        file_paths = []
        
        def _recursive_list(repo_path: str) -> None:
            """递归列出目录内容。"""
            params = {
                "ref": ref
            }
            
            contents = self._make_request(
                method="GET",
                endpoint=f"/repos/{project_param}/contents/{repo_path}",
                params=params
            )
            
            if not isinstance(contents, list):
                # 如果不是列表，可能是单个文件
                if isinstance(contents, dict) and contents.get("type") == "file":
                    file_paths.append(repo_path)
                return
            
            for item in contents:
                if item.get("type") == "file":
                    file_paths.append(item.get("path", ""))
                elif item.get("type") == "dir":
                    _recursive_list(item.get("path", ""))
        
        _recursive_list(path)
        return file_paths
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_branch_list(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier]
    ) -> List[Dict[str, Any]]:
        """获取Gitee仓库的分支列表。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/branches"
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_latest_commit(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        branch: Optional[str] = "master"
    ) -> Dict[str, Any]:
        """获取Gitee分支的最新提交。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}/commits/{branch}"
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_create_webhook(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier],
        url: str,
        events: List[str] = ["push", "pull_request", "issues"],
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """在Gitee项目上创建webhook。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        data = {
            "url": url,
            "events": events,
            "active": True
        }
        
        if secret:
            data["secret"] = secret
        
        return self._make_request(
            method="POST",
            endpoint=f"/repos/{project_param}/hooks",
            data=data
        )
    
    @GiteeInstanceManager.with_rate_limit_retry()
    def gitee_get_repository_info(
        self,
        project_id: Union[GiteeProjectId, GiteeProjectIdentifier]
    ) -> Dict[str, Any]:
        """获取Gitee仓库的信息。"""
        # 处理项目ID
        if isinstance(project_id, GiteeProjectIdentifier):
            project_param = project_id.value
        else:
            project_param = project_id
        
        return self._make_request(
            method="GET",
            endpoint=f"/repos/{project_param}"
        )
    
    def get_tools(self) -> List[FunctionTool]:
        """返回工具包中的所有工具。"""
        # 先获取GitBaseToolkit中的基础工具
        tools = super().get_tools()
        
        # 添加Gitee特定的工具
        tools.extend([
            FunctionTool(
                func=self.gitee_create_merge_request,
                name="gitee_create_merge_request",
                description="在Gitee上创建合并请求",
            ),
            FunctionTool(
                func=self.gitee_get_issue_list,
                name="gitee_get_issue_list",
                description="获取Gitee项目的Issue列表",
            ),
            FunctionTool(
                func=self.gitee_get_issue_content,
                name="gitee_get_issue_content",
                description="获取Gitee Issue的详细内容",
            ),
            FunctionTool(
                func=self.gitee_get_merge_request_list,
                name="gitee_get_merge_request_list",
                description="获取Gitee项目的合并请求列表",
            ),
            FunctionTool(
                func=self.gitee_get_merge_request_content,
                name="gitee_get_merge_request_content",
                description="获取Gitee合并请求的详细内容",
            ),
            FunctionTool(
                func=self.gitee_retrieve_file_content,
                name="gitee_retrieve_file_content",
                description="获取Gitee仓库中文件的内容",
            ),
            FunctionTool(
                func=self.gitee_get_all_file_paths,
                name="gitee_get_all_file_paths",
                description="递归获取Gitee仓库中的所有文件路径",
            ),
            FunctionTool(
                func=self.gitee_get_branch_list,
                name="gitee_get_branch_list",
                description="获取Gitee仓库的分支列表",
            ),
            FunctionTool(
                func=self.gitee_get_latest_commit,
                name="gitee_get_latest_commit",
                description="获取Gitee分支的最新提交",
            ),
            FunctionTool(
                func=self.gitee_create_webhook,
                name="gitee_create_webhook",
                description="在Gitee项目上创建webhook",
            ),
            FunctionTool(
                func=self.gitee_get_repository_info,
                name="gitee_get_repository_info",
                description="获取Gitee仓库的信息",
            ),
        ])
        
        return tools