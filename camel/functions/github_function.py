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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from github.Issue import Issue

class GitHubFunction:
    """Wrapper for GitHub API."""

    github: Any  #: :meta private:
    github_repo_instance: Any  #: :meta private:
    github_repository: Optional[str] = None
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None
    github_branch: Optional[str] = None
    github_base_branch: Optional[str] = None

    def validate_environment(cls, values: Dict) -> Dict:
        """ TODO 
        Validate that api key and python package exists in environment.
        """
        pass

    def parse_issues(self, issues: List[Issue]) -> List[dict]:
        """ TODO
        Extracts title and number from each Issue and puts them in a dictionary
        Parameters:
            issues(List[Issue]): A list of Github Issue objects
        Returns:
            List[dict]: A dictionary of issue titles and numbers
        """
        parsed = []
        return parsed

    def get_issues(self) -> str:
        """ TODO
        Fetches all open issues from the repo

        Returns:
            str: A plaintext report containing the number of issues
            and each issue's title and number.
        """
        return "No open issues available"

    def get_issue(self, issue_number: int) -> Dict[str, Any]:
        """ TODO
        Fetches a specific issue and its first 10 comments
        Parameters:
            issue_number(int): The number for the github issue
        Returns:
            dict: A doctionary containing the issue's title,
            body, and comments as a string
        """

        return {
            "title": "issue.title",
            "body": "issue.body",
            "comments": "str(comments)",
        }

    def create_pull_request(self, pr_query: str) -> str:
        """ TODO
        Makes a pull request from the bot's branch to the base branch
        Parameters:
            pr_query(str): a string which contains the PR title
            and the PR body. The title is the first line
            in the string, and the body are the rest of the string.
            For example, "Updated README\nmade changes to add info"
        Returns:
            str: A success or failure message
        """
        return f"Successfully created PR number #pr.number"

    def comment_on_issue(self, comment_query: str) -> str:
        """ TODO
        Adds a comment to a github issue
        Parameters:
            comment_query(str): a string which contains the issue number,
            two newlines, and the comment.
            for example: "1\n\nWorking on it now"
            adds the comment "working on it now" to issue 1
        Returns:
            str: A success or failure message
        """

        return "Commented on issue #comment"

    def create_file(self, file_query: str) -> str:
        """ TODO
        Creates a new file on the Github repo
        Parameters:
            file_query(str): a string which contains the file path
            and the file contents. The file path is the first line
            in the string, and the contents are the rest of the string.
            For example, "hello_world.md\n# Hello World!"
        Returns:
            str: A success or failure message
        """

        return "Created file #file_path"


    def read_file(self, file_path: str) -> str:
        """ TODO
        Reads a file from the github repo
        Parameters:
            file_path(str): the file path
        Returns:
            str: The file decoded as a string
        """
        return "#file"


    def update_file(self, file_query: str) -> str:
        """ TODO
        Updates a file with new content.
        Parameters:
            file_query(str): Contains the file path and the file contents.
                The old file contents is wrapped in OLD <<<< and >>>> OLD
                The new file contents is wrapped in NEW <<<< and >>>> NEW
                For example:
                /test/hello.txt
                OLD <<<<
                Hello Earth!
                >>>> OLD
                NEW <<<<
                Hello Mars!
                >>>> NEW
        Returns:
            A success or failure message
        """

        return "Updated file #file_path"

    def delete_file(self, file_path: str) -> str:
        """ TODO
        Deletes a file from the repo
        Parameters:
            file_path(str): Where the file is
        Returns:
            str: Success or failure message
        """

        return "Deleted file #file_path"
