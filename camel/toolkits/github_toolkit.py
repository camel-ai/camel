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
from typing import Dict, List, Literal, Optional, Union

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, dependencies_required

logger = logging.getLogger(__name__)


@MCPServer()
class GithubToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with GitHub
    repositories.

    This class provides methods for retrieving open issues, retrieving
        specific issues, and creating pull requests in a GitHub repository.

    Args:
        access_token (str, optional): The access token to authenticate with
            GitHub. If not provided, it will be obtained using the
            `get_github_access_token` method.
    """

    @dependencies_required('github')
    def __init__(
        self,
        access_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes a new instance of the GitHubToolkit class.

        Args:
            repo_name (str): The name of the GitHub repository.
            access_token (str, optional): The access token to authenticate
                with GitHub. If not provided, it will be obtained using the
                `get_github_access_token` method.
        """
        super().__init__(timeout=timeout)
        from github.Auth import Token
        from github.MainClass import Github

        if access_token is None:
            access_token = self.get_github_access_token()

        self.github = Github(auth=Token(access_token))

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
                " it here: `https://github.com/settings/tokens`."
            )
        return GITHUB_ACCESS_TOKEN

    def github_create_pull_request(
        self,
        repo_name: str,
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
            repo_name (str): The name of the GitHub repository.
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
        """
        repo = self.github.get_repo(repo_name)
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
                raise

        file = repo.get_contents(file_path)

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
                return f"Title: {pr.title}\n" f"Body: {pr.body}\n"
            else:
                return "Failed to create pull request."
        else:
            raise ValueError("PRs with multiple files aren't supported yet.")

    def github_get_issue_list(
        self, repo_name: str, state: Literal["open", "closed", "all"] = "all"
    ) -> List[Dict[str, object]]:
        r"""Retrieves all issues from the GitHub repository.

        Args:
            repo_name (str): The name of the GitHub repository.
            state (Literal["open", "closed", "all"]): The state of pull
                requests to retrieve. (default: :obj:`all`)
                Options are:
                - "open": Retrieve only open pull requests.
                - "closed": Retrieve only closed pull requests.
                - "all": Retrieve all pull requests, regardless of state.

        Returns:
            List[Dict[str, object]]: A list of dictionaries where each
                dictionary contains the issue number and title.
        """
        repo = self.github.get_repo(repo_name)
        issues_info = []
        issues = repo.get_issues(state=state)

        for issue in issues:
            issues_info.append({"number": issue.number, "title": issue.title})

        return issues_info

    def github_get_issue_content(
        self, repo_name: str, issue_number: int
    ) -> str:
        r"""Retrieves the content of a specific issue by its number.

        Args:
            repo_name (str): The name of the GitHub repository.
            issue_number (int): The number of the issue to retrieve.

        Returns:
            str: issues content details.
        """
        try:
            repo = self.github.get_repo(repo_name)
            issue = repo.get_issue(number=issue_number)
            return issue.body
        except Exception as e:
            return f"can't get Issue number {issue_number}: {e!s}"

    def github_get_pull_request_list(
        self, repo_name: str, state: Literal["open", "closed", "all"] = "all"
    ) -> List[Dict[str, object]]:
        r"""Retrieves all pull requests from the GitHub repository.

        Args:
            repo_name (str): The name of the GitHub repository.
            state (Literal["open", "closed", "all"]): The state of pull
                requests to retrieve. (default: :obj:`all`)
                Options are:
                - "open": Retrieve only open pull requests.
                - "closed": Retrieve only closed pull requests.
                - "all": Retrieve all pull requests, regardless of state.

        Returns:
            list: A list of dictionaries where each dictionary contains the
                pull request number and title.
        """
        repo = self.github.get_repo(repo_name)
        pull_requests_info = []
        pull_requests = repo.get_pulls(state=state)

        for pr in pull_requests:
            pull_requests_info.append({"number": pr.number, "title": pr.title})

        return pull_requests_info

    def github_get_pull_request_code(
        self, repo_name: str, pr_number: int
    ) -> List[Dict[str, str]]:
        r"""Retrieves the code changes of a specific pull request.

        Args:
            repo_name (str): The name of the GitHub repository.
            pr_number (int): The number of the pull request to retrieve.

        Returns:
            List[Dict[str, str]]: A list of dictionaries where each dictionary
                contains the file name and the corresponding code changes
                (patch).
        """
        repo = self.github.get_repo(repo_name)
        # Retrieve the specific pull request
        pr = repo.get_pull(number=pr_number)

        # Collect the file changes from the pull request
        files_changed = []
        # Returns the files and their changes in the pull request
        files = pr.get_files()
        for file in files:
            files_changed.append(
                {
                    "filename": file.filename,
                    "patch": file.patch,  # The code diff or changes
                }
            )

        return files_changed

    def github_get_pull_request_comments(
        self, repo_name: str, pr_number: int
    ) -> List[Dict[str, str]]:
        r"""Retrieves the comments from a specific pull request.

        Args:
            repo_name (str): The name of the GitHub repository.
            pr_number (int): The number of the pull request to retrieve.

        Returns:
            List[Dict[str, str]]: A list of dictionaries where each dictionary
                contains the user ID and the comment body.
        """
        repo = self.github.get_repo(repo_name)
        # Retrieve the specific pull request
        pr = repo.get_pull(number=pr_number)

        # Collect the comments from the pull request
        comments = []
        # Returns all the comments in the pull request
        for comment in pr.get_comments():
            comments.append({"user": comment.user.login, "body": comment.body})

        return comments

    def github_get_all_file_paths(
        self, repo_name: str, path: str = ""
    ) -> List[str]:
        r"""Recursively retrieves all file paths in the GitHub repository.

        Args:
            repo_name (str): The name of the GitHub repository.
            path (str): The repository path to start the traversal from.
                empty string means starts from the root directory.
                (default: :obj:`""`)

        Returns:
            List[str]: A list of file paths within the specified directory
                structure.
        """
        from github.ContentFile import ContentFile

        repo = self.github.get_repo(repo_name)

        files: List[str] = []

        # Retrieves all contents of the current directory
        contents: Union[List[ContentFile], ContentFile] = repo.get_contents(
            path
        )

        if isinstance(contents, ContentFile):
            files.append(contents.path)
        else:
            for content in contents:
                if content.type == "dir":
                    # If it's a directory, recursively retrieve its file paths
                    files.extend(self.github_get_all_file_paths(content.path))
                else:
                    # If it's a file, add its path to the list
                    files.append(content.path)
        return files

    def github_retrieve_file_content(
        self, repo_name: str, file_path: str
    ) -> str:
        r"""Retrieves the content of a file from the GitHub repository.

        Args:
            repo_name (str): The name of the GitHub repository.
            file_path (str): The path of the file to retrieve.

        Returns:
            str: The decoded content of the file.
        """
        from github.ContentFile import ContentFile

        repo = self.github.get_repo(repo_name)

        file_content = repo.get_contents(file_path)
        if isinstance(file_content, ContentFile):
            return file_content.decoded_content.decode()
        else:
            raise ValueError("PRs with multiple files aren't supported yet.")

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.github_create_pull_request),
            FunctionTool(self.github_get_issue_list),
            FunctionTool(self.github_get_issue_content),
            FunctionTool(self.github_get_pull_request_list),
            FunctionTool(self.github_get_pull_request_code),
            FunctionTool(self.github_get_pull_request_comments),
            FunctionTool(self.github_get_all_file_paths),
            FunctionTool(self.github_retrieve_file_content),
        ]

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
