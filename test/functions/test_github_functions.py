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
from unittest.mock import patch

from github import Auth, Github

from camel.functions.github_functions import (
    create_pull_request,
)
from camel.loaders.github_loader import GitHubLoaderIssue

mock_issue = GitHubLoaderIssue(
    title='Time complexity for product_of_array_except_self.py',
    body='Improve the time complexity for the product_of_array_except_self.py file',
    number=1,
    file_path='product_of_array_except_self.py',
    file_content='def product_of_array_except_self(nums): ...',
)

# get_github_access_token


# def test_get_github_access_token(monkeypatch):
#     monkeypatch.setenv('GITHUB_ACCESS_TOKEN', 'TOKEN')
#     expected_access_token = 'TOKEN'
#     access_token = get_github_access_token()
#     assert access_token == expected_access_token


# def test_get_github_access_token_no_token(monkeypatch):
#     monkeypatch.delenv('GITHUB_ACCESS_TOKEN', raising=False)
#     with pytest.raises(ValueError) as error:
#         get_github_access_token()
#     assert (
#         str(error.value)
#         == "`GITHUB_ACCESS_TOKEN` not found in environment variables. Get it here: `https://github.com/settings/tokens`."
#     )


# # retrieve_issue
# @patch.object(GitHubLoader, '__init__', lambda self, *args, **kwargs: None)
# @patch.object(GitHubLoader, 'retrieve_issue', return_value=mock_issue)
# def test_retrieve_issue(monkeypatch, mock_retrieve_issue):
#     monkeypatch.setenv('GITHUB_ACCESS_TOKEN', 'TOKEN')
#     expected_response = (
#         "Title: Time complexity for product_of_array_except_self.py\n"
#         "Body: Improve the time complexity for the product_of_array_except_self.py file\n"
#         "Number: 1\n"
#         "File Path: product_of_array_except_self.py\n"
#         "File Content: def product_of_array_except_self(nums): ..."
#     )

#     assert retrieve_issue('test/repo', 1) == expected_response


# @patch.object(GitHubLoader, '__init__', lambda self, *args, **kwargs: None)
# @patch.object(GitHubLoader, 'retrieve_issue', return_value=None)
# def test_retrieve_issue_not_found(monkeypatch, mock_retrieve_issue):
#     monkeypatch.setenv('GITHUB_ACCESS_TOKEN', 'TOKEN')
#     expected_response = "Issue not found."
#     assert retrieve_issue('test/repo', 1) == expected_response


# # create_pull_request


# @patch(
#     'camel.functions.github_functions.get_github_access_token',
#     return_value="1",
# )
# @patch.object(GitHubLoader, '__init__', lambda self, *args, **kwargs: None)
# @patch.object(GitHubLoader, 'create_pull_request', return_value="pr")
# def test_create_pull_request(
#     monkeypatch, mock_get_github_access_token, mock_create_pull_request
# ):
#     monkeypatch.setenv('GITHUB_ACCESS_TOKEN', 'TOKEN')
#     expected_response = (
#         "Title: [GitHub Agent] Solved issue: Time complexity for product_of_array_except_self.py\n"
#         "Body: Fixes #1\n"
#     )

#     pr = create_pull_request(
#         'test/repo',
#         mock_issue.file_path,
#         mock_issue.file_content,
#         mock_issue.title,
#         mock_issue.number,
#     )

#     assert pr == expected_response


# @patch(
#     'camel.functions.github_functions.get_github_access_token',
#     return_value=None,
# )
# def test_create_pull_request_no_access_token(monkeypatch, mock_get_github_access_token):
#     monkeypatch.setenv('GITHUB_ACCESS_TOKEN', 'TOKEN')
#     with pytest.raises(AssertionError) as error:
#         create_pull_request(
#             'test/repo',
#             mock_issue.file_path,
#             mock_issue.file_content,
#             mock_issue.title,
#             mock_issue.number,
#         )
#     assert str(error.value) == ""  # from Auth.Token initializer


@patch.object(Github, 'get_repo', return_value="test/repo")
@patch.object(Auth.Token, '__init__', lambda self, *args, **kwargs: None)
def test_create_pull_request_failed(monkeypatch):
    monkeypatch.setenv('GITHUB_ACCESS_TOKEN', 'TOKEN')
    expected_response = "Failed to create the pull request."

    patch_path = 'camel.loaders.github_loader.GitHubLoader.create_pull_request'
    with patch(patch_path) as mock_github_loader_create_pull_request:
        mock_github_loader_create_pull_request.return_value = None

        pr = create_pull_request(
            'test/repo',
            mock_issue.file_path,
            mock_issue.file_content,
            mock_issue.title,
            mock_issue.number,
        )
        assert pr == expected_response
