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
from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.toolkits import GithubToolkit
from camel.utils import print_text_animated


def solve_issue(
    repo_name,
    issue_number,
    model=None,
) -> None:
    prompt = f"""
    You need to solve the issue with number: {issue_number}
    For this you will have to use the provided github function to retrieve
    that issue. You will get all the necessary parameters to later create a
    pull request.

    When you have the issue, please follow the instruction and make the necessary
    changes to the source code provided. Once you have made the changes, you will
    need to use another provided github function to create a pull request
    that updates the file on the provided file path in the repository {repo_name}.
    The new_content property of the function should be the corrected source code.
    Return response of this function as the output of this task.
    """
    print(Fore.YELLOW + f"Final prompt:\n{prompt}\n")

    toolkit = GithubToolkit(repo_name=repo_name)
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Software Engineer",
        content="""You are an experienced software engineer who 
        specializes on data structures and algorithms tasks.""",
    )
    assistant_model_config = ChatGPTConfig(
        tools=toolkit.get_tools(),
        temperature=0.0,
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model_type=model,
        model_config=assistant_model_config,
        function_list=toolkit.get_tools(),
    )
    agent.reset()

    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    assistant_response = agent.step(user_msg)

    if len(assistant_response.msgs) > 0:
        print_text_animated(
            Fore.GREEN + f"Agent response:\n{assistant_response.msg.content}\n"
        )


def main(model=None) -> None:
    repo_name = "camel-ai/test-github-agent"
    solve_issue(repo_name=repo_name, issue_number=1, model=model)


if __name__ == "__main__":
    main()
