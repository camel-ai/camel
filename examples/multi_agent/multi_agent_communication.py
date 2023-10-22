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
from camel.typing import ModelType, TaskType


def main(model_type=ModelType.GPT_3_5_TURBO_16K, task_prompt=None,
         context_text=None) -> None:
    print(Fore.WHITE + "==========================================")
    print_and_write_md("==========================================",
                       color=Fore.WHITE)
    print(Fore.RED + "Welcome to CAMEL-AI Society!")
    print_and_write_md("Welcome to CAMEL-AI Society!", color=Fore.RED)
    print(Fore.WHITE + "================== TASK ==================")
    print_and_write_md("================== TASK ==================",
                       color=Fore.WHITE)
    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print_and_write_md(f"Original task prompt:\n{task_prompt}\n",
                       color=Fore.YELLOW)
    print(Fore.WHITE + "================ CONTEXT ================")
    print_and_write_md("================ CONTEXT ================",
                       color=Fore.WHITE)
    print(Fore.YELLOW + f"Context text:\n{context_text}\n")
    print_and_write_md(f"Context text:\n{context_text}\n", color=Fore.YELLOW)
    print(Fore.WHITE + "==========================================")
    print_and_write_md("==========================================",
                       color=Fore.WHITE)

    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)
    insight_agent = InsightAgent(model=ModelType.model_type,
                                 model_config=model_config_description)
    deductive_reasoner_agent = DeductiveReasonerAgent(
        model=ModelType.model_type, model_config=model_config_description)

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
            num_subtasks=2,
            context_text=context_text)

    print(Fore.BLUE + "Dependencies among subtasks: " +
          json.dumps(subtasks_with_dependencies_dict, indent=4))
    print_and_write_md(
        "Dependencies among subtasks: " +
        json.dumps(subtasks_with_dependencies_dict, indent=4), color=Fore.BLUE)
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

    print(Fore.GREEN +
          f"List of {len(role_descriptions_dict)} roles with description:")
    print_and_write_md(
        f"List of {len(role_descriptions_dict)} roles with " + "description:",
        color=Fore.GREEN)
    for role_name in role_descriptions_dict.keys():
        print(Fore.BLUE + f"{role_name}:\n"
              f"{role_descriptions_dict[role_name]}\n")
        print_and_write_md(
            f"{role_name}:\n" + f"{role_descriptions_dict[role_name]}\n",
            color=Fore.BLUE)
    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}")
    print_and_write_md(f"Original task prompt:\n{task_prompt}",
                       color=Fore.YELLOW)
    print(Fore.YELLOW + f"List of {len(subtasks)} subtasks:")
    print_and_write_md(f"List of {len(subtasks)} subtasks:", color=Fore.YELLOW)
    for i, subtask in enumerate(subtasks):
        print(Fore.YELLOW + f"Subtask {i + 1}:\n{subtask}")
        print_and_write_md(f"Subtask {i + 1}:\n{subtask}", color=Fore.YELLOW)
    for idx, subtask_group in enumerate(parallel_subtask_pipelines, 1):
        print(Fore.YELLOW + f"Pipeline {idx}: {', '.join(subtask_group)}")
        print_and_write_md(f"Pipeline {idx}: {', '.join(subtask_group)}",
                           color=Fore.YELLOW)
    print(Fore.WHITE + "==========================================")
    print_and_write_md("==========================================",
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
            print(Fore.CYAN + "Retrieved labels from the environment:\n" +
                  f"{labels_retrieved_sets}")
            print_and_write_md(
                "Retrieved labels from the environment:\n" +
                f"{labels_retrieved_sets}", color=Fore.CYAN)
            retrieved_insights = [
                environment_record[tuple(label_set)]
                for label_set in labels_retrieved_sets
            ]
            insights_pre_subtask += "\n".join(
                [str(insight) for insight in retrieved_insights])
            print(Fore.CYAN + "Retrieved insights from the environment:\n" +
                  f"{insights_pre_subtask}")
            print_and_write_md(
                "Retrieved insights from the environment:\n" +
                f"{insights_pre_subtask}", color=Fore.CYAN)
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

        print(Fore.WHITE + "==========================================")
        print_and_write_md("==========================================",
                           color=Fore.WHITE)
        print(Fore.YELLOW + f"Subtask: \n{one_subtask}\n")
        print_and_write_md(f"Subtask: \n{one_subtask}\n", color=Fore.YELLOW)
        print(Fore.GREEN + f"AI Assistant Role: {ai_assistant_role}\n"
              f"{ai_assistant_description}\n")
        print_and_write_md(
            f"AI Assistant Role: {ai_assistant_role}\n" +
            f"{ai_assistant_description}\n", color=Fore.GREEN)
        print(Fore.BLUE + f"AI User Role: {ai_user_role}\n"
              f"{ai_user_description}\n")
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
        while n < chat_turn_limit:
            n += 1
            assistant_response, user_response = role_play_session.step(
                input_assistant_msg)

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

            # print_text_animated(
            #     Fore.BLUE +
            #     f"AI User: {ai_user_role}\n\n{user_response.msg.content}\n")
            # print_text_animated(Fore.GREEN +
            #                     f"AI Assistant: {ai_assistant_role}\n\n" +
            #                     f"{assistant_response.msg.content}\n")
            # print_text_animated()
            print(Fore.BLUE + f"AI User: {ai_user_role}\n\n" +
                  f"{user_response.msg.content}\n")
            print_and_write_md(
                f"AI User: {ai_user_role}\n\n" +
                f"{user_response.msg.content}\n", color=Fore.BLUE)
            print(Fore.GREEN + f"AI Assistant: {ai_assistant_role}\n\n" +
                  f"{assistant_response.msg.content}\n")
            print_and_write_md(
                f"AI Assistant: {ai_assistant_role}\n\n" +
                f"{assistant_response.msg.content}\n", color=Fore.GREEN)

            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break

            # Generate the insights from the chat history
            chat_history_assistant += (f"===== [{n}] ===== \n"
                                       f"{assistant_response.msg.content}\n")

            input_assistant_msg = assistant_response.msg

        insights_instruction = ("The CONTEXT TEXT is the chat history of " +
                                f"{ai_user_role} and {ai_assistant_role}. " +
                                "The INSIGHTs should come solely from the " +
                                "content of the conversation, not the " +
                                "conversation itsel.")
        insights = insight_agent.run(context_text=chat_history_assistant,
                                     insights_instruction=insights_instruction)
        print(Fore.CYAN + "Insights from the chat history:\n" +
              f"{json.dumps(insights, indent=4)}")
        print_and_write_md(
            "Insights from the chat history:\n" +
            f"{json.dumps(insights, indent=4)}", color=Fore.CYAN)
        insights_str = insight_agent.convert_json_to_str(insights)
        insights_subtasks[ID_one_subtask] = insights_str
        for insight in insights.values():
            if insight["entity_recognition"] is None:
                continue
            labels_key = tuple(insight["entity_recognition"])
            environment_record[labels_key] = insight


def print_and_write_md(text="", color=Fore.RESET):
    import html
    import re

    MD_FILE = "examples/multi_agent/multi-agent-output.md"
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
    task_prompt_trading_bot = "Develop a trading bot for the stock market."
    task_prompt_authentication = \
        "Implementing Authentication Middleware in a Node.js Application."
    task_prompt_supply_chain = """Ensure All Customer Orders Are Fulfilled Within the Stipulated Time Frame While Minimizing Total Operational Costs:
    - Ensure 200 units of Product X and 300 units of Product Y are delivered to Customer 1 within 10 days.
    - Ensure 150 units of Product X are delivered to Customer 2 within 15 days."""  # noqa: E501

    task_prompt_list = [
        task_prompt_trading_bot, task_prompt_authentication,
        task_prompt_supply_chain
    ]

    context_content_trading_bot = """### **Enterprise Overview:**
**Enterprise Name:** GlobalTradeCorp
**Industry:** Financial Technology
**Years in Business:** 15 years
**Key Business Area:** Developing trading algorithms and financial tools for institutions and retail traders.

### **Background & Need:**
GlobalTradeCorp has always been at the forefront of financial innovations. With the advent of algorithmic trading, our institution saw a rise in demand for automated tools that can aid both retail and institutional traders. Our clientele base, ranging from hedge funds to independent day traders, has been expressing the need for a sophisticated trading bot that can adapt to the ever-changing stock market dynamics.

### **Existing Infrastructure & Tools:**
- **Trading Platforms**: Our enterprise uses a mix of MetaTrader 4, Thinkorswim, and proprietary platforms for executing trades.
- **Data Feed**: We receive real-time data feeds from Bloomberg Terminal, which includes stock prices, news alerts, and other relevant trading information.
- **Cloud Infrastructure**: Most of our applications are hosted on AWS, leveraging services like EC2, RDS, and Lambda.
- **Current Bots**: We have a few basic trading bots in place, mainly for forex trading, based on predefined strategies like MACD crossovers and Bollinger Bands.

### **Objective of the New Trading Bot:**
The new trading bot should be able to:
1. Analyze large datasets in real-time, including stock prices, news feeds, and social media sentiments.
2. Make buy/sell decisions based on a mix of predefined strategies and adaptive AI algorithms.
3. Automatically adjust its strategies based on market conditions (e.g., bull markets, bear markets, high volatility).
4. Provide a user-friendly interface where traders can set their risk levels, investment amounts, and other preferences.
5. Offer simulation modes for back-testing strategies."""  # noqa: E501
    context_content_authentication = """### 1. Development Environment

- **Operating System**: macOS Big Sur
- **Development Tools**: Visual Studio Code, Postman
- **Version Control**: Git, GitHub
- **Programming Language**: JavaScript
- **Runtime Environment**: Node.js v16.13.0 (LTS)
- **Package Manager**: npm
- **Framework**: Express.js
- **Database**: MongoDB

### 2. Testing Environment

- **Testing Framework**: Jest
- **Assertion Library**: Built into Jest
- **End-to-End Testing**: Cypress
- **Load Testing**: Artillery
- **Continuous Integration**: GitHub Actions

### 3. Production Environment

- **Server**: AWS EC2 t4g.micro instance
- **Container Orchestration**: AWS ECS with Docker
- **CI/CD**: GitHub Actions
- **Logging Management**: ELK Stack
- **Monitoring**: AWS CloudWatch
- **Error Tracking**: Sentry
- **Security**: HTTPS via AWS Certificate Manager, Hashing and salting passwords using bcrypt
- **CDN**: AWS CloudFront

### 4. Configuration and Security

#### a. Authentication Middleware Configuration

- **Authentication Middleware**: Passport.js with JWT strategy
- **Environment Variable Management**: `.env` files with the `dotenv` package
- **Password Protection**: bcrypt for hashing and salting

#### b. Database Configuration

- **Database Engine**: Mongoose ODM for MongoDB
- **Connection Pooling**: Managed through MongoDB Atlas
- **ORM**: Mongoose

#### c. API Configuration

- **API Design**: RESTful API
- **Authentication**: JWT (JSON Web Tokens) using Passport.js
- **CORS**: Limited to a specific, trusted domain

### 5. Code and Architecture Best Practices

- **Architecture Pattern**: MVC (Model-View-Controller)
- **Linter**: ESLint
- **Formatter**: Prettier
- **Code Review**: Utilize GitHub's pull request review functionality
- **Testing**: Jest for unit testing, Cypress for E2E testing

### 6. Documentation and Support

- **Documentation**: API documentation created with Swagger
- **Code Documentation**: JSDoc
- **README**: Detailed project setup and usage guide on GitHub"""  # noqa: E501
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
    context_content_list = [
        context_content_trading_bot, context_content_authentication,
        context_content_supply_chain
    ]

    index = 2
    main(task_prompt=task_prompt_list[index],
         context_text=context_content_list[index])
