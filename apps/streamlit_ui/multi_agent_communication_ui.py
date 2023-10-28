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
import json

import streamlit as st

from camel.agents.insight_agent import InsightAgent
from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig
from camel.societies import RolePlaying
from camel.typing import ModelType, TaskType


def main(model_type=None, task_prompt=None, context_text=None) -> None:

    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=None, model_config=model_config_description)
    insight_agent = InsightAgent(model=ModelType.GPT_3_5_TURBO_16K,
                                 model_config=model_config_description)

    # Generate role with descriptions
    role_names = None
    num_roles = 5
    role_descriptions_dict = role_assignment_agent.run(task_prompt=task_prompt,
                                                       num_roles=num_roles,
                                                       role_names=role_names)

    # Split the original task into subtasks
    subtasks_with_dependencies_dict = \
        role_assignment_agent.split_tasks(
            task_prompt=task_prompt,
            role_descriptions_dict=role_descriptions_dict,
            context_text=context_text)
    with st.expander("Dependencies among subtasks:"):
        for i in subtasks_with_dependencies_dict:
            with st.container():
                st.write(i)
                st.write(
                    'description:',
                    str(subtasks_with_dependencies_dict[i]['description']))
                st.write(
                    'dependencies:',
                    str(subtasks_with_dependencies_dict[i]['dependencies']))
                st.write('input:',
                         str(subtasks_with_dependencies_dict[i]['input']))
                st.write(
                    'output_standard:',
                    str(subtasks_with_dependencies_dict[i]['output_standard']))

    # print_and_write_md(
    #     "Dependencies among subtasks: " +
    #     json.dumps(subtasks_with_dependencies_dict, indent=4),
    # color=Fore.BLUE)
    subtasks = [
        subtasks_with_dependencies_dict[key]["description"]
        for key in sorted(subtasks_with_dependencies_dict.keys())
    ]

    parallel_subtask_pipelines = \
        role_assignment_agent.get_task_execution_order(
            subtasks_with_dependencies_dict)

    # Record the insights from chat history of the assistant
    insights_subtasks = {
        ID_subtask: ""
        for ID_subtask in subtasks_with_dependencies_dict.keys()
    }

    # print_and_write_md(
    #     f"List of {len(role_descriptions_dict)} roles with " +
    #  "description:",
    #     color=Fore.GREEN)
    with st.expander(
            f"List of {len(role_descriptions_dict)} roles with description:"):
        for role_name in role_descriptions_dict.keys():
            st.write(f"{role_name}:\n"
                     f"{role_descriptions_dict[role_name]}\n")

        # print_and_write_md(
        #     f"{role_name}:\n" + f"{role_descriptions_dict[role_name]}\n",
        #     color=Fore.BLUE)
    # st.write(Fore.YELLOW + f"Original task prompt:\n{task_prompt}")
    # print_and_write_md(f"Original task prompt:\n{task_prompt}",
    #                    color=Fore.YELLOW)
    with st.expander(f"List of {len(subtasks)} subtasks:"):
        # print_and_write_md(f"List of {len(subtasks)} subtasks:",
        # color=Fore.YELLOW)
        for i, subtask in enumerate(subtasks):
            st.write(f"Subtask {i + 1}:\n{subtask}")
            # print_and_write_md(f"Subtask {i + 1}:\n{subtask}",
            #  color=Fore.YELLOW)
        for idx, subtask_group in enumerate(parallel_subtask_pipelines, 1):
            st.write(f"Pipeline {idx}: {', '.join(subtask_group)}")
            # print_and_write_md(f"Pipeline {idx}: {', '.join(subtask_group)}",
            #                    color=Fore.YELLOW)
    # print_and_write_md("==========================================",
    #                    color=Fore.WHITE)

    # Resolve the subtasks in sequence based on the dependency graph
    for ID_one_subtask in (subtask for pipeline in parallel_subtask_pipelines
                           for subtask in pipeline):
        # Get the description of the subtask
        one_subtask = \
            subtasks_with_dependencies_dict[ID_one_subtask]["description"]
        # Get the insights from the chat history of based on the dependencies
        ID_pre_subtasks = \
            subtasks_with_dependencies_dict[ID_one_subtask]["dependencies"]

        if ID_pre_subtasks is not None and len(ID_pre_subtasks) != 0:
            insights_pre_subtask = "\n" + \
                "====== CURRENT STATE =====\n" + \
                "The snapshot and the context of the TASK is presentd in " + \
                "the following insights which is close related to The " + \
                "\"Insctruction\" and the \"Input\":\n" + \
                "\n".join(insights_subtasks[pre_subtask]
                          for pre_subtask in ID_pre_subtasks)
        else:
            insights_none_pre_subtask = insight_agent.run(
                context_text=context_text)
            insights_pre_subtask = "\n" + \
                "====== CURRENT STATE =====\n" + \
                "The snapshot and the context of the TASK is presentd in " + \
                "the following insights which is close related to The " + \
                "\"Insctruction\" and the \"Input\":\n" + \
                f"{json.dumps(insights_none_pre_subtask, indent=4)}\n"

        # Get the role with the highest compatibility score
        role_compatibility_scores_dict = (
            role_assignment_agent.evaluate_role_compatibility(
                one_subtask, role_descriptions_dict))

        # Get the top two roles with the highest compatibility scores
        top_two_positions = \
            sorted(role_compatibility_scores_dict.keys(),
                   key=lambda x: role_compatibility_scores_dict[x],
                   reverse=True)[:2]
        ai_assistant_role = top_two_positions[1]
        ai_user_role = top_two_positions[0]  # The user role is the one with
        # the highest score/compatibility
        ai_assistant_description = role_descriptions_dict[ai_assistant_role]
        ai_user_description = role_descriptions_dict[ai_user_role]

        # print_and_write_md("==========================================",
        #                    color=Fore.WHITE)
        # st.write(f"Subtask: \n{one_subtask}\n")
        # print_and_write_md(f"Subtask: \n{one_subtask}\n", color=Fore.YELLOW)
        # st.write(f"AI Assistant Role: {ai_assistant_role}\n"
        #          f"{ai_assistant_description}\n")
        # print_and_write_md(
        #     f"AI Assistant Role: {ai_assistant_role}\n" +
        #     f"{ai_assistant_description}\n", color=Fore.GREEN)
        # st.write(f"AI User Role: {ai_user_role}\n"
        #          f"{ai_user_description}\n")
        # print_and_write_md(
        #     f"AI User Role: {ai_user_role}\n" + f"{ai_user_description}\n",
        #     color=Fore.BLUE)

        # You can use the following code to play the role-playing game
        sys_msg_meta_dicts = [
            dict(
                assistant_role=ai_assistant_role, user_role=ai_user_role,
                assistant_description=ai_assistant_description +
                insights_pre_subtask, user_description=ai_user_description)
            for _ in range(2)
        ]

        task_with_IO = "Description of TASK:\n" + \
            subtasks_with_dependencies_dict[ID_one_subtask]["description"] + \
            "\nInput of TASK:\n" + \
            subtasks_with_dependencies_dict[ID_one_subtask]["input"] + \
            "\nOutput Standard of TASK:\n" + \
            subtasks_with_dependencies_dict[ID_one_subtask]["output_standard"]
        role_play_session = RolePlaying(
            assistant_role_name=ai_assistant_role,
            user_role_name=ai_user_role,
            task_prompt=task_with_IO,
            model_type=ModelType.GPT_3_5_TURBO_16K,
            task_type=TaskType.
            ROLE_DESCRIPTION,  # Important for role description
            with_task_specify=False,
            extend_sys_msg_meta_dicts=sys_msg_meta_dicts,
        )

        chat_history_assistant = ("The TASK of the context text is:\n" +
                                  f"{one_subtask}\n")

        chat_turn_limit, n = 50, 0
        input_assistant_msg, _ = role_play_session.init_chat()
        with st.expander(f"Subtask: \n{one_subtask}\n"):
            while n < chat_turn_limit:
                n += 1
                assistant_response, user_response = role_play_session.step(
                    input_assistant_msg)

                if assistant_response.terminated:
                    st.write(
                        (f"{ai_assistant_role} terminated. Reason: "
                         f"{assistant_response.info['termination_reasons']}."))
                    break
                if user_response.terminated:
                    st.write((
                        f"{ai_user_role} terminated. "
                        f"Reason: {user_response.info['termination_reasons']}."
                    ))
                    break

                # print_text_animated(
                #     Fore.BLUE +
                #     f"AI User:
                # {ai_user_role}\n\n{user_response.msg.content}\n")
                # print_text_animated(Fore.GREEN +
                #                     f"AI Assistant:
                # {ai_assistant_role}\n\n" +
                #                     f"{assistant_response.msg.content}\n")
                # print_text_animated()
                with st.chat_message("user"):
                    st.write(f"AI User: {ai_user_role}\n\n" +
                             f"{user_response.msg.content}\n")
                # print_and_write_md(
                #     f"AI User: {ai_user_role}\n\n" +
                #     f"{user_response.msg.content}\n", color=Fore.BLUE)
                with st.chat_message("assistant"):
                    st.write(f"AI Assistant: {ai_assistant_role}\n\n" +
                             f"{assistant_response.msg.content}\n")
                # print_and_write_md(
                #     f"AI Assistant: {ai_assistant_role}\n\n" +
                #     f"{assistant_response.msg.content}\n", color=Fore.GREEN)

                if "CAMEL_TASK_DONE" in user_response.msg.content:
                    break

                # Generate the insights from the chat history
                chat_history_assistant += (
                    f"===== [{n}] ===== \n"
                    f"{user_response.msg.content}\n"
                    f"{assistant_response.msg.content}\n")

                input_assistant_msg = assistant_response.msg

        # TODO: Generate insights from the chat history
        # insights_instruction = ("The CONTEXT TEXT is related to code " +
        #                         "implementation. Pay attention to the " +
        #                         "code structure code environment.")
        insights = insight_agent.run(context_text=chat_history_assistant)
        insights_str = insight_agent.convert_json_to_str(insights)
        insights_subtasks[ID_one_subtask] = insights_str


# def print_and_write_md(text, color=Fore.RESET):
#     import html
#     import re

#     MD_FILE = "examples/multi_agent/multi-agent-output.md"
#     COLOR_MAP_MD = {
#         Fore.BLUE: 'blue',
#         Fore.GREEN: 'darkgreen',
#         Fore.YELLOW: 'darkorange',
#         Fore.RED: 'darkred',
#         Fore.WHITE: 'black',
#         Fore.RESET: 'reset',
#         Fore.CYAN: 'darkcyan',
#     }

#     # Replace patterns outside of code blocks
#     def replace_outside_code_blocks(text, color):
#         # Split the text into code blocks and non-code blocks
#         blocks = re.split("```", text)

#         modified_blocks = []
#         for i, block in enumerate(blocks):
#             if i % 2 == 0:  # Non-code blocks
#                 lines = block.split('\n')
#                 modified_lines = [
#                     f"<span style='color: {COLOR_MAP_MD[color]};'>" +
#                     f"{line}</span>\n" if line else line for line in lines
#                 ]
#                 modified_block = '\n'.join(modified_lines)
#                 modified_blocks.append(modified_block)
#             else:  # Code blocks
#                 modified_blocks.append(f"\n```{block}```\n")

#         return ''.join(modified_blocks)

#     escaped_text = html.escape("\n" + text)

#     # Replace tabs and newlines outside of code blocks
#     md_text = replace_outside_code_blocks(escaped_text, color)

#     # Write to the markdown file
#     with open(MD_FILE, mode='a', encoding="utf-8") as file:
#         file.write(md_text)
task_prompt_supply_chain = """Ensure All Customer Orders Are Fulfilled Within the Stipulated Time Frame While Minimizing Total Operational Costs:
- Ensure 200 units of Product X and 300 units of Product Y are delivered to Customer 1 within 10 days.
- Ensure 150 units of Product X are delivered to Customer 2 within 15 days."""  # noqa: E501

context_content_supply_chain = """### Environmental State Information
1. **Inventory Information**
- Warehouse A: 1500 units of Product X, 1000 units of Product Y
- Warehouse B: 500 units of Product X, 1800 units of Product Y
- In-Transit Inventory: 200 units of Product X, en route from Supplier A, expected to reach Warehouse A in 7 days

2. **Order Information**
- Customer 1: Requests delivery of 200 units of Product X and 300 units of Product Y within 10 days
- Customer 2: Requests delivery of 150 units of Product X within 15 days

3. **Production Status**
- Production Line 1: Currently producing Product X, daily capacity is 100 units, with 50 units of work-in-process
- Production Line 2: Currently producing Product Y, daily capacity is 150 units, with 30 units of work-in-process

4. **Logistics Information**
- Transport Path 1 (Warehouse A to Customer 1): Estimated transit time of 3 days, transport cost of $2/unit
- Transport Path 2 (Warehouse B to Customer 2): Estimated transit time of 5 days, transport cost of $1.5/unit

5. **Market Information**
- Market demand for Product X: Average 1500 units per month, expected to increase by 10% next month
- Market demand for Product Y: Average 2000 units per month, expected to decrease by 5% next month

6. **Supply Information**
- Supplier A: Provides raw materials for Product X, delivery cycle is 14 days, cost is $5/unit
- Supplier B: Provides raw materials for Product Y, delivery cycle is 10 days, cost is $4/unit

7. **Supplier Contact Information**
- **Supplier A**:
    - Contact Person: John Doe
    - Phone: +123-456-7890
    - Email: [john.doe@supplierA.com](mailto:john.doe@supplierA.com)
    - Address: 123 Main St, CityA, CountryA
- **Supplier B**:
    - Contact Person: Jane Smith
    - Phone: +987-654-3210
    - Email: [jane.smith@supplierB.com](mailto:jane.smith@supplierB.com)
    - Address: 456 Elm St, CityB, CountryB"""  # noqa: E501
