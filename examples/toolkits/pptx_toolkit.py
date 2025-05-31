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
    # Make sure to set the PEXEL_API_KEY environment variable
    os.environ['PEXEL_API_KEY'] = 'your_api_key_here'

    # Initialize the model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Initialize the toolkit with an output directory
    pptx_toolkit = PPTXToolkit(
        output_dir="./pptx_outputs",
    )

    # Initialize the agent with the toolkit
    system_message = """You are a helpful assistant that can create PowerPoint presentations.
    When creating presentations, you must first select the appropriate template based on the topic:

    Available Templates:
    1. Modern Template (modern.pptx)
       - Best for: Technology, Innovation, Digital topics
       - Path: examples/toolkits/templates/modern.pptx

    2. Business Template (Ion_Boardroom.pptx)
       - Best for: Business, Corporate, Professional topics
       - Path: examples/toolkits/templates/Ion_Boardroom.pptx

    3. Education Template (Urban_monochrome.pptx)
       - Best for: Education, Learning, Academic topics
       - Path: examples/toolkits/templates/Urban_monochrome.pptx

    After selecting the appropriate template, output the content in the following JSON format and use the create_presentation tool to generate the PPTX file:

    [
        {
            "title": "Presentation Title",
            "subtitle": "Presentation Subtitle"
        },
        {
            "heading": "Slide Title",
            "bullet_points": [
                "**Bold text** for emphasis",
                "*Italic text* for additional emphasis",
                "Regular text for normal content"
            ],
            "img_keywords": "relevant search terms for images"
        },
        {
            "heading": "Step-by-Step Process",
            "bullet_points": [
                ">> **Step 1:** First step description",
                ">> **Step 2:** Second step description",
                ">> **Step 3:** Third step description"
            ],            
            "img_keywords": "process workflow steps"
        },
        {
            "heading": "Comparison Table",
            "table": {
                "headers": ["Column 1", "Column 2", "Column 3"],
                "rows": [
                    ["Row 1, Col 1", "Row 1, Col 2", "Row 1, Col 3"],
                    ["Row 2, Col 1", "Row 2, Col 2", "Row 2, Col 3"]
                ]
            },            
            "img_keywords": "comparison visualization"
        }
    ]

    Special formatting rules:
    1. Use **text** for bold text
    2. Use *text* for italic text
    3. Use >> at the start of bullet points for step-by-step processes
    4. Use proper JSON formatting with double quotes for all strings
    5. Add img_keywords field to include relevant images from Pexels

    IMPORTANT: 
    1. First, analyze the presentation topic and select the most appropriate template
    2. Then create the JSON content following the format above
    3. Finally, use the create_presentation tool to generate the PPTX file with the selected template

    Example tool usage:
    create_presentation(content='[{"title": "Example", "subtitle": "Demo"}]', filename="example.pptx", template="/examples/toolkits/templates/modern.pptx")
    """

    camel_agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=pptx_toolkit.get_tools(),
    )

    print("=== PPTXToolkit Example Usage ===\n")

    # Example 1: Presentation with various slide types
    print("Example 1: Creating a presentation with various slide types")
    presentation_query = """Create a PowerPoint presentation about \"Camel-ai\" 
                          that demonstrates different slide types including:
                          - A title slide
                          - A slide with bullet points and bold/italic text
                          - A step-by-step process slide
                          - A comparison table slide
                          - Include relevant images for each slide using img_keywords
                          
                          After creating the JSON content, use the create_presentation tool to generate the PPTX file."""

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
            "img_keywords": "https://images.pexels.com/photos/2014773/pexels-photo-2014773.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
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
    )
    print("Direct toolkit usage:")
    print(result)
    print("\n" + "=" * 50 + "\n")

    print("Both presentations have been created successfully!")
    print("Check the './pptx_outputs' directory for the generated PPTX files.")


if __name__ == "__main__":
    run_pptx_agent()


"""
=== PPTXToolkit Example Usage ===

Example 1: Creating a presentation with various slide types
OK. I've created a PowerPoint presentation about Camel-AI, including a title slide, bullet point slide, 
step-by-step process slide, and a comparison table slide. I've also added relevant image keywords for each slide.
 The presentation has been saved as "camel_ai_presentation.pptx" using the modern template.

Tool calls: [ToolCallingRecord(tool_name='create_presentation', args={'filename': 'camel_ai_presentation.pptx', 
'content': '[{"title": "Camel-AI: An Overview", "subtitle": "Conversational AI Made Accessible"}, {"heading": "What is Camel-AI?", 
"bullet_points": ["**Camel-AI** is a framework for building *conversational AI* agents.", "It simplifies the process of creating 
and managing complex dialogues.", "Key features include: role-playing, multi-agent collaboration, and task-oriented conversations."],
"img_keywords": "conversational AI agents"}, {"heading": "Building a Camel-AI Agent: Step-by-Step", 
"bullet_points": [">> **Step 1:** Define the roles and objectives of each agent.", ">> **Step 2:** Design the conversation flow and 
interaction protocols.", ">> **Step 3:** Implement the agent logic using the Camel-AI framework.", ">> **Step 4:** Test and refine
the agent through simulations and real-world interactions."], "img_keywords": "AI agent workflow"}, {"heading": "Camel-AI vs.
Traditional Chatbots", "table": {"headers": ["Feature", "Camel-AI", "Traditional Chatbots"], "rows": [["Complexity", "Handles complex, 
multi-agent dialogues", "Limited to simple, single-turn conversations"], ["Role-Playing", "Supports diverse roles and personalities", 
"Typically lacks role-playing capabilities"], ["Task-Oriented", "Designed for collaborative task completion", "Often focused on 
information retrieval"]] }, "img_keywords": "AI chatbot comparison"}]', 'template': 'examples/toolkits/templates/modern.pptx'}, 
result='PowerPoint presentation successfully created:camel/pptx_outputs/camel_ai_presentation.pptx', 
tool_call_id='')]

==================================================

Example 2: Direct toolkit usage with advanced features
Direct toolkit usage:
PowerPoint presentation successfully created: camel/pptx_outputs/modern_development.pptx

==================================================

Both presentations have been created successfully!
Check the './pptx_outputs' directory for the generated PPTX files."""
# ruff: noqa: E501
