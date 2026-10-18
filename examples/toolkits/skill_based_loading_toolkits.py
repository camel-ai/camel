# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Dict, List

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits.base import BaseToolkit
from camel.toolkits.skill_based.tool_loader import SkillBasedToolLoader
from camel.types import ModelPlatformType, ModelType


def get_token_count_from_response(response) -> int:
    r"""Extract total token count from agent response.

    Args:
        response: ChatAgentResponse object.

    Returns:
        int: Total token count.
    """
    if response.info and 'usage' in response.info:
        usage = response.info['usage']
        return usage.get('total_tokens', 0)
    return 0


def test_token_saving_small_scale():
    r"""Test token saving with small number of toolkits."""
    print("=" * 60)
    print("Test 1: Small Scale (5 toolkits)")
    print("=" * 60)

    from camel.toolkits import (
        ArxivToolkit,
        FileToolkit,
        CodeExecutionToolkit,
        SearchToolkit,
        WeatherToolkit,
    )

    toolkits: List[BaseToolkit] = [
        ArxivToolkit(),
        FileToolkit(),
        CodeExecutionToolkit(),
        SearchToolkit(),
        WeatherToolkit(),
    ]

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT
    )

    user_task = "Search for papers about machine learning on arXiv and download the first 3 papers."

    # Traditional approach
    print("\n[Traditional Approach]")
    all_tools = []
    for toolkit in toolkits:
        all_tools.extend(toolkit.get_tools())

    baseline_agent = ChatAgent(
        system_message="You are a helpful assistant. Select and use appropriate tools to complete the task.",
        tools=all_tools,
        model=model
    )

    baseline_response = baseline_agent.step(user_task)
    baseline_tokens = get_token_count_from_response(baseline_response)

    print(f"Total toolkits: {len(toolkits)}")
    print(f"Total tools: {len(all_tools)}")
    print(f"Total tokens: {baseline_tokens}")

    # Skill-based approach
    print("\n[Skill-Based Approach]")
    loader = SkillBasedToolLoader(toolkits)

    selected_toolkit_names, stage1_response = loader.select_toolkits_with_agent(
        user_task, model
    )
    stage1_tokens = get_token_count_from_response(stage1_response)

    selected_tools = loader.get_selected_tools()
    stage3_agent = ChatAgent(
        system_message="You are a helpful assistant. Use the selected tools to complete the task.",
        tools=selected_tools,
        model=model
    )
    stage3_response = stage3_agent.step(user_task)
    stage3_tokens = get_token_count_from_response(stage3_response)

    skill_total_tokens = stage1_tokens + stage3_tokens

    print(f"Selected toolkits: {selected_toolkit_names}")
    print(f"Selected tools: {len(selected_tools)}")
    print(f"Stage 1 tokens (toolkit selection): {stage1_tokens}")
    print(f"Stage 3 tokens (tool usage): {stage3_tokens}")
    print(f"Total tokens: {skill_total_tokens}")

    # Comparison
    print("\n[Comparison]")
    saved_tokens = baseline_tokens - skill_total_tokens
    saved_percentage = (saved_tokens / baseline_tokens * 100) if baseline_tokens > 0 else 0

    print(f"Baseline tokens: {baseline_tokens}")
    print(f"Skill-based tokens: {skill_total_tokens}")
    print(f"Saved tokens: {saved_tokens}")
    print(f"Saved percentage: {saved_percentage:.2f}%")

    return {
        "baseline_tokens": baseline_tokens,
        "skill_tokens": skill_total_tokens,
        "saved_tokens": saved_tokens,
        "saved_percentage": saved_percentage,
    }


def test_token_saving_large_scale():
    r"""Test token saving with large number of toolkits (20+)."""
    print("\n" + "=" * 60)
    print("Test 2: Large Scale (15+ toolkits)")
    print("=" * 60)

    from camel.toolkits import (
        ArxivToolkit,
        FileToolkit,
        CodeExecutionToolkit,
        MathToolkit,
        PubMedToolkit,
        SemanticScholarToolkit,
        ThinkingToolkit,
        SymPyToolkit,
        TaskPlanningToolkit,
        NoteTakingToolkit,
        ImageAnalysisToolkit,
        ExcelToolkit,
        PPTXToolkit,
        HumanToolkit,
        WebDeployToolkit,
        ScreenshotToolkit,
        PyAutoGUIToolkit,
        MarkItDownToolkit,
    )

    toolkits: List[BaseToolkit] = [
        ArxivToolkit(),
        FileToolkit(),
        CodeExecutionToolkit(),
        MathToolkit(),
        PubMedToolkit(),
        SemanticScholarToolkit(),
        ThinkingToolkit(),
        SymPyToolkit(),
        TaskPlanningToolkit(),
        NoteTakingToolkit(),
        ImageAnalysisToolkit(),
        ExcelToolkit(),
        PPTXToolkit(),
        HumanToolkit(),
        WebDeployToolkit(),
        ScreenshotToolkit(),
        PyAutoGUIToolkit(),
        MarkItDownToolkit(),
    ]

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT
    )

    user_task = "Search for machine learning papers on arXiv and give me the brief info about the title and authors of the first 3 papers."

    # Traditional approach
    print("\n[Traditional Approach]")
    all_tools = []
    for toolkit in toolkits:
        all_tools.extend(toolkit.get_tools())

    baseline_agent = ChatAgent(
        system_message="You are a helpful assistant. Select and use appropriate tools to complete the task.",
        tools=all_tools,
        model=model
    )

    baseline_response = baseline_agent.step(user_task)
    baseline_tokens = get_token_count_from_response(baseline_response)

    # Check if tools were called
    baseline_tool_calls = baseline_response.info.get('tool_calls', []) if baseline_response.info else []
    # for tool_call in baseline_tool_calls:
    #     print(f"Tool call: {tool_call}")
    baseline_tools_called = len(baseline_tool_calls) if baseline_tool_calls else 0

    print(f"Total toolkits: {len(toolkits)}")
    print(f"Total tools: {len(all_tools)}")
    print(f"Tools called: {baseline_tools_called}")
    print(f"Total tokens: {baseline_tokens}")
    print(f"Baseline response: {baseline_response.msg.content}")

    # Skill-based approach
    print("\n[Skill-Based Approach]")
    loader = SkillBasedToolLoader(toolkits)

    selected_toolkit_names, stage1_response = loader.select_toolkits_with_agent(
        user_task, model
    )
    stage1_tokens = get_token_count_from_response(stage1_response)

    selected_tools = loader.get_selected_tools()
    stage3_agent = ChatAgent(
        system_message="You are a helpful assistant. Use the selected tools to complete the task.",
        tools=selected_tools,
        model=model
    )
    stage3_response = stage3_agent.step(user_task)
    stage3_tokens = get_token_count_from_response(stage3_response)

    # for tool_call in stage3_response.info.get('tool_calls', []):
    #     print(f"Tool call: {tool_call}")
    stage3_tools_called = len(stage3_response.info.get('tool_calls', [])) if stage3_response.info.get('tool_calls', []) else 0

    skill_total_tokens = stage1_tokens + stage3_tokens

    print(f"Selected toolkits: {selected_toolkit_names}")
    print(f"Selected tools: {len(selected_tools)}")
    print(f"Stage 1 tokens (toolkit selection): {stage1_tokens}")
    print(f"Stage 3 tokens (tool usage): {stage3_tokens}")
    print(f"Total tokens: {skill_total_tokens}")
    print(f"Tools called: {stage3_tools_called}")
    print(f"Stage 3 response: {stage3_response.msg.content}")

    # Comparison
    print("\n[Comparison]")
    saved_tokens = baseline_tokens - skill_total_tokens
    saved_percentage = (saved_tokens / baseline_tokens * 100) if baseline_tokens > 0 else 0

    print(f"Baseline tokens: {baseline_tokens}")
    print(f"Skill-based tokens: {skill_total_tokens}")
    print(f"Saved tokens: {saved_tokens}")
    print(f"Saved percentage: {saved_percentage:.2f}%")

    return {
        "baseline_tokens": baseline_tokens,
        "skill_tokens": skill_total_tokens,
        "saved_tokens": saved_tokens,
        "saved_percentage": saved_percentage,
    }


if __name__ == "__main__":
    result1 = test_token_saving_small_scale()
    result2 = test_token_saving_large_scale()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Small scale saved: {result1['saved_percentage']:.2f}%")
    print(f"Large scale saved: {result2['saved_percentage']:.2f}%")

"""
============================================================
Test 1: Small Scale (5 toolkits)
============================================================

[Traditional Approach]
Total toolkits: 5
Total tools: 21
Total tokens: 177291

[Skill-Based Approach]
Selected toolkits: ['ArxivToolkit']
Selected tools: 2
Stage 1 tokens (toolkit selection): 1176
Stage 3 tokens (tool usage): 77838
Total tokens: 79014

[Comparison]
Baseline tokens: 177291
Skill-based tokens: 79014
Saved tokens: 98277
Saved percentage: 55.43%

============================================================
Test 2: Large Scale (15+ toolkits)
============================================================

[Traditional Approach]
Total toolkits: 18
Total tools: 102
Tools called: 2
Total tokens: 175132
Baseline response: Here are the brief information about the title and authors of the first 3 machine learning papers from the recent results:

1. Title: "Insights into Household Electric Vehicle Charging Behavior: Analysis and Predictive Modeling"
   Authors: Ahmad Almaghrebi, Kevin James, Fares al Juheshi, Mahmoud A. Alahmad

2. Title: "Abstractive text summarization of low-resourced languages using deep learning"
   Authors: Nida Shafiq, Isma Hamid, Muhammad Asif, Qamar Nawaz, Hanan Aljuaid, Hamid Ali

3. Title: "Detection of DDoS Attacks on Clouds Computing Environments Using Machine Learning Techniques"
   Authors: Iehab Alrassan, Asma Alqahtani

[Skill-Based Approach]
Selected toolkits: ['ArxivToolkit']
Selected tools: 2
Stage 1 tokens (toolkit selection): 2975
Stage 3 tokens (tool usage): 77764
Total tokens: 80739
Tools called: 1
Stage 3 response: Here is the brief information for the first 3 machine learning papers found on arXiv:

1. Title: Changing Data Sources in the Age of Machine Learning for Official Statistics
   Authors: Cedric De Boom, Michael Reusens
   URL: http://arxiv.org/abs/2306.04338v1

2. Title: DOME: Recommendations for supervised machine learning validation in biology
   Authors: Ian Walsh, Dmytro Fishman, Dario Garcia-Gasulla, Tiina Titma, Gianluca Pollastri, The ELIXIR Machine Learning focus group, Jen Harrow, Fotis E. Psomopoulos, Silvio C. E. Tosatto
   URL: http://arxiv.org/abs/2006.16189v4

3. Title: Learning Curves for Decision Making in Supervised Machine Learning: A Survey
   Authors: Felix Mohr, Jan N. van Rijn
   URL: http://arxiv.org/abs/2201.12150v2

If you want, I can provide summaries or download PDFs of these papers.

[Comparison]
Baseline tokens: 175132
Skill-based tokens: 80739
Saved tokens: 94393
Saved percentage: 53.90%

============================================================
Summary
============================================================
Large scale saved: 53.90%
"""