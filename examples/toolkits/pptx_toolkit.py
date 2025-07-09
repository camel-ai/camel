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
"""
Example usage of the PPTXToolkit for creating PowerPoint presentations.
"""

import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PPTXToolkit
from camel.types import ModelPlatformType, ModelType


def run_pptx_agent():
    # Set the PEXELS_API_KEY for Pexels image fetching
    os.environ['PEXELS_API_KEY'] = 'your_api_key_here'

    # Initialize the model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Initialize the toolkit with an output directory
    pptx_toolkit = PPTXToolkit(
        working_directory="./pptx_outputs",
    )

    # Initialize the agent with the toolkit
    system_message = """You are a helpful assistant that can create PowerPoint 
    presentations.
    When creating presentations, you must first select the appropriate 
    template based on the topic:

    Available Templates:
    1. Modern Template (modern.pptx)
       - Best for: Technology, Innovation, Digital topics
       - Path: examples/toolkits/slides_templates/modern.pptx

    2. Business Template (ion_boardroom.pptx)
       - Best for: Business, Corporate, Professional topics
       - Path: examples/toolkits/slides_templates/ion_boardroom.pptx

    3. Education Template (urban_monochrome.pptx)
       - Best for: Education, Learning, Academic topics
       - Path: examples/toolkits/slides_templates/urban_monochrome.pptx

    Special formatting rules:
    1. Use **text** for bold text
    2. Use *text* for italic text
    3. Use >> at the start of bullet points for step-by-step processes
    4. Use proper JSON formatting with double quotes for all strings
    5. Add img_keywords field to include relevant images from Pexels

    IMPORTANT: 
    1. First, analyze the presentation topic and select the most appropriate 
    template
    2. Then create the JSON content following the format above
    3. Finally, use the create_presentation tool to generate the PPTX file 
    with the selected template

    Example tool usage:
    create_presentation(content='[{"title": "Example", "subtitle": "Demo"}]', 
    filename="example.pptx", template="/examples/toolkits/slides_templates/
    modern.pptx")
    """

    camel_agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=pptx_toolkit.get_tools(),
    )

    print("=== PPTXToolkit Example Usage ===\n")

    # Example 1: Presentation with various slide types
    print("Example 1: Creating a presentation with various slide types")
    presentation_query = """Create a PowerPoint presentation about 
    \"CAMEL-AI\" based on the content below: 
    CAMEL: The first and the best multi-agent framework. We are working on 
    finding the scaling laws of Agents. We believe that studying these agents 
    on a large scale offers valuable insights into their behaviors, 
    capabilities, and potential risks. To facilitate research in this field, 
    we implement and support various types of agents, tasks, prompts, models, 
    and simulated environments.

    The CAMEL project is building the foundational infrastructure for AI 
    agents: collaborative, tool-using agents that operates in complex, 
    real-world environments.

    Our open-source framework empowers researchers and developers to rapidly 
    build and experiment with multi-agent systems. These agents are powered by 
    large language models (LLMs) and can interact with real-world 
    tools—including terminals, web browsers, code execution, and 
    APIs—unlocking high-value applications across enterprise automation, 
    simulation, and AI research.

    CAMEL is already gaining significant traction: over 200 contributors have 
    supported the project globally, our community spans more than 10,000 
    active members on private channels like Discord and Slack, and our work 
    has been cited more than 700 times in academic literature. CAMEL is widely 
    used in research, education, and industry to develop agentic systems and 
    drive innovation at the frontier of AI agent research.

    We believe CAMEL is well-positioned to become the core infrastructure 
    layer for safe, scalable, and intelligent multi-agent systems in the 
    emerging agent economy.
    """

    camel_agent.reset()
    response = camel_agent.step(presentation_query)
    print(response.msgs[0].content)
    print(f"Tool calls: {response.info['tool_calls']}")
    print("\n" + "=" * 50 + "\n")

    # Example 2: Direct toolkit usage with advanced features
    print("Example 2: Direct toolkit usage with advanced features")

    # Define presentation content as JSON string
    import json

    presentation_content = [
        {
            "title": "Modern Software Development",
            "subtitle": "Best Practices and Tools",
        },
        {
            "heading": "Key Development Principles",
            "bullet_points": [
                "**Agile** methodology for flexible development",
                "*Continuous Integration* and *Continuous Deployment*",
                "**Test-Driven Development** (TDD)",
                "Code review and pair programming",
                "Documentation and knowledge sharing",
            ],
            "img_keywords": "software development team collaboration",
        },
        {
            "heading": "Step-by-Step: Development Workflow",
            "bullet_points": [
                ">> **Step 1:** Plan and gather requirements",
                ">> **Step 2:** Design system architecture",
                ">> **Step 3:** Implement features",
                ">> **Step 4:** Write and run tests",
                ">> **Step 5:** Deploy and monitor",
            ],
            "img_keywords": "software development workflow process",
        },
        {
            "heading": "Best Practices Summary",
            "bullet_points": [
                "Write clean, maintainable code",
                "Automate testing and deployment",
                "Monitor and optimize performance",
                "Keep security in mind",
                "Document everything",
            ],
            "img_keywords": "https://images.pexels.com/photos/2014773"
            "/pexels-photo-2014773.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750"
            "&dpr=1",
        },
        {
            "heading": "Development Approaches Comparison",
            "table": {
                "headers": ["Approach", "Pros", "Cons"],
                "rows": [
                    [
                        "Waterfall",
                        "Clear structure, predictable",
                        "Less flexible, slow to adapt",
                    ],
                    [
                        "Agile",
                        "Flexible, iterative",
                        "Requires discipline, can be chaotic",
                    ],
                    [
                        "DevOps",
                        "Fast delivery, automation",
                        "Complex setup, requires expertise",
                    ],
                    [
                        "Lean",
                        "Efficient, waste reduction",
                        "Requires cultural change",
                    ],
                ],
            },
            "img_keywords": "software development methodologies comparison",
        },
    ]

    # Create the presentation directly
    result = pptx_toolkit.create_presentation(
        content=json.dumps(presentation_content),
        filename="modern_development.pptx",
        template="examples/toolkits/slides_templates/ion_boardroom.pptx",
    )
    print("Direct toolkit usage:")
    print(result)
    print("\n" + "=" * 50 + "\n")

    print("Both presentations have been created successfully!")
    print("Check the './pptx_outputs' directory for the generated PPTX files.")


if __name__ == "__main__":
    run_pptx_agent()


"""
===============================================================================
=== PPTXToolkit Example Usage ===

Example 1: Creating a presentation with various slide types
The PowerPoint presentation titled "CAMEL-AI: The First Multi-Agent Framework" 
has been successfully created. You can download it using the link below:

[Download CAMEL-AI Presentation](sandbox:/Users/enrei/Desktop/camel0508/camel/
pptx_outputs/camel_ai_presentation.pptx)
Tool calls: [ToolCallingRecord(tool_name='create_presentation', args=
{'content': '[{"title": "CAMEL-AI","subtitle": "The First Multi-Agent 
Framework"},{"heading": "Introduction to CAMEL","bullet_points":[">> 
Multi-agent framework for AI research.",">> Focus on the scaling laws of 
agents.",">> Insights into behavior, capabilities, and risks."],
"img_keywords":"AI research, agents"},{"heading": "Key Features",
"bullet_points":[">> Collaborative, tool-using agents for real-world 
environments.",">> Open-source framework for rapid development and 
experimentation.",">> Powered by large language models (LLMs)."],
"img_keywords":"collaboration, technology"},{"heading": "Applications of 
CAMEL","bullet_points":[">> Interaction with real-world tools: terminals, web 
browsers, APIs.",">> Enterprise automation and simulation applications.",">> 
Significant contributions to AI research."],"img_keywords":"application of AI, 
technologies"},{"heading": "Community and Impact","bullet_points":[">> Over 
200 global contributors or supporters.",">> Community of more than 10,000 
active members on Discord and Slack.",">> Over 700 citations in academic 
literature."],"img_keywords":"community, collaboration"},{"heading": "Future 
of CAMEL","bullet_points":[">> Core infrastructure for multi-agent systems in 
agent economy.",">> Positioned for safe and scalable intelligent systems."],
"img_keywords":"future of technology, AI"}]', 'filename': 
'camel_ai_presentation.pptx', 'template': '/examples/toolkits/templates/modern.
pptx'}, result='PowerPoint presentation successfully created: /Users/enrei/
Desktop/camel0508/camel/pptx_outputs/camel_ai_presentation.pptx', 
tool_call_id='call_DwygLSSBGGG9c6kXgQt3sFO5')]

==================================================

Example 2: Direct toolkit usage with advanced features
Direct toolkit usage:
PowerPoint presentation successfully created: /Users/enrei/Desktop/camel0508/
camel/pptx_outputs/modern_development.pptx

==================================================

Both presentations have been created successfully!
Check the './pptx_outputs' directory for the generated PPTX files.
===============================================================================
"""
