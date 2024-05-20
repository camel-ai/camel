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

from camel.functions.github_functions import (
    create_pull_request,
    retrieve_issue,
)
from camel.loaders.github_loader import GitHubLoader, GitHubLoaderIssue

mock_issue = GitHubLoaderIssue(
    title='Time complexity for product_of_array_except_self.py',
    body='Improve the time complexity for the product_of_array_except_self.py file',
    number=1,
    file_path='product_of_array_except_self.py',
    file_content='def product_of_array_except_self(nums): ...',
)


@patch.object(GitHubLoader, '__init__', lambda self, *args, **kwargs: None)
@patch.object(GitHubLoader, 'retrieve_issue', return_value=mock_issue)
def test_retrieve_issue(mock_retrieve_issue):
    expected_response = (
        "Title: Time complexity for product_of_array_except_self.py\n"
        "Body: Improve the time complexity for the product_of_array_except_self.py file\n"
        "Number: 1\n"
        "File Path: product_of_array_except_self.py\n"
        "File Content: def product_of_array_except_self(nums): ..."
    )

    loader = GitHubLoader('test/repo', '1')

    assert retrieve_issue(loader, 1) == expected_response


@patch(
    'camel.functions.github_functions.get_github_access_token',
    return_value="1",
)
@patch.object(GitHubLoader, '__init__', lambda self, *args, **kwargs: None)
@patch.object(GitHubLoader, 'create_pull_request', return_value="pr")
def test_create_pull_request(
    mock_get_github_access_token, mock_create_pull_request
):
    expected_response = (
        "Title: [GitHub Agent] Solved issue: Time complexity for product_of_array_except_self.py\n"
        "Body: Fixes #1\n"
    )

    loader = GitHubLoader('test/repo', '1')
    pr = create_pull_request(
        loader,
        mock_issue.file_path,
        mock_issue.file_content,
        mock_issue.title,
        mock_issue.number,
    )

    assert pr == expected_response


if __name__ == '__main__':
    import pytest

    pytest.main()
