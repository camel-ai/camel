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
from camel.configs import ChatGPTConfig, FunctionCallingConfig
from camel.functions import MATH_FUNCS, SEARCH_FUNCS
from camel.societies import RolePlaying
from camel.types import ModelType, TaskType


def main(model_type=ModelType.GPT_3_5_TURBO_16K, task_prompt=None,
         context_text=None) -> None:
    # Start the multi-agent communication
    print_and_write_md("========================================",
                       color=Fore.WHITE)
    print_and_write_md("Welcome to CAMEL-AI Society!", color=Fore.RED)
    print_and_write_md("================ INPUT TASK ================",
                       color=Fore.WHITE)
    print_and_write_md(f"Original task prompt:\n{task_prompt}\n",
                       color=Fore.YELLOW)
    print_and_write_md("============== INPUT CONTEXT ==============",
                       color=Fore.WHITE)
    print_and_write_md(f"Context text:\n{context_text}\n", color=Fore.YELLOW)
    print_and_write_md("========================================",
                       color=Fore.WHITE)

    # Model and agent initialization
    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model_type=model_type, model_config=model_config_description)
    insight_agent = InsightAgent(model_type=model_type,
                                 model_config=model_config_description)
    deductive_reasoner_agent = DeductiveReasonerAgent(
        model_type=model_type, model_config=model_config_description)

    # Generate role with descriptions
    role_descriptions_dict = \
        role_assignment_agent.run_role_with_description(
            task_prompt=task_prompt, num_roles=4, role_names=None)

    # Split the original task into subtasks
    subtasks_with_dependencies_dict = \
        role_assignment_agent.split_tasks(
            task_prompt=task_prompt,
            role_descriptions_dict=role_descriptions_dict,
            num_subtasks=None,
            context_text=context_text)

    oriented_graph = {}
    for subtask_idx, details in subtasks_with_dependencies_dict.items():
        deps = details["dependencies"]
        oriented_graph[subtask_idx] = deps
    role_assignment_agent.draw_subtasks_graph(oriented_graph=oriented_graph)

    # Get the list of subtasks
    subtasks = [
        subtasks_with_dependencies_dict[key]["description"]
        for key in sorted(subtasks_with_dependencies_dict.keys())
    ]

    # Calculate the execution order of the subtasks, based on their
    # dependencies
    parallel_subtask_pipelines = \
        role_assignment_agent.get_task_execution_order(
            subtasks_with_dependencies_dict)

    # Initialize the environment record
    environment_record = {}  # The cache of the system
    if context_text is not None:
        insights = insight_agent.run(context_text=context_text)
        for insight in insights.values():
            if insight["entity_recognition"] is None:
                continue
            tags = tuple(insight["entity_recognition"])
            environment_record[tags] = insight

    # Print a part of the configurations of the multi-agent communication
    # to specific markdown files
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
        json.dumps(subtasks_with_dependencies_dict, indent=4), color=Fore.BLUE,
        file_path="dependencies among subtasks")
    print_and_write_md("========================================",
                       color=Fore.WHITE)

    # Resolve the subtasks in sequence of the pipelines
    for subtask_id in (subtask for pipeline in parallel_subtask_pipelines
                       for subtask in pipeline):
        # Get the description of the subtask
        one_subtask = \
            subtasks_with_dependencies_dict[subtask_id]["description"]
        one_subtask_labels = \
            subtasks_with_dependencies_dict[subtask_id]["input_tags"]
        # Get the insights from the environment for the subtask
        insights_for_subtask = get_insights_from_environment(
            subtask_id, one_subtask, one_subtask_labels, environment_record,
            deductive_reasoner_agent, role_assignment_agent, insight_agent,
            context_text)

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
        print_and_write_md(f"{subtask_id}: \n{one_subtask}\n",
                           color=Fore.YELLOW)
        print_and_write_md(
            f"AI Assistant Role: {ai_assistant_role}\n" +
            f"{ai_assistant_description}\n", color=Fore.GREEN)
        print_and_write_md(
            f"AI User Role: {ai_user_role}\n" + f"{ai_user_description}\n",
            color=Fore.BLUE)

        subtask_content = (
            "- Description of TASK:\n" +
            subtasks_with_dependencies_dict[subtask_id]["description"] +
            "\n- Input of TASK:\n" +
            subtasks_with_dependencies_dict[subtask_id]["input_content"] +
            "\n- Output Standard for the completion of TASK:\n" +
            subtasks_with_dependencies_dict[subtask_id]["output_standard"])
        print_and_write_md(
            f"Task of the role-playing ({subtask_id}):\n"
            f"{subtask_content}\n\n", color=Fore.RED, file_path=subtask_id)

        # You can use the following code to play the role-playing game
        sys_msg_meta_dicts = [
            dict(
                assistant_role=ai_assistant_role, user_role=ai_user_role,
                assistant_description=ai_assistant_description + "\n" +
                insights_for_subtask, user_description=ai_user_description +
                "\n" + insights_for_subtask) for _ in range(2)
        ]  # System message meta data dicts
        function_list = [*MATH_FUNCS, *SEARCH_FUNCS]
        assistant_model_config = \
            FunctionCallingConfig.from_openai_function_list(
                function_list=function_list,
                kwargs=dict(temperature=0.7),
            )  # Assistant model config
        user_model_config = FunctionCallingConfig.from_openai_function_list(
            function_list=function_list,
            kwargs=dict(temperature=0.7),
        )  # User model config

        role_play_session = RolePlaying(
            assistant_role_name=ai_assistant_role,
            user_role_name=ai_user_role,
            assistant_agent_kwargs=dict(
                model_type=ModelType.GPT_4_TURBO,
                model_config=assistant_model_config,
                function_list=function_list,
            ),
            user_agent_kwargs=dict(
                model_type=ModelType.GPT_4_TURBO,
                model_config=user_model_config,
                function_list=function_list,
            ),
            task_prompt=subtask_content,
            model_type=ModelType.GPT_4_TURBO,
            task_type=TaskType.
            ROLE_DESCRIPTION,  # Important for role description
            with_task_specify=False,
            extend_sys_msg_meta_dicts=sys_msg_meta_dicts,
        )

        actions_record = ("The TASK of the context text is:\n" +
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
                file_path=subtask_id)
            print_and_write_md(
                f"AI Assistant: {ai_assistant_role}\n\n" +
                f"{assistant_response.msg.content}\n", color=Fore.GREEN,
                file_path=subtask_id)

            actions_record += (f"--- [{n}] ---\n"
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
            if ("ASSISTANCE" in transformed_text_with_category["categories"]
                    or "ANALYSIS"
                    in transformed_text_with_category["categories"]):
                transformed_text = transformed_text_with_category["text"]
                chat_history_two_roles += (transformed_text + "\n\n")

            print(Fore.BLUE + "AI User:\n"
                  f"{user_response.msg.content}\n")
            print(Fore.GREEN + "AI Assistant:\n"
                  f"{assistant_response.msg.content}\n")

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

            if "CAMEL_TASK_DONE" in user_response.msg.content or \
                    "CAMEL_TASK_DONE" in assistant_response.msg.content:
                break

            input_assistant_msg = assistant_response.msg

        print_and_write_md(
            f"Output of the {subtask_id}:\n" + f"{chat_history_two_roles}\n",
            color=Fore.GREEN)

        insights_instruction = ("The CONTEXT TEXT is the steps to resolve " +
                                "the TASK. The INSIGHTs should come solely" +
                                "from the actions/steps.")
        insights = insight_agent.run(context_text=actions_record,
                                     insights_instruction=insights_instruction)
        for insight in insights.values():
            if insight["entity_recognition"] is None:
                continue
            labels_key = tuple(insight["entity_recognition"])
            environment_record[labels_key] = insight
        printable_environment_record = \
            [insight_data for _, insight_data in environment_record.items()]
        print_and_write_md(
            "Environment record:\n" +
            f"{json.dumps(printable_environment_record, indent=4)}",
            color=Fore.CYAN, file_path=f"environment record of {subtask_id}")


def get_insights_from_environment(subtask_id, one_subtask, one_subtask_labels,
                                  environment_record, deductive_reasoner_agent,
                                  role_assignment_agent, insight_agent,
                                  context_text):
    # React to the environment, and get the insights from it
    conditions_and_quality_json = \
        deductive_reasoner_agent.deduce_conditions_and_quality(
            starting_state="None",
            target_state=one_subtask)

    target_labels = list(
        set(conditions_and_quality_json["labels"]) | set(one_subtask_labels))
    print(f"Target labels for {subtask_id}:\n{target_labels}")

    labels_sets = [
        list(labels_set) for labels_set in environment_record.keys()
    ]
    print(f"Labels sets for {subtask_id}:\n{labels_sets}")

    _, _, _, labels_retrieved_sets = \
        role_assignment_agent.get_retrieval_index_from_environment(
            labels_sets=labels_sets,
            target_labels=target_labels)
    print_and_write_md(
        "Retrieved labels from the environment:\n" +
        f"{labels_retrieved_sets}", color=Fore.CYAN,
        file_path=f"retrieved labels for {subtask_id}")

    # Retrive the necessaray insights from the environment
    retrieved_insights = [
        environment_record[tuple(label_set)]
        for label_set in labels_retrieved_sets
    ]
    print("Retrieved insights from the environment for "
          f"{subtask_id}:\n"
          f"{json.dumps(retrieved_insights, indent=4)}")

    insights_none_pre_subtask = insight_agent.run(context_text=context_text)
    insights_for_subtask = (
        "\n====== CURRENT STATE =====\n"
        "The snapshot and the context of the TASK is presentd in "
        "the following insights which is close related to The "
        "\"Insctruction\" and the \"Input\":\n" +
        f"{json.dumps(insights_none_pre_subtask, indent=4)}\n")

    insights_for_subtask += "\n".join(
        [json.dumps(insight, indent=4) for insight in retrieved_insights])

    print_and_write_md(
        f"Insights from the context text:\n{insights_for_subtask}",
        color=Fore.GREEN, file_path="insights of context text for "
        f"{subtask_id}")

    return insights_for_subtask


def print_and_write_md(text="", color=Fore.RESET, file_path=None):
    # Print the text in the terminal
    # print(color + text)

    import html
    import re

    if file_path is None:
        file_path = ("examples/multi_agent/"
                     "tmp_of_multi_agent/multi-agent-output.md")
    else:
        file_path = ("examples/multi_agent/"
                     f"tmp_of_multi_agent/{file_path}.md")
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
    with open(file_path, mode='a', encoding="utf-8") as file:
        file.write(md_text)


if __name__ == "__main__":
    root_path = "examples/multi_agent/demo_examples/"
    file_names_task_prompt = [
        "task_prompt_trading_bot.txt",
        "task_prompt_authentication.txt",
        "task_prompt_supply_chain.txt",
        "task_prompt_endpoint_implementation.txt",
        "task_prompt_science_fiction.txt",
        "task_prompt_business_novel.txt",
        "task_prompt_experiment.txt",
    ]
    file_names_context = [
        "context_content_trading_bot.txt",
        "context_content_authentication.txt",
        "context_content_supply_chain.txt",
        "context_content_endpoint_implementation.txt",
        "context_content_science_fiction.txt",
        "context_content_business_novel.txt",
        "context_content_experiment.txt",
    ]

    index = 3
    with open(root_path + file_names_task_prompt[index], mode='r',
              encoding="utf-8") as file:
        task_prompt = file.read()
    with open(root_path + file_names_context[index], mode='r',
              encoding="utf-8") as file:
        context_text = file.read()
    context_text = ("The context of the task is used to assist in knowledge "
                    "retrieval and collection. Given a or some specific query "
                    "requirement(s) or research topic(s), we will show its "
                    "intelligence to find the answer. For example, we are "
                    "inquired about the latest research on a specific "
                    "scientific question or explore the historical "
                    "development of a particular field.")
    task_prompt = (context_text + "\nNow, the query requirement "
                   "is: every important event in Generative AI in "
                   "2023, and predict the future of Generative AI "
                   "in 2024 through rigorous and mathematical "
                   "reasoning.")
    task_prompt = ("Create a detailed travel plan for a trip to "
                   "France, including itinerary, places to visit, "
                   "attractions, accommodations, and "
                   "transportation.")
    context_text = """Destination Overview:
Main Destination: France
Key Cities to Visit: Paris, Nice, Lyon, Bordeaux, Marseille
Special Interest Areas: French Riviera, Loire Valley (for castles and vineyards), Normandy (for historical sites)

Travel Dates and Duration:
Duration: 2 Weeks
Proposed Travel Dates: June 10, 2024, to June 24, 2024

Attractions and Activities:
Must-Visit Attractions: Eiffel Tower, Louvre Museum, Palace of Versailles, Mont Saint-Michel, Côte d'Azur beaches
Activities of Interest: Wine tasting in Bordeaux, culinary tours in Lyon, river cruising on the Seine, exploring the lavender fields in Provence

Accommodation and Transportation Preferences:
Accommodation Type: Mix of hotels and boutique guesthouses, preferably centrally located or with scenic views

Transportation: Domestic flights for longer distances, train travel for intercity connections, car rental for exploring countryside areas

Budget Considerations:
Total Budget: 2000 euros
Preferential Budget Allocation: Accommodations, experiences, dining

Cultural Experiences:
Interest in local cultural experiences, such as cooking classes, art workshops, and attending a live performance (e.g., cabaret show in Paris)
Dining Preferences:

Explore renowned French cuisine; include recommendations for bistros, brasseries, and Michelin-starred restaurants
Dietary Restrictions: no-pork

Language and Communication:
French language proficiency: entry level
Desire for English-speaking guides or information resources"""  # noqa: E501

    main(task_prompt=task_prompt, context_text=context_text)
