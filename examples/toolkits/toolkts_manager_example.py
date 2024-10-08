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
from camel.toolkits import ToolManager
from camel.toolkits.github_toolkit import GithubToolkit
from camel.toolkits.openai_function import OpenAIFunction


def pretty_print_list(title, items):
    print(f"\n{'=' * 40}\n{title}:\n{'-' * 40}")
    if not items:
        print("  (No project)")
    else:
        for index, item in enumerate(items, start=1):
            print(f"  {index}. {item}")
    print('=' * 40)


manager = ToolManager()

toolkits = manager.list_toolkits()
toolkit_classes = manager.list_toolkit_classes()

pretty_print_list("Function Toolkits", toolkits)
pretty_print_list("Class Toolkits", toolkit_classes)

matching_toolkits_test = manager.search_toolkits('weather')
pretty_print_list("Matching Toolkit", matching_toolkits_test)


def strict_search_algorithm(keyword: str, description: str) -> bool:
    return keyword.lower() in description.lower()


matching_toolkits_custom = manager.search_toolkits(
    'weather', algorithm=strict_search_algorithm
)
pretty_print_list(
    "Custom Algorithm Matching Toolkit", matching_toolkits_custom
)

tool = manager.get_toolkit('get_weather_data')
if isinstance(tool, OpenAIFunction):
    print("\nFunction Description:")
    print('-' * 40)
    print(tool.get_function_description())

camel_github_toolkit = GithubToolkit(repo_name='camel-ai/camel')
crab_github_toolkit = GithubToolkit(repo_name='ZackYule/crab')

manager.add_toolkit_from_instance(
    camel_github_toolkit=camel_github_toolkit,
    crab_github_toolkit=crab_github_toolkit,
)

matching_tools_for_github = manager.search_toolkits('github')
pretty_print_list("Matching Tools for GitHub", matching_tools_for_github)

if isinstance(matching_tools_for_github, list):
    tools_instances = manager.get_toolkits(names=matching_tools_for_github)
    pretty_print_list("Tools Instances", tools_instances)

"""
===============================================================================
========================================
Function Toolkits:
----------------------------------------
  1. get_dalle_img
  2. get_github_access_token
  3. add
  4. mul
  5. sub
  6. query_wolfram_alpha
  7. search_duckduckgo
  8. search_google
  9. search_wiki
  10. get_openweathermap_api_key
  11. get_weather_data
========================================

========================================
Class Toolkits:
----------------------------------------
  1. BaseToolkit: 
  2. CodeExecutionToolkit: 
  3. DalleToolkit: 
  4. GithubIssue: 
  5. GithubPullRequest: 
  6. GithubPullRequestDiff: 
  7. GithubToolkit: create_pull_request, retrieve_issue, retrieve_issue_list, 
  retrieve_pull_requests
  8. GoogleMapsToolkit: 
  9. LinkedInToolkit: 
  10. MathToolkit: 
  11. OpenAPIToolkit: 
  12. OpenAIFunction: 
  13. RedditToolkit: 
  14. RetrievalToolkit: 
  15. SearchToolkit: 
  16. SlackToolkit: 
  17. ToolManager: 
  18. TwitterToolkit: 
  19. WeatherToolkit: 
========================================

========================================
Matching Toolkit:
----------------------------------------
  1. get_openweathermap_api_key
  2. get_weather_data
========================================

========================================
Custom Algorithm Matching Toolkit:
----------------------------------------
  1. get_openweathermap_api_key
  2. get_weather_data
========================================

Function Description:
----------------------------------------
Fetch and return a comprehensive weather report for a given city
as a string. The report includes current weather conditions,
temperature, wind details, visibility, and sunrise/sunset times,
all formatted as a readable string.

The function interacts with the OpenWeatherMap API to
retrieve the data.

========================================
Matching Tools for GitHub:
----------------------------------------
  1. get_github_access_token
  2. camel_github_toolkit_create_pull_request
  3. camel_github_toolkit_retrieve_issue
  4. camel_github_toolkit_retrieve_issue_list
  5. camel_github_toolkit_retrieve_pull_requests
  6. crab_github_toolkit_create_pull_request
  7. crab_github_toolkit_retrieve_issue
  8. crab_github_toolkit_retrieve_issue_list
  9. crab_github_toolkit_retrieve_pull_requests
========================================

========================================
Tools Instances:
----------------------------------------
  1. <function get_github_access_token at 0x1070d04c0>
  2. <bound method GithubToolkit.create_pull_request of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x1070ed150>>
  3. <bound method GithubToolkit.retrieve_issue of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x1070ed150>>
  4. <bound method GithubToolkit.retrieve_issue_list of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x1070ed150>>
  5. <bound method GithubToolkit.retrieve_pull_requests of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x1070ed150>>
  6. <bound method GithubToolkit.create_pull_request of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x11759b0a0>>
  7. <bound method GithubToolkit.retrieve_issue of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x11759b0a0>>
  8. <bound method GithubToolkit.retrieve_issue_list of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x11759b0a0>>
  9. <bound method GithubToolkit.retrieve_pull_requests of <camel.toolkits.
  github_toolkit.GithubToolkit object at 0x11759b0a0>>
========================================
===============================================================================
"""
