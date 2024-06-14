# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import os
from dataclasses import dataclass
from typing import List, Optional

from camel.functions import OpenAIFunction

from .base import BaseToolkit


@dataclass
class GithubIssue:
    r"""Represents a GitHub issue.

    Attributes:
        title (str): The title of the issue.
        body (str): The body/content of the issue.
        number (int): The issue number.
        file_path (str): The path of the file associated with the issue.
        file_content (str): The content of the file associated with the issue.
    """

    def __init__(
        self,
        title: str,
        body: str,
        number: int,
        file_path: str,
        file_content: str,
    ) -> None:
        r"""Initialize a GithubIssue object.

        Args:
            title (str): The title of the GitHub issue.
            body (str): The body/content of the GitHub issue.
            number (int): The issue number.
            file_path (str): The path of the file associated with the issue.
            file_content (str): The content of the file associated with the
                issue.
        """
        self.title = title
        self.body = body
        self.number = number
        self.file_path = file_path
        self.file_content = file_content

    def summary(self) -> str:
        r"""Returns a summary of the issue.

        Returns:
            str: A string containing the title, body, number, file path, and
                file content of the issue.
        """
        return (
            f"Title: {self.title}\n"
            f"Body: {self.body}\n"
            f"Number: {self.number}\n"
            f"File Path: {self.file_path}\n"
            f"File Content: {self.file_content}"
        )


class GithubToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with GitHub
    repositories.

    This class provides methods for retrieving open issues, retrieving
        specific issues, and creating pull requests in a GitHub repository.

    Args:
        repo_name (str): The name of the GitHub repository.
        access_token (str, optional): The access token to authenticate with
            GitHub. If not provided, it will be obtained using the
            `get_github_access_token` method.
    """

    def __init__(
        self, repo_name: str, access_token: Optional[str] = None
    ) -> None:
        r"""Initializes a new instance of the GitHubToolkit class.

        Args:
            repo_name (str): The name of the GitHub repository.
            access_token (str, optional): The access token to authenticate
                with GitHub. If not provided, it will be obtained using the
                `get_github_access_token` method.
        """
        if access_token is None:
            access_token = self.get_github_access_token()

        try:
            from github import Auth, Github
        except ImportError:
            raise ImportError(
                "Please install `github` first. You can install it by running "
                "`pip install wikipedia`."
            )
        self.github = Github(auth=Auth.Token(access_token))
        self.repo = self.github.get_repo(repo_name)

    def get_tools(self) -> List[OpenAIFunction]:
        r"""Returns a list of OpenAIFunction objects representing the
        functions in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects
                representing the functions in the toolkit.
        """
        return [
            OpenAIFunction(self.retrieve_issue_list),
            OpenAIFunction(self.retrieve_issue),
            OpenAIFunction(self.create_pull_request),
        ]

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

    def retrieve_issue_list(self) -> List[GithubIssue]:
        r"""Retrieve a list of open issues from the repository.

        Returns:
            A list of GithubIssue objects representing the open issues.
        """
        issues = self.repo.get_issues(state='open')
        return [
            GithubIssue(
                title=issue.title,
                body=issue.body,
                number=issue.number,
                file_path=issue.labels[
                    0
                ].name,  # we require file path to be the first label in the PR
                file_content=self.retrieve_file_content(issue.labels[0].name),
            )
            for issue in issues
            if not issue.pull_request
        ]

    def retrieve_issue(self, issue_number: int) -> Optional[str]:
        r"""Retrieves an issue from a GitHub repository.

        This function retrieves an issue from a specified repository using the
        issue number.

        Args:
            issue_number (int): The number of the issue to retrieve.

        Returns:
            str: A formatted report of the retrieved issue.
        """
        issues = self.retrieve_issue_list()
        for issue in issues:
            if issue.number == issue_number:
                return issue.summary()
        return None

    def create_pull_request(
        self,
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
        sb = self.repo.get_branch(self.repo.default_branch)
        self.repo.create_git_ref(
            ref=f"refs/heads/{branch_name}", sha=sb.commit.sha
        )

        file = self.repo.get_contents(file_path)
        from github.ContentFile import ContentFile

        if isinstance(file, ContentFile):
            self.repo.update_file(
                file.path, body, new_content, file.sha, branch=branch_name
            )
            pr = self.repo.create_pull(
                title=pr_title,
                body=body,
                head=branch_name,
                base=self.repo.default_branch,
            )

            if pr is not None:
                return f"Title: {pr.title}\n" f"Body: {pr.body}\n"
            else:
                return "Failed to create pull request."
        else:
            raise ValueError("PRs with multiple files aren't supported yet.")

    def retrieve_file_content(self, file_path: str) -> str:
        r"""Retrieves the content of a file from the GitHub repository.

        Args:
            file_path (str): The path of the file to retrieve.

        Returns:
            str: The decoded content of the file.
        """
        file_content = self.repo.get_contents(file_path)

        from github.ContentFile import ContentFile

        if isinstance(file_content, ContentFile):
            return file_content.decoded_content.decode()
        else:
            raise ValueError("PRs with multiple files aren't supported yet.")
