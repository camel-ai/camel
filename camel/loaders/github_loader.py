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
from github import Auth, Github


class GitHubLoaderIssue:
    def __init__(self, title, body, number, file_path, file_content):
        self.title = title
        self.body = body
        self.number = number
        self.file_path = file_path
        self.file_content = file_content


class GitHubLoader:
    r"""A class for loading data from GitHub repositories."""

    def __init__(self, repo_name, access_token):
        self.github = Github(auth=Auth.Token(access_token))
        self.repo = self.github.get_repo(repo_name)

    def retrieve_issue_list(self):
        issues = self.repo.get_issues(state='open')
        return [
            GitHubLoaderIssue(
                issue.title,
                issue.body,
                issue.number,
                issue.labels[0].name,
                self.retrieve_file_content(issue.labels[0].name),
            )
            for issue in issues
            if not issue.pull_request
        ]

    def retrieve_latest_issue(self):
        issues = self.retrieve_issue_list()
        return issues[0]

    def retrieve_file_content(self, file_path):
        file_content = self.repo.get_contents(file_path)
        return file_content.decoded_content.decode()

    def create_pull_request(
        self, file_path, new_content, pr_title, commit_message
    ):
        branch_name = f"github-agent-update-{file_path.replace('/', '-')}"
        sb = self.repo.get_branch(self.repo.default_branch)
        self.repo.create_git_ref(
            ref=f"refs/heads/{branch_name}", sha=sb.commit.sha
        )
        file = self.repo.get_contents(file_path)
        self.repo.update_file(
            file.path, commit_message, new_content, file.sha, branch=branch_name
        )
        pr = self.repo.create_pull(
            title=pr_title,
            body=commit_message,
            head=branch_name,
            base=self.repo.default_branch,
        )
        return pr

    def commit_file_content(self, file_path, new_content, commit_message):
        file = self.repo.get_contents(file_path)
        self.repo.update_file(file.path, commit_message, new_content, file.sha)
