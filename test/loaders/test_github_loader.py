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

from unittest.mock import MagicMock

from camel.loaders.github_loader import GitHubLoader, GitHubLoaderIssue


def test_init():
    # Create a mock GitHub instance
    mock_github = MagicMock()

    # Call the constructor of the GitHubLoader class
    github_loader = GitHubLoader(mock_github, "repo_name")

    # Assert that the repo attribute is set to the return value of the get_repo method
    assert github_loader.repo == mock_github.get_repo.return_value

    # Assert that the get_repo method was called with the correct argument
    mock_github.get_repo.assert_called_once_with("repo_name")


def test_retrieve_issue_list():
    # Create a mock GitHub instance
    mock_github = MagicMock()

    # Create a mock GitHubLoader instance
    mock_github_loader = GitHubLoader(mock_github, "repo_name")

    # Create a mock issue object
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "This is a test issue"
    mock_issue.pull_request = False

    mock_label = MagicMock()
    mock_label.name = "path/to/file"
    mock_issue.labels = [mock_label]

    # Mock the get_issues method of the mock_repo instance to return a list containing the mock issue object
    mock_github_loader.repo.get_issues.return_value = [mock_issue]
    mock_github_loader.retrieve_file_content = MagicMock(
        return_value="This is the content of the file"
    )

    # Call the retrieve_issue_list method
    issue_list = mock_github_loader.retrieve_issue_list()

    # Assert the returned issue list
    expected_issue = GitHubLoaderIssue(
        "Test Issue",
        "This is a test issue",
        1,
        "path/to/file",
        "This is the content of the file",
    )
    assert issue_list == [
        expected_issue
    ], f"Expected {expected_issue}, but got {issue_list}"
