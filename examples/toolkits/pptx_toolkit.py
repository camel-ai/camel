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
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    # Initialize the toolkit with an output directory
    pptx_toolkit = PPTXToolkit(output_dir="./pptx_outputs")

    # Initialize the agent with the toolkit
    camel_agent = ChatAgent(
        system_message="You are a helpful assistant that can create PowerPoint presentations.",
        model=model,
        tools=pptx_toolkit.get_tools(),
    )

    print("=== PPTXToolkit Example Usage ===\n")

    # Example 1: Presentation with images
    print("Example 1: Creating a presentation with images")
    image_query = """Create a PowerPoint presentation about "Data Science Workflow" 
                     with a title slide and 2 content slides. Include placeholder images
                     for data visualization examples."""
    
    camel_agent.reset()
    response = camel_agent.step(image_query)
    print(response.msgs[0].content)
    print(f"Tool calls: {response.info['tool_calls']}")
    print("\n" + "="*50 + "\n")

    # Example 2: Direct toolkit usage (without agent)
    print("Example 2: Direct toolkit usage")
    
    # Define presentation content as JSON string
    import json
    presentation_content = [
        {
            "title": "My Custom Presentation",
            "subtitle": "Created with PPTXToolkit"
        },
        {
            "title": "First Topic",
            "text": "This is the main content of the first slide.\n\nIt can include multiple lines and bullet points."
        },
        {
            "title": "Second Topic with Image",
            "text": "This slide demonstrates image integration.",
            "image": "https://via.placeholder.com/400x300.png"
        },
        {
            "title": "Conclusion",
            "text": "Thank you for your attention!\n\nQuestions are welcome."
        }
    ]
    
    # Create the presentation directly
    result = pptx_toolkit.create_presentation(
        content=json.dumps(presentation_content),
        filename="custom_presentation.pptx"
    )
    print("Direct toolkit usage:")
    print(result)
    print("\n" + "="*50 + "\n")

    print("Both presentations have been created successfully!")
    print("Check the './pptx_outputs' directory for the generated PPTX files.")


if __name__ == "__main__":
    run_pptx_agent() 