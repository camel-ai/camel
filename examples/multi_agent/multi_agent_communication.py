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

from colorama import Fore

from camel.agents.deductive_reasoner_agent import DeductiveReasonerAgent
from camel.agents.insight_agent import InsightAgent
from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig
from camel.societies import RolePlaying
from camel.types import ModelType, TaskType


def main(model_type=ModelType.GPT_3_5_TURBO_16K, task_prompt=None,
         context_text=None) -> None:
    # Start the multi-agent communication
    print_and_write_md("=========================================",
                       color=Fore.WHITE)
    print_and_write_md("Welcome to CAMEL-AI Society!", color=Fore.RED)
    print_and_write_md("================== TASK ==================",
                       color=Fore.WHITE)
    print_and_write_md(f"Original task prompt:\n{task_prompt}\n",
                       color=Fore.YELLOW)
    print_and_write_md("================ CONTEXT ================",
                       color=Fore.WHITE)
    print_and_write_md(f"Context text:\n{context_text}\n", color=Fore.YELLOW)
    print_and_write_md("=========================================",
                       color=Fore.WHITE)

    # Model and agent initialization
    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)
    insight_agent = InsightAgent(model=model_type,
                                 model_config=model_config_description)
    deductive_reasoner_agent = DeductiveReasonerAgent(
        model=model_type, model_config=model_config_description)

    # Generate role with descriptions
    role_descriptions_dict = \
        role_assignment_agent.run_role_with_description(
            task_prompt=task_prompt, num_roles=4, role_names=None)

    # Split the original task into subtasks
    subtasks_with_dependencies_dict = \
        role_assignment_agent.split_tasks(
            task_prompt=task_prompt,
            role_descriptions_dict=role_descriptions_dict,
            num_subtasks=1,
            context_text=context_text)
    oriented_graph = {}
    for subtask_idx, details in subtasks_with_dependencies_dict.items():
        deps = details["dependencies"]
        oriented_graph[subtask_idx] = deps
    role_assignment_agent.draw_subtasks_graph(oriented_graph=oriented_graph)

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
    environment_record = {}

    # Print the information of the task, the subtasks and the roles with
    # descriptions
    print_and_write_md(
        f"List of {len(role_descriptions_dict)} roles with description:",
        color=Fore.GREEN)
    for role_name in role_descriptions_dict.keys():
        print_and_write_md(
            f"{role_name}:\n" + f"{role_descriptions_dict[role_name]}\n",
            color=Fore.BLUE)
    print_and_write_md(f"List of {len(subtasks)} subtasks:", color=Fore.YELLOW)
    for i, subtask in enumerate(subtasks):
        print_and_write_md(f"Subtask {i + 1}:\n{subtask}", color=Fore.YELLOW)
    for idx, subtask_group in enumerate(parallel_subtask_pipelines, 1):
        print_and_write_md(f"Pipeline {idx}: {', '.join(subtask_group)}",
                           color=Fore.YELLOW)
    print_and_write_md(
        "Dependencies among subtasks: " +
        json.dumps(subtasks_with_dependencies_dict, indent=4), color=Fore.BLUE)
    print_and_write_md("=========================================",
                       color=Fore.WHITE)

    # Resolve the subtasks in sequence based on the dependency graph
    for ID_one_subtask in (subtask for pipeline in parallel_subtask_pipelines
                           for subtask in pipeline):
        # Get the description of the subtask
        one_subtask = \
            subtasks_with_dependencies_dict[ID_one_subtask]["description"]
        # Get the insights from the chat history of based on the dependencies
        ID_pre_subtasks = \
            subtasks_with_dependencies_dict[ID_one_subtask]["dependencies"]

        insights_pre_subtask = \
            get_insights(ID_pre_subtasks, environment_record,
                         deductive_reasoner_agent, one_subtask,
                         role_assignment_agent, insight_agent, context_text)

        # Get the role with the highest compatibility score
        role_compatibility_scores_dict = (
            role_assignment_agent.evaluate_role_compatibility(
                one_subtask, role_descriptions_dict))

        # Get the top two roles with the highest compatibility scores
        ai_assistant_role = \
            max(role_compatibility_scores_dict,
                key=lambda role:
                role_compatibility_scores_dict[role]["score_assistant"])
        ai_user_role = \
            max(role_compatibility_scores_dict,
                key=lambda role:
                role_compatibility_scores_dict[role]["score_user"])

        ai_assistant_description = role_descriptions_dict[ai_assistant_role]
        ai_user_description = role_descriptions_dict[ai_user_role]

        print_and_write_md("================ SESSION ================",
                           color=Fore.WHITE)
        print_and_write_md(f"{ID_one_subtask}: \n{one_subtask}\n",
                           color=Fore.YELLOW)
        print_and_write_md(
            f"AI Assistant Role: {ai_assistant_role}\n" +
            f"{ai_assistant_description}\n", color=Fore.GREEN)
        print_and_write_md(
            f"AI User Role: {ai_user_role}\n" + f"{ai_user_description}\n",
            color=Fore.BLUE)

        # You can use the following code to play the role-playing game
        sys_msg_meta_dicts = [
            dict(
                assistant_role=ai_assistant_role, user_role=ai_user_role,
                assistant_description=ai_assistant_description +
                insights_pre_subtask, user_description=ai_user_description)
            for _ in range(2)
        ]

        task_with_IO = "- Description of TASK:\n" + \
            subtasks_with_dependencies_dict[ID_one_subtask]["description"] + \
            "\n- Input of TASK:\n" + \
            subtasks_with_dependencies_dict[ID_one_subtask]["input"] + \
            "\n- Output Standard for the completion of TASK:\n" + \
            subtasks_with_dependencies_dict[ID_one_subtask]["output_standard"]
        role_play_session = RolePlaying(
            assistant_role_name=ai_assistant_role,
            user_role_name=ai_user_role,
            task_prompt=task_with_IO,
            model_type=model_type,
            task_type=TaskType.
            ROLE_DESCRIPTION,  # Important for role description
            with_task_specify=False,
            extend_sys_msg_meta_dicts=sys_msg_meta_dicts,
        )

        chat_history_assistant = ("The TASK of the context text is:\n" +
                                  f"{one_subtask}\n")
        chat_history_two_roles = ""

        # Start the role-playing to complete the subtask
        chat_turn_limit, n = 50, 0
        input_assistant_msg, _ = role_play_session.init_chat()
        while n < chat_turn_limit:
            n += 1
            assistant_response, user_response = role_play_session.step(
                input_assistant_msg)

            print_and_write_md(
                f"AI User: {ai_user_role}\n\n" +
                f"{user_response.msg.content}\n", color=Fore.BLUE,
                MD_FILE=ID_one_subtask)
            print_and_write_md(
                f"AI Assistant: {ai_assistant_role}\n\n" +
                f"{assistant_response.msg.content}\n", color=Fore.GREEN,
                MD_FILE=ID_one_subtask)

            # Generate the insights from the chat history
            chat_history_assistant += (f"--- [{n}] ---\n"
                                       f"{assistant_response.msg.content}\n")
            user_conversation = user_response.msg.content
            assistant_conversation = assistant_response.msg.content.replace(
                "Solution&Action:\n", "").replace("Next request.",
                                                  "").strip("\n")
            transformed_text_with_category = \
                role_assignment_agent.transform_dialogue_into_text(
                    user=ai_user_role, assistant=ai_assistant_role,
                    task_prompt=one_subtask,
                    user_conversation=user_conversation,
                    assistant_conversation=assistant_conversation)
            if "ASSISTANCE" in transformed_text_with_category["categories"]:
                transformed_text = transformed_text_with_category["text"]
                chat_history_two_roles += (transformed_text + "\n\n")

            if assistant_response.terminated:
                print(Fore.GREEN +
                      (f"{ai_assistant_role} terminated. Reason: "
                       f"{assistant_response.info['termination_reasons']}."))
                break
            if user_response.terminated:
                print(Fore.GREEN + (
                    f"{ai_user_role} terminated. "
                    f"Reason: {user_response.info['termination_reasons']}."))
                break

            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break

            input_assistant_msg = assistant_response.msg

        print_and_write_md(
            f"Output of the {ID_one_subtask}:\n" +
            f"{chat_history_two_roles}\n", color=Fore.GREEN)

        insights_instruction = ("The CONTEXT TEXT is the chat history of " +
                                f"{ai_user_role} and {ai_assistant_role}. " +
                                "The INSIGHTs should come solely from the " +
                                "content of the conversation, not the " +
                                "conversation itsel.")
        insights = insight_agent.run(context_text=chat_history_assistant,
                                     insights_instruction=insights_instruction)
        insights_str = insight_agent.convert_json_to_str(insights)
        insights_subtasks[ID_one_subtask] = insights_str
        for insight in insights.values():
            if insight["entity_recognition"] is None:
                continue
            labels_key = tuple(insight["entity_recognition"])
            environment_record[labels_key] = insight
        printable_environment_record = \
            {str(label_tuple): insight_data
             for label_tuple, insight_data in environment_record.items()}
        print_and_write_md(
            "Environment record:\n" +
            f"{json.dumps(printable_environment_record, indent=4)}",
            color=Fore.CYAN)


def get_insights(ID_pre_subtasks, environment_record, deductive_reasoner_agent,
                 one_subtask, role_assignment_agent, insight_agent,
                 context_text):
    # React to the environment, and get the insights from it
    if ID_pre_subtasks is not None and len(ID_pre_subtasks) != 0:
        insights_pre_subtask = "\n" + \
            "====== CURRENT STATE =====\n" + \
            "The snapshot and the context of the TASK is presentd in " + \
            "the following insights which is close related to The " + \
            "\"Insctruction\" and the \"Input\":\n"
        labels_sets = [
            list(labels_set) for labels_set in environment_record.keys()
        ]
        conditions_and_quality_json = \
            deductive_reasoner_agent.deduce_conditions_and_quality(
                starting_state="None",
                target_state=one_subtask)
        target_labels = conditions_and_quality_json["labels"]

        _, _, _, labels_retrieved_sets = \
            role_assignment_agent.get_retrieval_index_from_environment(
                labels_sets=labels_sets,
                target_labels=target_labels,
                )
        # TODO: Add the print to UI
        print_and_write_md(
            "Retrieved labels from the environment:\n" +
            f"{labels_retrieved_sets}", color=Fore.CYAN)
        retrieved_insights = [
            environment_record[tuple(label_set)]
            for label_set in labels_retrieved_sets
        ]
        insights_pre_subtask += "\n".join(
            [str(insight) for insight in retrieved_insights])
    else:
        insights_none_pre_subtask = insight_agent.run(
            context_text=context_text)
        insights_pre_subtask = "\n" + \
            "====== CURRENT STATE =====\n" + \
            "The snapshot and the context of the TASK is presentd in " + \
            "the following insights which is close related to The " + \
            "\"Insctruction\" and the \"Input\":\n" + \
            f"{insights_none_pre_subtask}\n"
    return insights_pre_subtask


def print_and_write_md(text="", color=Fore.RESET, MD_FILE=None):
    # Print the text in the terminal
    # print(color + text)

    import html
    import re

    if MD_FILE is None:
        MD_FILE = ("examples/multi_agent/"
                   "tmp_of_multi_agent/multi-agent-output.md")
    else:
        MD_FILE = ("examples/multi_agent/"
                   f"tmp_of_multi_agent/{MD_FILE}.md")
    COLOR_MAP_MD = {
        Fore.BLUE: 'blue',
        Fore.GREEN: 'darkgreen',
        Fore.YELLOW: 'darkorange',
        Fore.RED: 'darkred',
        Fore.WHITE: 'black',
        Fore.RESET: 'reset',
        Fore.CYAN: 'darkcyan',
    }

    # Replace patterns outside of code blocks
    def replace_outside_code_blocks(text, color):
        # Split the text into code blocks and non-code blocks
        blocks = re.split("```", text)

        modified_blocks = []
        for i, block in enumerate(blocks):
            if i % 2 == 0:  # Non-code blocks
                lines = block.split('\n')
                modified_lines = [
                    f"<span style='color: {COLOR_MAP_MD[color]};'>" +
                    f"{line}</span>\n" if line else line for line in lines
                ]
                modified_block = '\n'.join(modified_lines)
                modified_blocks.append(modified_block)
            else:  # Code blocks
                modified_blocks.append(f"\n```{block}```\n")

        return ''.join(modified_blocks)

    escaped_text = html.escape("\n" + text)

    # Replace tabs and newlines outside of code blocks
    md_text = replace_outside_code_blocks(escaped_text, color)

    # Write to the markdown file
    with open(MD_FILE, mode='a', encoding="utf-8") as file:
        file.write(md_text)


if __name__ == "__main__":
    root_path = "examples/multi_agent/demo_examples/"
    file_names_task_prompt = [
        "task_prompt_trading_bot.txt", "task_prompt_authentication.txt",
        "task_prompt_supply_chain.txt",
        "task_prompt_endpoint_implementation.txt",
        "task_prompt_science_fiction.txt"
    ]
    file_names_context = [
        "context_content_trading_bot.txt",
        "context_content_authentication.txt",
        "context_content_supply_chain.txt",
        "context_content_endpoint_implementation.txt",
        "context_content_science_fiction.txt"
    ]

    index = 0
    with open(root_path + file_names_task_prompt[index], mode='r',
              encoding="utf-8") as file:
        task_prompt = file.read()
    with open(root_path + file_names_context[index], mode='r',
              encoding="utf-8") as file:
        context_text = file.read()

    main(task_prompt=task_prompt, context_text=context_text)
