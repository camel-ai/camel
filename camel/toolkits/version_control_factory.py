from typing import Dict, List, Optional, Any, Union
import logging
from camel.toolkits.version_control_base_toolkit import VersionControlBaseToolkit
from camel.toolkits.github_toolkit import GithubToolkit
from camel.toolkits.gitee_toolkit import GiteeToolkit
from camel.toolkits.gitlab_toolkit import GitLabToolkit
from camel.toolkits.svn_toolkit import SVNToolkit
from camel.types.version_control import GitPlatformType, VersionControlError, AuthenticationError, OperationFailedError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VersionControlFactory:
    """
    版本控制系统工具包工厂类
    
    提供创建和管理各种版本控制系统工具包实例的功能，确保单例模式，
    避免重复初始化，并提供统一的接口来访问不同平台的工具包。
    """
    
    # 存储工具包实例的字典
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_github_toolkit(cls, access_token: Optional[str] = None) -> VersionControlBaseToolkit:
        """
        获取GitHub工具包实例
        
        Args:
            access_token: GitHub访问令牌，如果为None则从环境变量获取
            
        Returns:
            VersionControlBaseToolkit: GitHub工具包实例
            
        Raises:
            AuthenticationError: 如果认证失败
            OperationFailedError: 如果工具包初始化失败
        """
        key = "github"
        if key not in cls._instances:
            try:
                logger.info("创建GitHubToolkit实例")
                cls._instances[key] = GithubToolkit(access_token=access_token)
                logger.info("成功初始化GitHub工具包")
            except AuthenticationError:
                logger.error("GitHub工具包认证失败")
                raise
            except Exception as e:
                logger.error(f"初始化GitHub工具包失败: {str(e)}")
                raise OperationFailedError(f"初始化GitHub工具包失败: {str(e)}")
        return cls._instances[key]
    
    @classmethod
    def get_gitlab_toolkit(cls, access_token: Optional[str] = None, base_url: Optional[str] = None) -> VersionControlBaseToolkit:
        """
        获取GitLab工具包实例
        
        Args:
            access_token: GitLab访问令牌，如果为None则从环境变量获取
            base_url: GitLab服务器URL，如果为None则使用官方GitLab
            
        Returns:
            VersionControlBaseToolkit: GitLab工具包实例
            
        Raises:
            AuthenticationError: 如果认证失败
            OperationFailedError: 如果工具包初始化失败
        """
        key = f"gitlab_{base_url or 'official'}"
        if key not in cls._instances:
            try:
                logger.info(f"创建GitLabToolkit实例 (base_url={base_url})")
                cls._instances[key] = GitLabToolkit(access_token=access_token, base_url=base_url)
                logger.info("成功初始化GitLab工具包")
            except AuthenticationError:
                logger.error("GitLab工具包认证失败")
                raise
            except Exception as e:
                logger.error(f"初始化GitLab工具包失败: {str(e)}")
                raise OperationFailedError(f"初始化GitLab工具包失败: {str(e)}")
        return cls._instances[key]
    
    @classmethod
    def get_gitee_toolkit(cls, access_token: Optional[str] = None) -> VersionControlBaseToolkit:
        """
        获取Gitee工具包实例
        
        Args:
            access_token: Gitee访问令牌，如果为None则从环境变量获取
            
        Returns:
            VersionControlBaseToolkit: Gitee工具包实例
            
        Raises:
            AuthenticationError: 如果认证失败
            OperationFailedError: 如果工具包初始化失败
        """
        key = "gitee"
        if key not in cls._instances:
            try:
                logger.info("创建GiteeToolkit实例")
                cls._instances[key] = GiteeToolkit(access_token=access_token)
                logger.info("成功初始化Gitee工具包")
            except AuthenticationError:
                logger.error("Gitee工具包认证失败")
                raise
            except Exception as e:
                logger.error(f"初始化Gitee工具包失败: {str(e)}")
                raise OperationFailedError(f"初始化Gitee工具包失败: {str(e)}")
        return cls._instances[key]
    
    @classmethod
    def get_svn_toolkit(cls, username: Optional[str] = None, password: Optional[str] = None) -> VersionControlBaseToolkit:
        """
        获取SVN工具包实例
        
        Args:
            username: SVN用户名，如果为None则从环境变量获取
            password: SVN密码，如果为None则从环境变量获取
            
        Returns:
            VersionControlBaseToolkit: SVN工具包实例
            
        Raises:
            AuthenticationError: 如果认证失败
            OperationFailedError: 如果工具包初始化失败
        """
        key = "svn"
        if key not in cls._instances:
            try:
                logger.info("创建SVNToolkit实例")
                cls._instances[key] = SVNToolkit(username=username, password=password)
                logger.info("成功初始化SVN工具包")
            except AuthenticationError:
                logger.error("SVN工具包认证失败")
                raise
            except Exception as e:
                logger.error(f"初始化SVN工具包失败: {str(e)}")
                raise OperationFailedError(f"初始化SVN工具包失败: {str(e)}")
        return cls._instances[key]
    
    @classmethod
    def get_toolkit_by_platform(cls, platform: Union[str, GitPlatformType], **kwargs) -> VersionControlBaseToolkit:
        """
        根据平台名称获取对应的工具包实例
        
        Args:
            platform: 平台名称或GitPlatformType枚举值，可选值：github, gitlab, gitee, svn
            **kwargs: 传递给具体工具包的参数
            
        Returns:
            对应的版本控制工具包实例
            
        Raises:
            OperationFailedError: 如果指定的平台不支持或工具包初始化失败
            ImportError: 如果所需的工具包未安装
        """
        if isinstance(platform, GitPlatformType):
            platform_name = platform.value
        else:
            platform_name = str(platform).lower()
        
        try:
            if platform_name == "github":
                return cls.get_github_toolkit(**kwargs)
            elif platform_name == "gitlab":
                return cls.get_gitlab_toolkit(**kwargs)
            elif platform_name == "gitee":
                return cls.get_gitee_toolkit(**kwargs)
            elif platform_name == "svn":
                return cls.get_svn_toolkit(**kwargs)
            else:
                raise OperationFailedError(
                    f"不支持的版本控制平台: {platform_name}",
                    platform=platform_name
                )
        except ImportError as e:
            logger.error(f"导入工具包失败: {str(e)}")
            raise ImportError(f"无法导入{platform_name}工具包: {str(e)}")
        except Exception as e:
            logger.error(f"初始化{platform_name}工具包失败: {str(e)}")
            raise OperationFailedError(
                f"创建{platform_name}工具包实例失败: {str(e)}",
                platform=platform_name
            )
    
    @classmethod
    def clear_cache(cls, platform: Optional[str] = None) -> None:
        """
        清除工具包实例缓存
        
        Args:
            platform: 要清除的平台，如果为None则清除所有平台
            
        Raises:
            OperationFailedError: 如果缓存清除过程中发生错误
        """
        try:
            if platform:
                platform = platform.lower()
                # 处理GitLab的特殊情况
                if platform == "gitlab":
                    keys_before = len(cls._instances)
                    cls._instances = {k: v for k, v in cls._instances.items() if not k.startswith("gitlab_")}
                    keys_removed = keys_before - len(cls._instances)
                    logger.info(f"清除GitLab工具包缓存，移除了{keys_removed}个实例")
                else:
                    keys_to_remove = [k for k in cls._instances.keys() if k == platform]
                    for key in keys_to_remove:
                        del cls._instances[key]
                    logger.info(f"清除{platform}工具包缓存，移除了{len(keys_to_remove)}个实例")
            else:
                # 清除所有平台的缓存
                instance_count = len(cls._instances)
                cls._instances.clear()
                logger.info(f"清除所有工具包缓存，移除了{instance_count}个实例")
        except Exception as e:
            logger.error(f"清除工具包缓存失败: {str(e)}")
            raise OperationFailedError(f"清除工具包缓存失败: {str(e)}")
    
    @classmethod
    def get_available_platforms(cls) -> List[str]:
        """
        获取所有可用的版本控制平台列表
        
        Returns:
            List[str]: 可用的平台名称列表
        """
        platforms = []
        try:
            # 尝试导入各个平台的工具包，能成功导入则说明支持该平台
            from camel.toolkits.github_toolkit import GithubToolkit
            platforms.append("github")
        except ImportError:
            pass
        
        try:
            from camel.toolkits.gitee_toolkit import GiteeToolkit
            platforms.append("gitee")
        except ImportError:
            pass
        
        try:
            from camel.toolkits.gitlab_toolkit import GitLabToolkit
            platforms.append("gitlab")
        except ImportError:
            pass
        
        try:
            from camel.toolkits.svn_toolkit import SVNToolkit
            platforms.append("svn")
        except ImportError:
            pass
        
        return platforms