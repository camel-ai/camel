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

from unittest.mock import MagicMock, patch

from github.Auth import Auth
from github.ContentFile import ContentFile
from github.MainClass import Github  # type: ignore[attr-defined]

from camel.toolkits.github_toolkit import GithubToolkit


class MockToken(Auth):
    def __init__(self, token, *args, **kwargs):
        self._token = token

    @property
    def token(self):
        return self._token

    @property
    def token_type(self):
        return "Bearer"

    def __call__(self):
        return self._token


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_init(mock_get_repo):
    mock_get_repo.assert_called_once_with("repo_name")


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_tools(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    tools = github_toolkit.get_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_create_pull_request(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")

    mock_pr_response = MagicMock()
    mock_pr_response.title = """[GitHub Agent] Solved issue: Time 
    complexity for product_of_array_except_self.py"""
    mock_pr_response.body = "Fixes #1"
    github_toolkit.repo.create_pull.return_value = mock_pr_response

    mock_content_file = MagicMock(spec=ContentFile)
    mock_content_file.path = "path/to/file"
    mock_content_file.sha = "dummy_sha"
    github_toolkit.repo.get_contents.return_value = mock_content_file

    pr = github_toolkit.create_pull_request(
        file_path="path/to/file",
        branch_name="branch_name",
        new_content="This is the content of the file",
        pr_title="""[GitHub Agent] Solved issue: Time complexity for 
        product_of_array_except_self.py""",
        body="Fixes #1",
    )

    expected_response = """Title: [GitHub Agent] Solved issue: Time 
    complexity for product_of_array_except_self.py\nBody: Fixes #1\n"""

    assert (
        pr == expected_response
    ), f"Expected {expected_response}, but got {pr}"


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_all_issues(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    github_toolkit.repo.get_issues.return_value = [mock_issue]

    issues = github_toolkit.get_issue_list()

    expected_issues = [{"number": 1, "title": "Test Issue"}]
    assert (
        issues == expected_issues
    ), f"Expected {expected_issues}, but got {issues}"


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_issue_content(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    mock_issue = MagicMock()
    mock_issue.body = "Issue content"
    github_toolkit.repo.get_issue.return_value = mock_issue

    content = github_toolkit.get_issue_content(1)
    expected_content = "Issue content"

    assert (
        content == expected_content
    ), f"Expected {expected_content}, but got {content}"


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_all_pull_requests(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    mock_pr = MagicMock()
    mock_pr.number = 1
    mock_pr.title = "Test PR"
    github_toolkit.repo.get_pulls.return_value = [mock_pr]

    prs = github_toolkit.get_pull_request_list()
    expected_prs = [{"number": 1, "title": "Test PR"}]

    assert prs == expected_prs, f"Expected {expected_prs}, but got {prs}"


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_pull_request_code(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    mock_file = MagicMock()
    mock_file.filename = "file1.py"
    mock_file.patch = "code changes"
    github_toolkit.repo.get_pull.return_value.get_files.return_value = [
        mock_file
    ]

    files_changed = github_toolkit.get_pull_request_code(1)
    expected_files = [{"filename": "file1.py", "patch": "code changes"}]

    assert (
        files_changed == expected_files
    ), f"Expected {expected_files}, but got {files_changed}"


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_pull_request_comments(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    mock_comment = MagicMock()
    mock_comment.user.login = "user1"
    mock_comment.body = "Test comment"
    github_toolkit.repo.get_pull.return_value.get_comments.return_value = [
        mock_comment
    ]

    comments = github_toolkit.get_pull_request_comments(1)
    expected_comments = [{"user": "user1", "body": "Test comment"}]

    assert (
        comments == expected_comments
    ), f"Expected {expected_comments}, but got {comments}"


@patch('github.Auth.Token', MockToken)
@patch.object(Github, 'get_repo', return_value=MagicMock())
def test_get_all_file_paths(mock_get_repo):
    github_toolkit = GithubToolkit("repo_name", "token")
    mock_content = MagicMock()
    mock_content.type = "file"
    mock_content.path = "path/to/file.py"
    github_toolkit.repo.get_contents.return_value = [mock_content]

    files = github_toolkit.get_all_file_paths()
    expected_files = ["path/to/file.py"]

    assert (
        files == expected_files
    ), f"Expected {expected_files}, but got {files}"
