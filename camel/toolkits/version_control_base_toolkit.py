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
提供所有版本控制系统工具包的统一抽象基类，定义通用接口和行为。
适用于Git（GitHub、GitLab、Gitee）和SVN等不同版本控制系统的统一操作规范。
"""

import logging
from abc import abstractmethod
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from datetime import datetime

from camel.toolkits.base import BaseToolkit
from camel.types.version_control import VersionControlError



class VersionControlBaseToolkit(BaseToolkit):
    """
    版本控制系统基础工具包抽象基类
    
    为所有版本控制工具包提供统一的接口规范，包括仓库操作、文件管理、
    凭证处理等核心功能。适用于Git和SVN等不同类型的版本控制系统。
    """
    
    # 平台名称常量，由子类定义
    PLATFORM_NAME: str = "version_control"
    
    def __init__(self, timeout: Optional[float] = None) -> None:
        """
        初始化版本控制基础工具包
        
        Args:
            timeout: 操作超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self._session_start_time = datetime.now()
    
    @abstractmethod
    def get_repository_info(self, repository_path: str) -> Dict[str, Any]:
        """
        获取仓库信息
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            Dict[str, Any]: 包含仓库信息的字典
        """
        pass
    
    @abstractmethod
    def is_repository_exist(self, repository_path: str) -> bool:
        """
        检查仓库是否存在
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            bool: 仓库是否存在
        """
        pass
    
    @abstractmethod
    def create_repository(self, repository_path: str, **kwargs) -> bool:
        """
        创建新仓库
        
        Args:
            repository_path: 仓库路径或标识符
            **kwargs: 其他创建参数
            
        Returns:
            bool: 创建是否成功
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_branches_or_tags(self, repository_path: str) -> List[str]:
        """
        获取仓库的分支或标签列表
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            List[str]: 分支或标签名称列表
        """
        pass
    
    @abstractmethod
    def get_latest_commit_info(self, repository_path: str) -> Dict[str, Any]:
        """
        获取最新提交信息
        
        Args:
            repository_path: 仓库路径或标识符
            
        Returns:
            Dict[str, Any]: 包含提交信息的字典
        """
        pass
    
    @abstractmethod
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
        pass
    
    def format_path(self, path: str) -> str:
        """
        格式化路径，处理不同操作系统和平台的路径差异
        
        Args:
            path: 原始路径
            
        Returns:
            str: 格式化后的路径
        """
        # 默认实现，子类可以覆盖
        return path
    
    def validate_credentials(self) -> bool:
        """
        验证凭证是否有效
        
        Returns:
            bool: 凭证是否有效
        """
        # 默认实现返回True，子类应该提供具体实现
        return True
    
    def get_platform_name(self) -> str:
        """
        获取平台名称
        
        Returns:
            str: 平台名称
        """
        return self.PLATFORM_NAME
    
    def _handle_error(self, error: Exception, method_name: str = None) -> Dict[str, Any]:
        """
        统一错误处理方法
        
        Args:
            error: 异常对象
            method_name: 发生错误的方法名
            
        Returns:
            Dict[str, Any]: 统一格式的错误信息
        """
        error_info = {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat(),
            "platform": self.PLATFORM_NAME
        }
        
        if method_name:
            error_info["method"] = method_name
            self.logger.error(f"方法 {method_name} 执行失败: {str(error)}")
        else:
            self.logger.error(f"操作失败: {str(error)}")
        
        return error_info
    
    def _ensure_tool_available(self) -> bool:
        """
        确保版本控制工具可用
        
        Returns:
            bool: 工具是否可用
        """
        # 基础实现，子类可以覆盖
        return True
    
    def get_toolkit_info(self) -> Dict[str, Any]:
        """
        获取工具包信息
        
        Returns:
            Dict[str, Any]: 包含工具包信息的字典
        """
        return {
            "platform": self.PLATFORM_NAME,
            "version": getattr(self, "__version__", "unknown"),
            "initialized_at": self._session_start_time.isoformat() if hasattr(self, "_session_start_time") else None,
            "timeout": getattr(self, "timeout", None)
        }