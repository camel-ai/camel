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

from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import FunctionCallingConfig
from camel.functions import GITHUB_FUNCS
from camel.loaders import GitHubLoader
from camel.messages import BaseMessage
from camel.prompts import PromptTemplateGenerator
from camel.types import TaskType
from camel.utils import print_text_animated


def solve_latest_issue(
    loader: GitHubLoader,
    repo_name,
    model=None,
) -> None:
    latest_issue = loader.retrieve_latest_issue()
    prompt_template = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.GITHUB, 'solve_issue'
    )
    prompt = prompt_template.format(
        issue_title=latest_issue.title,
        issue_number=latest_issue.number,
        issue_description=latest_issue.body,
        file_path=latest_issue.file_path,
        source_code=latest_issue.file_content,
        repo_name=repo_name,
    )
    print(Fore.YELLOW + f"Final prompt:\n{prompt}\n")

    function_list = [
        *GITHUB_FUNCS,
    ]
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Software Engineer",
        content="You are an experienced software engineer who specializes on data structures and algorithms tasks.",
    )
    assistant_model_config = FunctionCallingConfig.from_openai_function_list(
        function_list=function_list,
        kwargs=dict(temperature=0.0),
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model_type=model,
        model_config=assistant_model_config,
        function_list=function_list,
    )
    agent.reset()

    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    assistant_response = agent.step(user_msg)

    if len(assistant_response.msgs) > 0:
        print_text_animated(
            Fore.GREEN + f"Agent response:\n{assistant_response.msg.content}\n"
        )


def main(model=None) -> None:
    repo_name = "eigent-ai/lambda-working-repo"
    access_token = os.getenv("GITHUB_ACCESS_TOKEN")
    loader = GitHubLoader(repo_name, access_token)
    solve_latest_issue(loader, repo_name, model)


if __name__ == "__main__":
    main()
