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

from camel.agents import ChatAgent
from camel.loaders import GitHubLoader
from camel.messages import BaseMessage
from camel.prompts import PromptTemplateGenerator
from camel.types import TaskType


def solve_latest_issue(
    loader: GitHubLoader,
    model=None,
) -> None:
    latest_issue = loader.retrieve_latest_issue()
    prompt_template = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.GITHUB, 'solve_issue'
    )
    prompt = prompt_template.format(
        issue_description=latest_issue.body,
        source_code=latest_issue.file_content,
    )
    print(f"Prompt: {prompt}")
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Software Engineer",
        content="You are an experienced software engineer who specializes on data structures and algorithms tasks.",
    )
    agent = ChatAgent(assistant_sys_msg, model_type=model)
    agent.reset()

    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    assistant_response = agent.step(user_msg)

    if len(assistant_response.msgs) > 0:
        print(f"Assistant response: {assistant_response.msg.content}")
        print("Committing...")
        loader.create_pull_request(
            latest_issue.file_name,
            assistant_response.msg.content,
            f"[GitHub Agent] Solved issue : {latest_issue.title}",
            "I hope it works",
        )


def main(model=None) -> None:
    repo_name = "eigent-ai/lambda-working-repo"
    access_token = os.getenv("GITHUB_ACCESS_TOKEN")
    loader = GitHubLoader(repo_name, access_token)
    solve_latest_issue(loader, model)


if __name__ == "__main__":
    main()
