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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PPTXToolkit
from camel.types import ModelPlatformType, ModelType


def run_pptx_agent():
    # Initialize the model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_2_0_FLASH,
    )

    # Initialize the toolkit with an output directory
    pptx_toolkit = PPTXToolkit(output_dir="./pptx_outputs")

    # Initialize the agent with the toolkit
    system_message = """You are a helpful assistant that can create PowerPoint presentations.
    When creating presentations, you must output the content in the following JSON format and use the create_presentation tool to generate the PPTX file:

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
            "key_message": "Optional key message for the slide"
        },
        {
            "heading": "Step-by-Step Process",
            "bullet_points": [
                ">> **Step 1:** First step description",
                ">> **Step 2:** Second step description",
                ">> **Step 3:** Third step description"
            ],
            "key_message": "Optional key message for the process"
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
            "key_message": "Optional key message for the table"
        }
    ]

    Special formatting rules:
    1. Use **text** for bold text
    2. Use *text* for italic text
    3. Use >> at the start of bullet points for step-by-step processes
    4. Include a key_message field when you want to highlight important points
    5. Use proper JSON formatting with double quotes for all strings

    IMPORTANT: After creating the JSON content, you MUST use the create_presentation tool to generate the PPTX file.
    Example tool usage:
    create_presentation(content='[{"title": "Example", "subtitle": "Demo"}]', filename="example.pptx")
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
                          - A slide with a key message
                          
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
            "key_message": "Modern development focuses on collaboration and continuous improvement",
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
            "key_message": "A structured workflow ensures quality and efficiency",
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
            "key_message": "**Success in software development comes from following best practices consistently**",
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
            "key_message": "Choose the approach that best fits your team and project",
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

# ruff: noqa: E501
