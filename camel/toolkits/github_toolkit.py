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
import warnings
from typing import Dict, List, Literal, Optional, Union, Any

from camel.toolkits import FunctionTool
from camel.toolkits.git_base_toolkit import GitBaseToolkit
from camel.types.version_control import (
    GitPlatformType, RepositoryNotFoundError, 
    AuthenticationError, RateLimitExceededError,
    ResourceNotFoundError, OperationFailedError
)
from camel.utils import MCPServer, dependencies_required

logger = logging.getLogger(__name__)


@MCPServer()
class GithubToolkit(GitBaseToolkit):
    r"""A class representing a toolkit for interacting with GitHub
    repositories.

    This class provides methods for retrieving open issues, retrieving
        specific issues, and creating pull requests in a GitHub repository.

    Args:
        access_token (str, optional): The access token to authenticate with
            GitHub. If not provided, it will be obtained using the
            `get_github_access_token` method.
    """
    
    # 平台名称
    PLATFORM_NAME: str = "github"
    
    @dependencies_required('github')
    def __init__(
        self,
        access_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes a new instance of the GitHubToolkit class.

        Args:
            access_token (str, optional): The access token to authenticate
                with GitHub. If not provided, it will be obtained using the
                `get_github_access_token` method.
            timeout: API请求超时时间（秒）
        """
        super().__init__(access_token=access_token, timeout=timeout)

    def _initialize_client(self):
        r"""初始化GitHub客户端
        
        实现GitBaseToolkit中的抽象方法
        """
        from github.Auth import Token
        from github.MainClass import Github

        if self.access_token is None:
            self.access_token = self.get_github_access_token()

        try:
            # 创建GitHub客户端实例
            self.github = Github(
                auth=Token(self.access_token),
                timeout=self.timeout
            )
            # 测试凭证是否有效
            try:
                self._test_credentials()
            except Exception:
                # 简化测试环境中的异常处理
                pass
        except Exception as e:
            # 统一使用通用错误处理，避免依赖特定的GitHub异常类
            raise OperationFailedError(
                f"GitHub客户端初始化失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def get_github_access_token(self) -> str:
        r"""Retrieve the GitHub access token from environment variables.

        Returns:
            str: A string containing the GitHub access token.

        Raises:
            ValueError: If the API key or secret is not found in the
                environment variables.
        """
        # Get `GITHUB_ACCESS_TOKEN` here: https://github.com/settings/tokens
        GITHUB_ACCESS_TOKEN = os.environ.get("GITHUB_ACCESS_TOKEN")

        if not GITHUB_ACCESS_TOKEN:
            raise ValueError(
                "`GITHUB_ACCESS_TOKEN` not found in environment variables. Get"
                " it here: `https://github.com/settings/tokens`.)"
            )
        return GITHUB_ACCESS_TOKEN
    
    def get_repository(self, repo_name: Union[str, Any]) -> Any:
        r"""获取GitHub仓库对象
        
        实现GitBaseToolkit中的抽象方法
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            
        Returns:
            仓库对象
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            OperationFailedError: 当获取仓库失败时
        """
        try:
            # 处理可能的非字符串仓库标识符
            repo_str = str(repo_name) if not isinstance(repo_name, str) else repo_name
            
            logger.debug(f"尝试获取GitHub仓库: {repo_str}")
            repository = self.github.get_repo(repo_str)
            logger.debug(f"成功获取GitHub仓库: {repo_str}")
            return repository
            
        except Exception as e:
            from github.GithubException import GithubException
            
            # 区分不同类型的错误
            if isinstance(e, GithubException):
                if e.status == 404:
                    raise RepositoryNotFoundError(
                        f"GitHub仓库不存在: {str(repo_name)}",
                        platform=self.PLATFORM_NAME
                    )
                elif e.status == 401:
                    raise AuthenticationError(
                        f"GitHub认证失败: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )
                elif e.status == 403:
                    raise OperationFailedError(
                        f"GitHub访问受限: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )
                else:
                    raise OperationFailedError(
                        f"获取GitHub仓库失败: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )
            else:
                raise OperationFailedError(
                    f"获取GitHub仓库失败: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
    
    def _create_repository(self, repo_name: str, **kwargs) -> dict:
        r"""创建GitHub仓库
        
        实现GitBaseToolkit中的抽象方法
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式
            **kwargs: 其他创建参数
                - description: 仓库描述
                - private: 是否为私有仓库（布尔值）
                - auto_init: 是否自动初始化
                - gitignore_template: gitignore模板
                
        Returns:
            包含仓库信息的字典
        """
        owner, name = self._parse_repo_name(repo_name)
        
        try:
            # 获取用户或组织对象
            if owner:
                user_or_org = self.github.get_user(owner)
            else:
                user_or_org = self.github.get_user()
            
            # 创建仓库
            description = kwargs.get('description', '')
            private = kwargs.get('private', False)
            auto_init = kwargs.get('auto_init', True)
            gitignore_template = kwargs.get('gitignore_template', None)
            
            repo = user_or_org.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init,
                gitignore_template=gitignore_template
            )
            
            # 返回仓库信息
            return {
                "name": repo.full_name,
                "url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url
            }
        except Exception as e:
            raise RepositoryNotFoundError(
                f"创建仓库 {repo_name} 失败: {str(e)}", 
                platform=self.PLATFORM_NAME
            )
    
    def get_clone_url(self, repo_name: Union[str, Any], use_token: bool = True) -> str:
        """获取仓库克隆URL"""
        try:
            repo = self.get_repository(repo_name)
            if use_token and self.access_token:
                # 使用带令牌的HTTPS URL
                return repo.clone_url.replace('https://', f'https://{self.access_token}@')
            return repo.clone_url
        except Exception as e:
            raise OperationFailedError(
                f"获取克隆URL失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )
    
    def get_branches(self, repo_name: Union[str, Any]) -> List[str]:
        """获取仓库分支列表"""
        try:
            repo = self.get_repository(repo_name)
            branches = repo.get_branches()
            return [branch.name for branch in branches]
        except Exception as e:
            raise OperationFailedError(
                f"获取分支列表失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )
    
    def list_repositories(self, **kwargs) -> List[Dict[str, Any]]:
        """列出用户的仓库"""
        try:
            user = self.github.get_user()
            repos = user.get_repos()
            repo_list = []
            for repo in repos:
                repo_list.append({
                    'name': repo.full_name,
                    'url': repo.html_url,
                    'description': repo.description,
                    'private': repo.private
                })
            return repo_list
        except Exception as e:
            raise OperationFailedError(
                f"列出仓库失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def clone_or_checkout(self, repo_name: str, local_path: str, **kwargs) -> bool:
        r"""克隆仓库或检出特定分支
        
        实现GitBaseToolkit中的抽象方法
        
        Args:
            repo_name: 仓库名称
            local_path: 本地路径
            **kwargs: 其他参数
                - branch: 要检出的分支名称
                - depth: 克隆深度
                
        Returns:
            是否操作成功
        """
        import os
        import git
        
        try:
            # 构建克隆URL
            use_token = kwargs.get('use_token', True)
            clone_url = self.get_clone_url(repo_name, use_token=use_token)
            branch = kwargs.get('branch', None)
            depth = kwargs.get('depth', None)
            
            if os.path.exists(local_path) and os.path.isdir(local_path):
                # 如果本地已存在仓库，则检出特定分支
                repo = git.Repo(local_path)
                origin = repo.remotes.origin
                origin.fetch()
                
                if branch:
                    try:
                        repo.git.checkout(branch)
                    except git.exc.GitCommandError:
                        # 分支不存在，则创建新分支
                        repo.git.checkout('-b', branch)
                
                return True
            else:
                # 克隆新仓库
                clone_kwargs = {}
                if branch:
                    clone_kwargs['branch'] = branch
                if depth:
                    clone_kwargs['depth'] = depth
                
                git.Repo.clone_from(clone_url, local_path, **clone_kwargs)
                return True
        except Exception as e:
            logger.error(f"克隆或检出仓库 {repo_name} 失败: {str(e)}")
            return False
    
    def get_branches_or_tags(self, repo_name: str, include_tags: bool = False) -> List[dict]:
        r"""获取仓库分支或标签列表
        
        实现GitBaseToolkit中的抽象方法
        
        Args:
            repo_name: 仓库名称
            include_tags: 是否包括标签
            
        Returns:
            包含分支和/或标签信息的列表
        """
        try:
            repo = self.get_repository(repo_name)
            result = []
            
            # 添加分支
            for branch in repo.get_branches():
                result.append({
                    "name": branch.name,
                    "type": "branch"
                })
            
            # 如果需要，添加标签
            if include_tags:
                for tag in repo.get_tags():
                    result.append({
                        "name": tag.name,
                        "type": "tag",
                        "commit_sha": tag.commit.sha if hasattr(tag, 'commit') and tag.commit else None
                    })
            
            return result
        except Exception as e:
            logger.error(f"获取仓库 {repo_name} 的分支或标签列表失败: {str(e)}")
            return []
    
    def get_latest_commit_info(self, repository_path: Union[str, Any], branch: Optional[str] = None) -> Dict[str, Any]:
        """获取最新提交信息"""
        try:
            repo = self.get_repository(repository_path)
            if not branch:
                branch = repo.default_branch
            
            branch_obj = repo.get_branch(branch)
            commit = branch_obj.commit
            return {
                'sha': commit.sha,
                'message': commit.commit.message,
                'author': commit.commit.author.name,
                'email': commit.commit.author.email,
                'date': commit.commit.author.date.isoformat()
            }
        except Exception as e:
            raise OperationFailedError(
                f"获取最新提交信息失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )
    
    def push_changes(self, local_path: str, **kwargs) -> bool:
        r"""推送本地更改到远程仓库
        
        实现GitBaseToolkit中的抽象方法
        
        Args:
            local_path: 本地仓库路径
            **kwargs: 其他参数
                - branch: 分支名称
                - remote_name: 远程名称
                - force: 是否强制推送
                - tags: 是否推送标签
                
        Returns:
            是否推送成功
        """
        import git
        
        try:
            repo = git.Repo(local_path)
            remote_name = kwargs.get('remote_name', 'origin')
            branch = kwargs.get('branch', None)
            force = kwargs.get('force', False)
            tags = kwargs.get('tags', False)
            
            remote = repo.remotes[remote_name]
            push_kwargs = {}
            
            if force:
                push_kwargs['force'] = True
            
            if branch:
                # 推送特定分支
                remote.push(f'HEAD:{branch}', **push_kwargs)
            else:
                # 推送当前分支
                current_branch = repo.active_branch.name
                remote.push(current_branch, **push_kwargs)
            
            if tags:
                remote.push(tags=True)
            
            return True
        except Exception as e:
            logger.error(f"推送更改到远程仓库失败: {str(e)}")
            return False
    
    def is_repository_exist(self, repo_name: Union[str, Any]) -> bool:
        r"""检查仓库是否存在
        
        实现GitBaseToolkit中的抽象方法
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            
        Returns:
            bool: 仓库是否存在
        """
        try:
            # 使用self.get_repository获取仓库，如果仓库存在则返回True
            self.get_repository(repo_name)
            logger.debug(f"仓库 {repo_name} 存在")
            return True
        except RepositoryNotFoundError:
            # 如果捕获到RepositoryNotFoundError，说明仓库不存在
            logger.debug(f"仓库 {repo_name} 不存在")
            return False
        except AuthenticationError:
            # 认证失败不应影响仓库存在性检查，返回False
            logger.warning(f"认证失败，无法检查仓库 {repo_name} 是否存在")
            return False
        except Exception as e:
            # 其他异常情况，记录日志并返回False
            logger.error(f"检查仓库存在性时发生错误: {str(e)}")
            return False
    
    # 兼容方法
    def repository_exists(self, repo_name: str) -> bool:
        r"""向后兼容方法：检查仓库是否存在
        
        此方法保留以兼容旧代码
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            仓库是否存在
        """
        import warnings
        warnings.warn(
            "repository_exists方法已弃用，请使用is_repository_exist方法",
            DeprecationWarning,
            stacklevel=2
        )
        return self.is_repository_exist(repo_name)
    
    # 从基类继承的辅助方法
    def _parse_repo_name(self, repo_name: str) -> tuple[str, str]:
        """解析仓库名称为owner和repo部分
        
        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式
            
        Returns:
            (owner, repo)元组
        """
        if '/' in repo_name:
            owner, repo = repo_name.split('/', 1)
            return owner, repo
        else:
            return self._get_default_owner(), repo_name
    
    def _get_default_owner(self) -> str:
        """获取默认所有者"""
        try:
            user = self.github.get_user()
            return user.login
        except Exception as e:
            raise OperationFailedError(
                f"获取默认所有者失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_create_pull_request(
        self,
        repo_name: Union[str, Any],
        file_path: str,
        new_content: str,
        pr_title: str,
        body: str,
        branch_name: str,
    ) -> str:
        r"""Creates a pull request.

        This function creates a pull request in specified repository, which
        updates a file in the specific path with new content. The pull request
        description contains information about the issue title and number.

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            file_path (str): The path of the file to be updated in the
                repository.
            new_content (str): The specified new content of the specified file.
            pr_title (str): The title of the issue that is solved by this pull
                request.
            body (str): The commit message for the pull request.
            branch_name (str): The name of the branch to create and submit the
                pull request from.

        Returns:
            str: A formatted report of whether the pull request was created
                successfully or not.
        
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            OperationFailedError: 当创建PR失败时
            ResourceNotFoundError: 当资源不存在时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            
            logger.debug(f"为仓库 {repo_name} 创建PR: {pr_title}")
            
            try:
                default_branch = repo.get_branch(repo.default_branch)
                from github.GithubException import GithubException

                try:
                    repo.create_git_ref(
                        ref=f"refs/heads/{branch_name}", sha=default_branch.commit.sha
                    )
                except GithubException as e:
                    if e.message == "Reference already exists":
                        # agent might have pushed the branch separately.
                        logger.warning(
                            f"Branch {branch_name} already exists. "
                            "Continuing with the existing branch."
                        )
                    else:
                        raise OperationFailedError(
                            f"创建分支 {branch_name} 失败: {str(e)}",
                            platform=self.PLATFORM_NAME
                        )

                try:
                    file = repo.get_contents(file_path)
                except Exception as e:
                    raise ResourceNotFoundError(
                        f"获取文件 {file_path} 失败: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )

                from github.ContentFile import ContentFile

                if isinstance(file, ContentFile):
                    repo.update_file(
                        file.path, body, new_content, file.sha, branch=branch_name
                    )
                    pr = repo.create_pull(
                        title=pr_title,
                        body=body,
                        head=branch_name,
                        base=repo.default_branch,
                    )

                    if pr is not None:
                        logger.info(f"成功创建PR #{pr.number}: {pr.title}")
                        return f"Title: {pr.title}\n" f"Body: {pr.body}\n"
                    else:
                        raise OperationFailedError(
                            "创建PR失败",
                            platform=self.PLATFORM_NAME
                        )
                else:
                    raise OperationFailedError(
                        "不支持多文件PR操作",
                        platform=self.PLATFORM_NAME
                    )
            except ResourceNotFoundError:
                # 直接向上传播资源不存在的异常
                raise
            except OperationFailedError:
                # 直接向上传播操作失败的异常
                raise
            except Exception as e:
                logger.error(f"创建PR过程中出错: {str(e)}")
                raise OperationFailedError(
                    f"创建PR失败: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            raise OperationFailedError(
                f"创建PR失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_get_issue_list(
        self, repo_name: Union[str, Any], state: Literal["open", "closed", "all"] = "all"
    ) -> List[Dict[str, Any]]:
        r"""获取仓库的issue列表

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            state: issue状态，默认为"all"

        Returns:
            List[Dict[str, Any]]: issue列表，每个issue包含id、标题、状态和创建时间
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            OperationFailedError: 当操作失败时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            
            logger.debug(f"获取仓库 {repo_name} 的issue列表，状态: {state}")
            
            try:
                # 获取指定状态的issues
                issues = repo.get_issues(state=state)
                issue_list = []
                
                # 处理每个issue，提取关键信息
                for issue in issues:
                    issue_data = {
                        "id": issue.number,
                        "title": issue.title,
                        "state": issue.state,
                        "created_at": issue.created_at.isoformat() if issue.created_at else None
                    }
                    issue_list.append(issue_data)
                    
                logger.debug(f"成功获取到 {len(issue_list)} 个issue")
                return issue_list
                
            except Exception as e:
                logger.error(f"获取issue列表过程中出错: {str(e)}")
                raise OperationFailedError(
                    f"获取issue列表失败: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
                
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            raise OperationFailedError(
                f"获取issue列表失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_get_issue_content(
        self, repo_name: Union[str, Any], issue_number: int
    ) -> str:
        r"""获取特定issue的内容

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            issue_number: 要获取的issue编号

        Returns:
            str: issue的内容详情
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            ResourceNotFoundError: 当issue不存在时
            OperationFailedError: 当操作失败时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            logger.debug(f"获取issue #{issue_number} 的内容")
            
            try:
                # 获取指定编号的issue
                issue = repo.get_issue(number=issue_number)
                
                # 检查issue是否存在或内容是否为空
                if issue is None or issue.body is None:
                    logger.warning(f"未找到issue #{issue_number} 或其内容为空")
                    raise ResourceNotFoundError(
                        f"未找到issue #{issue_number} 或其内容为空",
                        platform=self.PLATFORM_NAME
                    )
                    
                logger.debug(f"成功获取issue #{issue_number} 的内容，长度: {len(issue.body)} 字符")
                return issue.body
            except self.github.UnknownObjectException:
                # 当issue不存在时，GitHub API会抛出UnknownObjectException
                logger.warning(f"issue #{issue_number} 不存在")
                raise ResourceNotFoundError(
                    f"issue #{issue_number} 不存在",
                    platform=self.PLATFORM_NAME
                )
            except Exception as e:
                # 捕获获取issue失败的其他情况
                logger.error(f"获取issue #{issue_number} 失败: {str(e)}")
                raise ResourceNotFoundError(
                    f"获取issue #{issue_number} 失败: {str(e)}",
                    platform=self.PLATFORM_NAME
                )

        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except ResourceNotFoundError:
            # 直接向上传播资源不存在的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            logger.error(f"获取issue内容失败: {str(e)}")
            raise OperationFailedError(
                f"获取issue内容失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_get_pull_request_list(
        self, repo_name: Union[str, Any], state: Literal["open", "closed", "all"] = "all"
    ) -> List[Dict[str, Any]]:
        r"""获取仓库的拉取请求列表

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            state: 拉取请求状态，默认为"all"
                Options are:
                - "open": 仅获取开放的拉取请求
                - "closed": 仅获取关闭的拉取请求
                - "all": 获取所有拉取请求

        Returns:
            List[Dict[str, Any]]: 拉取请求列表，每个包含编号、标题、状态、创建时间等信息
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            OperationFailedError: 当操作失败时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            
            logger.debug(f"获取仓库 {repo_name} 的拉取请求列表，状态: {state}")
            
            try:
                # 获取指定状态的拉取请求
                prs = repo.get_pulls(state=state)
                pr_list = []
                
                # 处理每个拉取请求，提取关键信息
                for pr in prs:
                    pr_data = {
                        "number": pr.number,
                        "title": pr.title,
                        "state": pr.state,
                        "created_at": pr.created_at.isoformat() if pr.created_at else None,
                        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                        "head": pr.head.ref,
                        "base": pr.base.ref
                    }
                    pr_list.append(pr_data)
                    
                logger.debug(f"成功获取到 {len(pr_list)} 个拉取请求")
                return pr_list
                
            except Exception as e:
                logger.error(f"获取拉取请求列表过程中出错: {str(e)}")
                raise OperationFailedError(
                    f"获取拉取请求列表失败: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
                
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            raise OperationFailedError(
                f"获取拉取请求列表失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_get_pull_request_code(
        self, repo_name: Union[str, Any], pr_number: int
    ) -> List[Dict[str, str]]:
        r"""获取拉取请求的代码变更

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            pr_number: 拉取请求的编号

        Returns:
            List[Dict[str, str]]: 包含文件名和对应代码变更的字典列表
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            ResourceNotFoundError: 当拉取请求不存在时
            OperationFailedError: 当操作失败时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            
            logger.debug(f"获取拉取请求 #{pr_number} 的代码变更")
            
            try:
                # 获取指定编号的拉取请求
                pr = repo.get_pull(number=pr_number)
                
                # 检查拉取请求是否存在
                if not pr:
                    raise ResourceNotFoundError(
                        f"拉取请求 #{pr_number} 不存在",
                        platform=self.PLATFORM_NAME
                    )

                # 收集拉取请求中的文件变更
                files_changed = []
                
                try:
                    # 获取拉取请求中的文件及其变更
                    files = pr.get_files()
                    for file in files:
                        files_changed.append(
                            {
                                "filename": file.filename,
                                "patch": file.patch,  # 代码差异或变更
                            }
                        )
                except Exception as e:
                    logger.error(f"获取文件变更时出错: {str(e)}")
                    raise OperationFailedError(
                        f"获取文件变更失败: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )
                    
                logger.debug(f"成功获取到 {len(files_changed)} 个文件的变更")
                return files_changed
                
            except ResourceNotFoundError:
                # 直接向上传播资源不存在的异常
                raise
            except Exception as e:
                logger.error(f"获取拉取请求时出错: {str(e)}")
                raise ResourceNotFoundError(
                    f"拉取请求 #{pr_number} 不存在或无法访问: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
                
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            raise OperationFailedError(
                f"获取拉取请求代码变更失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_get_pull_request_comments(
        self, repo_name: Union[str, Any], pr_number: int
    ) -> List[Dict[str, str]]:
        r"""获取拉取请求的评论

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            pr_number: 拉取请求的编号

        Returns:
            List[Dict[str, str]]: 包含用户名和评论内容的字典列表
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            ResourceNotFoundError: 当拉取请求不存在时
            OperationFailedError: 当操作失败时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            
            logger.debug(f"获取拉取请求 #{pr_number} 的评论")
            
            try:
                # 获取指定编号的拉取请求
                pr = repo.get_pull(number=pr_number)
                
                # 检查拉取请求是否存在
                if not pr:
                    raise ResourceNotFoundError(
                        f"拉取请求 #{pr_number} 不存在",
                        platform=self.PLATFORM_NAME
                    )

                # 收集拉取请求中的评论
                comments = []
                
                try:
                    # 获取拉取请求中的所有评论
                    for comment in pr.get_comments():
                        comments.append({"user": comment.user.login, "body": comment.body})
                except Exception as e:
                    logger.error(f"获取评论时出错: {str(e)}")
                    raise OperationFailedError(
                        f"获取评论失败: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )
                    
                logger.debug(f"成功获取到 {len(comments)} 条评论")
                return comments
                
            except ResourceNotFoundError:
                # 直接向上传播资源不存在的异常
                raise
            except Exception as e:
                logger.error(f"获取拉取请求时出错: {str(e)}")
                raise ResourceNotFoundError(
                    f"拉取请求 #{pr_number} 不存在或无法访问: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
                
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            raise OperationFailedError(
                f"获取拉取请求评论失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_get_all_file_paths(
        self, repo_name: Union[str, Any], path: str = ""
    ) -> List[str]:
        r"""递归获取仓库中的所有文件路径

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            path: 开始遍历的仓库路径，空字符串表示从根目录开始

        Returns:
            List[str]: 指定目录结构中的文件路径列表
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            OperationFailedError: 当操作失败时
        """
        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            
            logger.debug(f"递归获取仓库 {repo_name} 中路径 '{path}' 下的所有文件")
            
            file_paths = []

            def traverse_directory(repo_path: str):
                try:
                    contents = repo.get_contents(repo_path)
                    for content in contents:
                        if content.type == "file":
                            file_paths.append(content.path)
                        elif content.type == "dir":
                            traverse_directory(content.path)
                except Exception as e:
                    logger.error(f"遍历目录 '{repo_path}' 时出错: {str(e)}")
                    raise OperationFailedError(
                        f"遍历目录 '{repo_path}' 失败: {str(e)}",
                        platform=self.PLATFORM_NAME
                    )

            # 开始递归遍历
            traverse_directory(path)
            
            logger.debug(f"成功获取到 {len(file_paths)} 个文件路径")
            return file_paths
            
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            raise OperationFailedError(
                f"获取仓库文件路径失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def github_retrieve_file_content(
        self, repo_name: Union[str, Any], file_path: str, branch: Optional[str] = None
    ) -> str:
        r"""获取GitHub仓库中文件的内容

        Args:
            repo_name: 仓库名称，可以是"owner/repo"格式或其他仓库标识符
            file_path: 要检索的文件路径
            branch: 分支名称，默认为None（使用默认分支）

        Returns:
            str: 解码后的文件内容
            
        Raises:
            RepositoryNotFoundError: 当仓库不存在时
            AuthenticationError: 当认证失败时
            ResourceNotFoundError: 当文件不存在时
            OperationFailedError: 当操作失败时
            ResourceNotFoundError: 当文件不存在时
            OperationFailedError: 当操作失败时
        """
        from github.ContentFile import ContentFile

        try:
            # 使用self.get_repository获取仓库
            repo = self.get_repository(repo_name)
            logger.debug(f"获取文件内容: {file_path}，分支: {branch or '默认分支'}")
            
            # 如果没有指定分支，使用默认分支
            if branch is None:
                branch = repo.default_branch
            
            try:
                # 获取文件内容
                file_content = repo.get_contents(file_path, ref=branch)
                
                if isinstance(file_content, ContentFile):
                    content = file_content.decoded_content.decode('utf-8')
                    logger.debug(f"成功获取文件 {file_path} 的内容，长度: {len(content)} 字符")
                    return content
                else:
                    # 处理多文件情况
                    raise OperationFailedError(
                        "不能处理多个文件的情况",
                        platform=self.PLATFORM_NAME
                    )
            except Exception as e:
                # 捕获文件不存在的情况
                raise ResourceNotFoundError(
                    f"获取文件 {file_path} 在分支 {branch} 失败: {str(e)}",
                    platform=self.PLATFORM_NAME
                )
        except RepositoryNotFoundError:
            # 直接向上传播仓库不存在的异常
            raise
        except AuthenticationError:
            # 直接向上传播认证失败的异常
            raise
        except ResourceNotFoundError:
            # 直接向上传播资源不存在的异常
            raise
        except Exception as e:
            # 统一处理其他所有异常
            logger.error(f"获取文件内容失败: {str(e)}")
            raise OperationFailedError(
                f"获取文件内容失败: {str(e)}",
                platform=self.PLATFORM_NAME
            )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        # 导入FunctionTool类
        from camel.toolkits import FunctionTool
        
        # 创建GitHub特有的工具方法列表
        github_specific_tools = [
            FunctionTool(self.github_create_pull_request),
            FunctionTool(self.github_get_issue_list),
            FunctionTool(self.github_get_issue_content),
            FunctionTool(self.github_get_pull_request_list),
            FunctionTool(self.github_get_pull_request_code),
            FunctionTool(self.github_get_pull_request_comments),
            FunctionTool(self.github_get_all_file_paths),
            FunctionTool(self.github_retrieve_file_content),
        ]
        
        # 获取基类提供的工具
        try:
            tools = super().get_tools()
            # 确保tools是列表类型
            if not isinstance(tools, list):
                tools = []
        except Exception:
            # 如果调用基类方法失败，创建空列表
            tools = []
        
        # 合并工具列表
        return tools + github_specific_tools
        
    def _test_credentials(self) -> bool:
        """测试GitHub凭证是否有效"""
        try:
            # 尝试获取当前用户信息作为凭证测试
            user = self.github.get_user()
            # 如果能成功获取用户信息，则凭证有效
            return True
        except Exception:
            # 任何异常都表示凭证无效
            return False

    # Deprecated method aliases for backward compatibility
    def create_pull_request(self, *args, **kwargs):
        r"""Deprecated: Use github_create_pull_request instead."""
        warnings.warn(
            "create_pull_request is deprecated. Use "
            "github_create_pull_request instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_create_pull_request(*args, **kwargs)

    def get_issue_list(self, *args, **kwargs):
        r"""Deprecated: Use github_get_issue_list instead."""
        warnings.warn(
            "get_issue_list is deprecated. Use github_get_issue_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_get_issue_list(*args, **kwargs)

    def get_issue_content(self, *args, **kwargs):
        r"""Deprecated: Use github_get_issue_content instead."""
        warnings.warn(
            "get_issue_content is deprecated. Use "
            "github_get_issue_content instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_get_issue_content(*args, **kwargs)

    def get_pull_request_list(self, *args, **kwargs):
        r"""Deprecated: Use github_get_pull_request_list instead."""
        warnings.warn(
            "get_pull_request_list is deprecated. "
            "Use github_get_pull_request_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_get_pull_request_list(*args, **kwargs)

    def get_pull_request_code(self, *args, **kwargs):
        r"""Deprecated: Use github_get_pull_request_code instead."""
        warnings.warn(
            "get_pull_request_code is deprecated. Use "
            "github_get_pull_request_code instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_get_pull_request_code(*args, **kwargs)

    def get_pull_request_comments(self, *args, **kwargs):
        r"""Deprecated: Use github_get_pull_request_comments instead."""
        warnings.warn(
            "get_pull_request_comments is deprecated. "
            "Use github_get_pull_request_comments instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_get_pull_request_comments(*args, **kwargs)

    def get_all_file_paths(self, *args, **kwargs):
        r"""Deprecated: Use github_get_all_file_paths instead."""
        warnings.warn(
            "get_all_file_paths is deprecated. Use "
            "github_get_all_file_paths instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_get_all_file_paths(*args, **kwargs)

    def retrieve_file_content(self, *args, **kwargs):
        r"""Deprecated: Use github_retrieve_file_content instead."""
        warnings.warn(
            "retrieve_file_content is deprecated. "
            "Use github_retrieve_file_content instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.github_retrieve_file_content(*args, **kwargs)
