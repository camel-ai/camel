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

import asyncio

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    system_prompt = """You are an expert presentation designer. Generate a single-slide HTML document for a professional presentation.
Dont use ```html ``` at the beginning and end of the HTML code.
**IMPORTANT OUTPUT RULES:**
- Output ONLY the HTML code. No explanations, markdown, or extra text.
- The HTML must be a complete document, ready for direct use.

**TECHNICAL CONSTRAINTS:**
- Fixed slide size: width 1280px, height 720px (not responsive).
- Use only these HTML tags: div, h1-h6, p.
- For icons, use Font Awesome (via CDN) or Unicode emoji as fallback.
- Do NOT use Tailwind CSS, external CSS frameworks, or advanced CSS (no grid, no flex for main layout).
- All styles must be in a single <style> block in the <head>.
- Use only solid background colors (no gradients).
- Use Google Fonts (Montserrat for headings, Arial or Open Sans for body text) via CDN.

**VISUAL DESIGN GUIDELINES:**
- Minimalistic, clean, and professional look.
- Ample white space and clear visual hierarchy.
- Use soft, pastel, or neutral color palettes.
- Use card-like blocks with subtle box-shadows and rounded corners for sections or features.
- Align content in a visually balanced way (e.g., three feature cards in a row).
- Use large, bold headings and smaller, readable body text.
- Add a small, subtle footer with slide dimensions and branding.

**CONTENT STRUCTURE:**
- Prominent slide title at the top.
- Optional subtitle below the title.
- 2-4 feature cards/sections, each with:
    - An icon (Font Awesome or emoji)
    - A short title
    - A brief description
- Footer with slide size and branding.

**EXAMPLE LAYOUT:**
- Title
- Subtitle
- [Feature Card 1] [Feature Card 2] [Feature Card 3]
- Footer

**CONTENT GUIDELINES:**
- Make the content relevant and engaging for the given topic.
- Use clear, professional language.
- Balance text and visual elements for readability.

**OUTPUT FORMAT:**
- Complete HTML document with <!DOCTYPE html>, <html>, <head>, and <body>.
- All CSS in a <style> block in the <head>.
- All external resources (Font Awesome, Google Fonts) loaded via CDN.

The final output should be visually appealing, minimalistic, and ready for professional presentation use. Output ONLY the HTML code, nothing else."""
    # Load config from JSON file
    config_dict = "examples/toolkits/mcp_pptx_html/mcp_config.json"
    async with MCPToolkit(config_path=str(config_dict)) as mcp_toolkit:
        await mcp_toolkit.connect()
        tools = mcp_toolkit.get_tools()
        # print(tools[0].openai_tool_schema)
        model = ModelFactory.create(
            model_platform=ModelPlatformType.GEMINI,
            model_type=ModelType.GEMINI_2_0_FLASH,
        )
        html_agent = ChatAgent(
            system_message=system_prompt,
            model=model,
        )

        response = await html_agent.astep(
            "create presentation for the following topic: 'Camel-ai'"
        )

        # Save the HTML response to slide.html
        with open(
            "examples/toolkits/mcp_pptx_html/slide.html", "w", encoding="utf-8"
        ) as f:
            f.write(response.msg.content)

        result = await mcp_toolkit.call_tool(
            "convert_html_to_pptx",
            {
                "html": response.msg.content,
                "outputPath": "examples/toolkits/mcp_pptx_html/output/output.pptx",
            },
        )
        print(result)


asyncio.run(main())
