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
import logging
from typing import Dict, List, Optional, Tuple, Any, TypeVar, Generic, overload
from functools import wraps

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit

logger = get_logger(__name__)

# 定义Git相关的强类型
RepoName: TypeVar = str
BranchName: TypeVar = str

class GitBaseToolkit(BaseToolkit):
    """Git平台工具包的抽象基类，定义统一的接口
    
    为不同Git平台（如GitHub、Gitee、GitLab）提供统一的接口，使上层应用可以通过一致的方式
    与不同的Git平台进行交互，而不需要关心具体平台的实现细节。
    """
    
    # 平台名称，由子类实现
    PLATFORM_NAME: str = "generic"
    
    def __init__(self, access_token: Optional[str] = None, timeout: Optional[float] = None):
        """初始化Git工具包
        
        Args:
            access_token: 访问平台API所需的令牌，如果不提供，将尝试从环境变量获取
            timeout: API请求的超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self.access_token = access_token
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化平台客户端
        
        由子类实现，用于创建与特定Git平台通信的客户端实例
        """
        raise NotImplementedError("子类必须实现_initialize_client方法")
    
    def get_repository(self, repo_name: str) -> Any:
        """获取仓库对象
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或简单的仓库名
            
        Returns:
            仓库对象，具体类型由子类实现决定
            
        Raises:
            Exception: 当仓库不存在或访问失败时
        """
        raise NotImplementedError("子类必须实现get_repository方法")
    
    def create_repository(self, repo_name: str, **kwargs) -> dict:
        """创建新仓库
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或简单的仓库名
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
            Exception: 当仓库已存在或创建失败时
        """
        raise NotImplementedError("子类必须实现create_repository方法")
    
    def repository_exists(self, repo_name: str) -> bool:
        """检查仓库是否存在
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或简单的仓库名
            
        Returns:
            仓库存在返回True，否则返回False
        """
        raise NotImplementedError("子类必须实现repository_exists方法")
    
    def get_clone_url(self, repo_name: str, use_token: bool = True) -> str:
        """获取仓库克隆URL
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或简单的仓库名
            use_token: 是否在URL中包含认证令牌
            
        Returns:
            可用于克隆仓库的URL
        """
        raise NotImplementedError("子类必须实现get_clone_url方法")
    
    def get_branches(self, repo_name: str) -> List[str]:
        """获取仓库分支列表
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或简单的仓库名
            
        Returns:
            仓库所有分支名称的列表
        """
        raise NotImplementedError("子类必须实现get_branches方法")
    
    def list_repositories(self, **kwargs) -> List[dict]:
        """列出用户或组织的仓库
        
        Args:
            **kwargs: 其他可能的参数
                - owner: 所有者名称（用户或组织）
                - per_page: 每页返回的仓库数量
                - page: 页码
                - ...
                
        Returns:
            List[dict]: 仓库信息列表
        """
        raise NotImplementedError("子类必须实现list_repositories方法")
    
    def handle_rate_limit(self, func):
        """处理速率限制的装饰器基类实现
        
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
    
    def _parse_repo_name(self, repo_name: str) -> Tuple[str, str]:
        """解析仓库名为(owner, name)格式
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或简单的仓库名
            
        Returns:
            (owner, repo_name)元组
        """
        parts = repo_name.split('/')
        if len(parts) == 2:
            return parts[0], parts[1]
        # 默认实现，需要子类根据实际情况重写
        return self._get_default_owner(), repo_name
    
    def _get_default_owner(self) -> str:
        """获取默认的仓库拥有者
        
        由子类实现，用于确定当只提供仓库名而不提供拥有者时的默认拥有者
        
        Returns:
            默认拥有者名称
        """
        raise NotImplementedError("子类必须实现_get_default_owner方法")
    
    def _test_credentials(self) -> bool:
        """测试凭证是否有效
        
        由子类实现，用于验证访问令牌是否有效
        
        Returns:
            bool: 如果凭证有效则返回True，否则返回False
        """
        raise NotImplementedError("子类必须实现_test_credentials方法")
    
    def get_platform_name(self) -> str:
        """获取平台名称
        
        Returns:
            平台名称字符串
        """
        return self.PLATFORM_NAME
    
    def get_tools(self):
        """获取工具列表
        
        Returns:
            List[FunctionTool]: 工具列表
        """
        # 基础Git工具将由子类实现
        return []