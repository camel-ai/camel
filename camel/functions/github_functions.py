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
from typing import List

from camel.functions import OpenAIFunction
from camel.loaders import GitHubLoader


def get_github_access_token() -> str:
    r"""Retrieve the GitHub access token from environment variables.

    Returns:
        str: A string containing the GitHub access token.

    Raises:
        ValueError: If the API key or secret is not found in the environment
            variables.
    """
    # Get `GITHUB_ACCESS_TOKEN` here:
    # https://github.com/settings/tokens
    GITHUB_ACCESS_TOKEN = os.environ.get("GITHUB_ACCESS_TOKEN")

    if not GITHUB_ACCESS_TOKEN:
        raise ValueError(
            "GITHUB_ACCESS_TOKEN not found in environment variables. Get it "
            "here: `https://github.com/settings/tokens`."
        )
    return GITHUB_ACCESS_TOKEN


def get_github_loader(access_token: str, repo_name: str) -> GitHubLoader:
    r"""Create a GitHub loader object.

    Args:
        access_token (str): The GitHub access token.
        repo_name (str): The name of the repository.

    Returns:
        GitHubLoader: A GitHub loader object.
    """
    return GitHubLoader(repo_name, access_token)


def retrieve_issue(loader, issue_number):
    r"""Retrieves an issue from a GitHub repository.

    This function retrieves an issue from a specified repository using the
    issue number.

    Args:
        repo_name (str): The name of the repository from which to retrieve the issue.
        issue_number (str): The number of the issue to retrieve.

    Returns:
        str: A formatted report of the retrieved issue.
    """
    issue = loader.retrieve_issue(issue_number)

    if issue:
        return (
            f"Title: {issue.title}\n"
            f"Body: {issue.body}\n"
            f"Number: {issue.number}\n"
            f"File Path: {issue.file_path}\n"
            f"File Content: {issue.file_content}"
        )
    return "Issue not found."


def create_pull_request(
    loader, file_path, new_content, issue_title, issue_number
):
    r"""Creates a pull request.

    This function creates a pull request in specified repository, which updates a
    file in the specific path with new content. The pull request description
    contains information about the issue title and number.

    Args:
        repo_name (str): The name of the repository in which to create the pull request.
        file_path (str): The path of the file to be updated in the repository.
        new_content (str): The specified new content of the specified file.
        issue_title (str): The title of the issue that is solved by this pull request.
        issue_number (str): The number of the issue that is solved by this pull request.

    Returns:
        str: A formatted report of the whether the pull request was created
        successfully or not.
    """
    title = f"[GitHub Agent] Solved issue: {issue_title}"
    body = f"Fixes #{issue_number}"
    pr = loader.create_pull_request(file_path, new_content, title, body)

    if pr:
        return f"Title: {title}\n" f"Body: {body}\n"
    return "Failed to create the pull request."


GITHUB_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func)  # type: ignore[arg-type]
    for func in [retrieve_issue, create_pull_request]
]
