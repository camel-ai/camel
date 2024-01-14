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

from camel.agents import InsightAgent
from camel.societies import RolePlaying
from camel.types import ModelType


def main(model_type=None,
         model_type_for_structure_output=ModelType.GPT_4_TURBO,
         chat_turn_limit=50, role_playing_output_tamplate=None) -> None:
    if role_playing_output_tamplate is None:
        role_playing_output_tamplate = """Lemma <NUM_1>:
    <PROOF>
Lemma <NUM_2>:
    <PROOF>
And so on...
Proof by Lemmas:
    <PROOF>
"""

    task_prompt = """Problem: Prove that for all positive integers `n` and `k` (where `k \\leq n`), the following identity holds:
`\\sum_{i=0}^{k} (-1)^i \\binom{n}{i} \\binom{n-i}{k-i} = (-1)^k`
"""  # noqa: E501

    role_play_session = RolePlaying(
        assistant_role_name="Mathematician",
        assistant_agent_kwargs=dict(model_type=model_type),
        user_role_name="Mathematician",
        user_agent_kwargs=dict(model_type=model_type),
        task_prompt=task_prompt,
        with_task_specify=False,
        task_specify_agent_kwargs=dict(model_type=model_type),
    )

    insight_agent = InsightAgent(model_type=model_type_for_structure_output)

    print(
        Fore.GREEN +
        f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n")
    print(Fore.BLUE +
          f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    n = 0
    input_assistant_msg, _ = role_play_session.init_chat()
    assistant_msg_record = ("The TASK of the context text is:\n"
                            f"{role_play_session.task_prompt}\n")
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(
            input_assistant_msg)

        if assistant_response.terminated:
            print(Fore.GREEN +
                  ("AI Assistant terminated. Reason: "
                   f"{assistant_response.info['termination_reasons']}."))
            break
        if user_response.terminated:
            print(Fore.GREEN +
                  ("AI User terminated. "
                   f"Reason: {user_response.info['termination_reasons']}."))
            break

        print(Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n")
        print(Fore.GREEN + "AI Assistant:\n\n"
              f"{assistant_response.msg.content}\n")

        assistant_msg_record += (f"--- [{n}] ---\n" +
                                 assistant_response.msg.content.replace(
                                     "Next request.", "").strip("\n") + "\n")

        if ("CAMEL_TASK_DONE" in user_response.msg.content
                or "CAMEL_TASK_DONE" in assistant_response.msg.content):
            insights_instruction = (
                "The CONTEXT TEXT is the steps to resolve " +
                "the TASK. The INSIGHTs should come solely" +
                "from the actions/steps.")
            insights = \
                insight_agent.run(context_text=assistant_msg_record,
                                  insights_instruction=insights_instruction)
            strutured_output = \
                insight_agent.transform_into_text(
                    insights=insights,
                    answer_template=role_playing_output_tamplate)

            print(Fore.YELLOW +
                  "The final structured output of the role-playing session "
                  f"is:\n{strutured_output}\n")

            break

        input_assistant_msg = assistant_response.msg

    # Clean up the color of the terminal
    print(Fore.RESET)


if __name__ == "__main__":
    main()
