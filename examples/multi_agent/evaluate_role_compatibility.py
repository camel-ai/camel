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

from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig


def main(model_type=None) -> None:
    role_description_dict = {
        "Software Engineer":
        ("Competencies: Proficiency in programming languages such as "
         "Python, Java, or C++, knowledge of algorithms and data structures, "
         "experience with software development methodologies. "
         "Characteristics: Analytical thinking, problem-solving skills, "
         "attention to detail, ability to work in a team. Duties and "
         "workflows: Design and develop the trading bot software, implement "
         "algorithms for analyzing market data, integrate with stock market "
         "APIs, conduct testing and debugging, collaborate with other experts "
         "to ensure smooth functioning of the bot."),
        "Financial Analyst":
        ("Competencies: Strong understanding of financial markets and trading "
         "strategies, knowledge of technical and fundamental analysis, "
         "familiarity with financial modeling and forecasting techniques. "
         "Characteristics: Analytical mindset, ability to interpret market "
         "trends, attention to detail, good communication skills. Duties and "
         "workflows: Analyze market data and identify potential trading "
         "opportunities, develop and optimize trading strategies, perform "
         "risk assessments, provide insights and recommendations to the "
         "software engineer for implementing trading algorithms."),
        "Data Scientist":
        ("Competencies: Proficiency in programming languages such as Python "
         "or R, expertise in statistical analysis and machine learning "
         "algorithms, knowledge of data visualization techniques. "
         "Characteristics: Strong analytical and problem-solving skills, "
         "ability to work with large datasets, curiosity and creativity. "
         "Duties and workflows: Collect and preprocess market data, perform "
         "exploratory data analysis, develop predictive models for stock "
         "price movements, evaluate and fine-tune the performance of the "
         "trading bot using historical data, collaborate with the software "
         "engineer to integrate data-driven features into the bot."),
        "Risk Manager":
        ("Competencies: Knowledge of risk management principles and "
         "techniques, familiarity with financial regulations, understanding "
         "of market dynamics and volatility. Characteristics: Strong "
         "analytical and critical thinking skills, attention to detail, "
         "ability to make informed decisions under uncertainty. Duties and "
         "workflows: Assess and monitor the risks associated with the trading "
         "bot's strategies, develop risk mitigation strategies, implement "
         "risk management protocols, collaborate with the financial analyst "
         "and software engineer to ensure compliance with regulations and "
         "risk management best practices.")
    }
    one_subtask = "Collect and preprocess market data."

    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)

    role_compatibility_scores_dict = (
        role_assignment_agent.evaluate_role_compatibility(
            one_subtask, role_description_dict))

    print(Fore.YELLOW + f"One specific subtask prompt:\n{one_subtask}\n")
    for (role_name, score) in role_compatibility_scores_dict.items():
        print(Fore.GREEN + f"Score of {role_name}: {score}")

    if role_compatibility_scores_dict is None:
        raise ValueError("role_compatibility_scores_dict is None.")
    len_role_compatibility_scores_dict = len(role_compatibility_scores_dict)
    len_role_description_dict = len(role_description_dict)
    if (len_role_compatibility_scores_dict != len_role_description_dict):
        raise ValueError(f"Length of role_compatibility_scores_dict "
                         f"({len_role_compatibility_scores_dict}) "
                         f"does not equal to length of role_description_dict "
                         f"({len_role_description_dict}).")


if __name__ == "__main__":
    main()
