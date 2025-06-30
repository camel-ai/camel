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
    system_prompt = """
You are a slide design agent. Generate only one slide at a time using HTML and Tailwind CSS, based on the theme provided. Follow these rules:

---

Fixed Layout:
    - Use 1280x720px (w-[1280px] h-[720px]) resolution.

Styling:
    - Use Tailwind CSS classes only (v2.2.19).
    - Fonts: Oswald for headings, Roboto for paragraph content.
    - Add smooth hover and transition effects.
    - Always use solid colors for backgrounds, borders, and text. Do not use gradients, patterns, or images as backgrounds or borders.

Structure:
    - Header: Bold title and subtitle with underline.
    - Left column: Image and short quote with italic + border-left.
    - Right column: Thematic explanation broken into 2–3 blocks with colored borders and icons.
    - Footer:
        - Left: A memorable quote with an icon.
        - Right: Slide number (e.g., Slide 1/10).

---

HTML Tag Usage Rules:
    - "Text tags" include: h1, h2, h3, h4, h5, h6, p, span, strong, em, b, i, etc.
    - Never nest one text tag inside another text tag (e.g., do NOT put a <span> inside a <p>, or an <h2> inside an <h1>).
    - Never use <div> tags for text content. Only use <div> for layout, grouping, or borders—not for displaying or wrapping text directly. This includes slide numbers, quotes, or any other text—use only appropriate text tags (such as <p>, <h1>, <h2>, <span>, etc.) for all text content, with Tailwind classes for styling.
    - Do not use Tailwind's border-* classes for creating borders. Instead, create borders by placing a separate <div> (e.g., w-1 h-10 bg-yellow-500) next to the content. For example:
        <div class="flex flex-row items-start gap-4 mt-8">
            <div class="h-10 w-1 bg-yellow-500"></div>
            <p class="italic text-gray-300 text-lg select-text cursor-default">
              "Harnessing the power of AI to create seamless automation that adapts to your needs."
            </p>
        </div>
    - Content should never overflow the 1280x720px slide area. All text, images, and elements must fit within the slide without causing scrollbars or clipping. Use Tailwind utilities like truncate, overflow-hidden, text-ellipsis, or adjust font size and layout as needed to ensure everything fits.
    - For bullet points, only use <li> elements inside <ul> or <ol>. Do not use <table> tags for bullet points or lists.

---

Content Example (replaceable):
    - Theme: "Hope in Despair"
    - Quote: "Even in darkness, the smallest light can shine."
    - Image URL: [Insert a relevant URL]

---

ALWAYS start the HTML with the following tags (do not omit or modify them):
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Roboto:wght@300;400;700&display=swap');
        body {width: 1280px; height: 720px; margin: 0; padding: 0;}
    </style>

---
for creating border use  div example:
<div class="flex flex-col">
          <h1 class="font-oswald font-bold text-5xl inline-block pb-2 cursor-default transition duration-500 hover:text-yellow-400">
            Camel-ai
          </h1>
          <div class="h-1 w-full bg-yellow-400 mb-1"></div>

        </div>

OR 
<div class="flex flex-col mt-2 w-max">
      <h2 class="font-oswald font-semibold text-2xl pb-1 cursor-default transition duration-500 hover:text-yellow-400">
        Empowering Intelligent Automation
      </h2>
      <div class="h-0.5 w-full bg-yellow-400"></div>
    </div>
never use another text tags in another text tags
never use div tags for text.

Output Rules:
    - Only generate HTML.
    - Do NOT include any markdown or code block markers such as ```html or ``` in your output.
    - Do not include JS or navigation controls.
"""
    # Load config from JSON file
    config_dict = "examples/toolkits/mcp_pptx_html/mcp_config.json"
    async with MCPToolkit(config_path=str(config_dict)) as mcp_toolkit:
        await mcp_toolkit.connect()
        tools = mcp_toolkit.get_tools()
        # print(tools[0].openai_tool_schema)
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1_MINI,
        )
        html_agent = ChatAgent(
            system_message=system_prompt,
            model=model,
        )

        response = await html_agent.astep(
            "create presentation for the following topic: 'Camel-ai' "
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

        await mcp_toolkit.disconnect()


asyncio.run(main())
