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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import ZhiPuToolkit, FunctionTool
from camel.types import ModelPlatformType, ModelType

# Create a Model
model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Initialize the ZhiPuToolkit
zhipu_toolkit = ZhiPuToolkit().ai_drawing
tools = [FunctionTool(zhipu_toolkit)]

# Set up the ChatAgent with thinking capabilities
sys_msg = (
    "You are an assistant that can use other agents to complete tasks."
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

usr_msg = """
Help me draw a picture of a cat.
"""

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

# ruff: noqa: E501
"""
===============================================================================
Here is the drawing of a cute and playful cat sitting on a windowsill:

![Cat Drawing](https://sfile.chatglm.cn/testpath/gen-1744186721453265884_0.png)

You can choose one of the following options to continue:

1. 🎨 **Transform Style** - Change this drawing to a Van Gogh style, adding vibrant colors and dynamic brush strokes.
2. 🌟 **Add Elements** - Include a small bird in the scene, making it look like the cat is interacting with the bird.
3. 📚 **Comic Strip** - Generate another image showing the cat jumping down from the windowsill to chase a butterfly.
4. 💡 **Enhance Tips** - Suggest making the flowers on the windowsill more vibrant and adding details like small decorations to enrich the scene.

Please let me know your choice!

Tool calls:
[ToolCallingRecord(tool_name='ai_drawing', args={'prompt': 'A cute and playful cat sitting on a windowsill, looking outside with bright green eyes. The background shows a sunny day with blue skies and fluffy clouds.', 'file_path': None}, result="DrawingToolOutput(image='https://sfile.chatglm.cn/testpath/gen-1744186721453265884_0.png')这是一幅描绘一只可爱、活泼的猫咪坐在窗台上的画。它用明亮的绿色眼睛望着窗外,背景是晴朗的一天,蓝天上飘着蓬松的云朵。\n\n接下来,您可以选择以下四个选项之一来继续生成图片:\n\n1. 🎨 选项1 **转变风格** —— 将这幅画转变为梵高风格的画作,增加梵高特有的鲜艳色彩和动感笔触。\n2. 🌟 选项2 **增加元素** —— 在画面中增加一只小鸟,让猫咪看起来像是在和小鸟互动。\n3. 📚 选项3 **连环画** —— 继续生成一张图,展示猫咪从窗台跳下,开始追逐一只蝴蝶的情景。\n4. 💡 选项4 **提升 tips** —— 建议将窗台上的花朵画得更鲜艳一些,并增加一些细节,如窗台上摆放的小饰品,来丰富画面内容。\n\n请告诉我您的选择！", tool_call_id='call_XW4NuDb54ejFH5zBlkdokClZ')]
===============================================================================
"""

zhipu_toolkit = ZhiPuToolkit().data_analysis
tools = [FunctionTool(zhipu_toolkit)]

usr_msg = """
Make a line chart of Beijing's temperature in the next seven days.
"""

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

# ruff: noqa: E501
"""
===============================================================================
Here is the line chart showing the temperature forecast for Beijing over the next seven days:

![Beijing Temperature Forecast](https://sfile.chatglm.cn/img2text/be415fe4-c41d-4ea3-8614-1a49c9becde3.jpg)

The chart displays the dates on the x-axis and the corresponding temperatures in degrees Celsius on the y-axis. Each point represents the forecasted temperature for a specific day.

Tool calls:
[ToolCallingRecord(tool_name='data_analysis', args={'prompt': 'Create a line chart showing the temperature forecast for Beijing over the next seven days.', 'file_path': None}, result="CodeInterpreterToolOutput(type='logs', logs='https://sfile.chatglm.cn/img2text/be415fe4-c41d-4ea3-8614-1a49c9becde3.jpg', error_msg=None)Here is a line chart showing the temperature forecast for Beijing over the next seven days. The chart displays the dates on the x-axis and the corresponding temperatures in degrees Celsius on the y-axis. The data points are connected by a blue line, and each point represents the forecasted temperature for a specific day.", tool_call_id='call_22lrsWel28CV43qxojME2bGY')]
===============================================================================
"""

zhipu_toolkit = ZhiPuToolkit().draw_flowchart
tools = [FunctionTool(zhipu_toolkit)]

input_file = "/Users/suntao/Documents/GitHub/camel/CONTRIBUTING.md"

usr_msg = f"""
tell me if want to contribute to camel, how to do it. 
here is the reference file: {input_file},draw a flowchart of the file.
"""

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])


# ruff: noqa: E501
"""
===============================================================================
I have created a flowchart based on the contents of the `CONTRIBUTING.md` file for the Camel project. The flowchart outlines the steps and guidelines for contributing. You can view it below:

![Camel Project Contribution Flowchart](https://sfile.chatglm.cn/mermaid/bcbdc7cb-52be-4aee-9f3d-3612184728af.png)

This visual representation summarizes the various steps involved in contributing to the Camel project. If you have any specific questions or need further details, feel free to ask!

Tool calls:
[ToolCallingRecord(tool_name='draw_flowchart', args={'prompt': 'Create a flowchart based on the contents of the CONTRIBUTING.md file for the Camel project, outlining the steps and guidelines for contributing.', 'file_path': '/Users/suntao/Documents/GitHub/camel/CONTRIBUTING.md'}, result='To create a flowchart based on the contents of the `CONTRIBUTING.md` file for the Camel project, I will first analyze the document to identify the key steps and guidelines for contributing. Then, I will use this information to generate a Mermaid code, which will be used to create the flowchart.\n\n### Analysis of `CONTRIBUTING.md`\n\n1. **Welcome and Introduction**: The document starts with a welcome message and an overview of the project.\n\n2. **Join Our Community**: This section provides information on how to join the community, including scheduling introduction calls and joining communication channels like Discord and WeChat.\n\n3. **Guidelines for Contributing**:\n   - **Contributing to the Code**: This includes following specific workflows for opening pull requests, ensuring code quality, and adhering to coding standards.\n   - **Contributing to the Cookbook Writing**: Guidelines for writing and reviewing cookbooks, including using a specific template and following a review process.\n   - **Contributing to Code Reviews**: This part outlines the guidelines and best practices for conducting code reviews.\n\n4. **Principles**: This section discusses naming principles and the use of `logger` instead of `print` for output.\n\n5. **Board Item Create Workflow**: Describes the workflow for creating and managing issues and pull requests.\n\n6. **Sprint Planning & Review**: Information on the sprint duration, planning, and review process.\n\n7. **Getting Help**: Provides guidance on how to get help with the developer setup and other aspects of contributing.\n\n8. **Quick Start**: Steps for cloning the repository, setting up a virtual environment, and installing dependencies.\n\n9. **Common Actions**: This includes instructions for updating dependencies, running tests, and generating coverage reports.\n\n10. **Documentation**: Guidelines for contributing to the documentation and building it locally.\n\n11. **Versioning and Release**: Information on the versioning standard and release process.\n\n12. **License**: Details about the Apache 2.0 license and how to add it to your code.\n\n13. **Giving Credit**: Instructions on how to receive credit for your contributions.\n\n### Creating the Mermaid Code\n\nBased on the analysis, I will create a Mermaid code that outlines the steps and guidelines for contributing to the Camel project. This code will be used to generate the flowchart.FunctionToolOutput(content=\'{"url":"https://sfile.chatglm.cn/mermaid/bcbdc7cb-52be-4aee-9f3d-3612184728af.png"}\')Here is the flowchart based on the contents of the `CONTRIBUTING.md` file for the Camel project, outlining the steps and guidelines for contributing:\n\n![Camel Project Contribution Flowchart](https://sfile.chatglm.cn/mermaid/bcbdc7cb-52be-4aee-9f3d-3612184728af.png)\n\nThis flowchart provides a visual representation of the various steps and guidelines involved in contributing to the Camel project. If you have any specific requests or need further details, please let me know!', tool_call_id='call_JUfuqgDxh3Dtwdxc23kTcNyC')]
===============================================================================
"""

zhipu_toolkit = ZhiPuToolkit().ppt_generation
tools = [FunctionTool(zhipu_toolkit)]

input_file = "/Users/suntao/Documents/GitHub/camel/CONTRIBUTING.md"

usr_msg = f"""
tell me if want to contribute to camel, how to do it. 
here is the reference file: {input_file},generate a ppt of the file.
"""

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

# ruff: noqa: E501
"""
===============================================================================
The PowerPoint presentation based on the CONTRIBUTING.md file for Apache Camel has been generated. 

### Cover Image:
![Cover](https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-0.jpg)

### Links:
- **[Online Preview](https://fc.chatglm.cn/islide/get_pure_link?history_id=7f1070dc-3c73-4a34-a93f-7241a64c97b0&uid=ef6589cf-1aa5-4871-bf66-0c9b1ff1adf2#glmiframe)**
- **[Download PPT](https://sfile.chatglm.cn/islide/625d10f0-d54e-4c0c-b7f4-fbc97dcb75f6.pptx)**

Feel free to check it out!

Tool calls:
[ToolCallingRecord(tool_name='ppt_generation', args={'prompt': 'Generate a PowerPoint presentation based on the contents of the CONTRIBUTING.md file for Apache Camel, detailing how to contribute to the project.', 'file_path': '/Users/suntao/Documents/GitHub/camel/CONTRIBUTING.md'}, result='FunctionToolOutput(content=\'{"pages":[{"index":0,"slideLayout":"title","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-0.jpg"},{"diagramId":652349,"diagramMagnitude":8,"index":1,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-1.jpg"},{"index":2,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-2.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":3,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-3.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":4,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-4.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":5,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-5.jpg"},{"index":6,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-6.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":7,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-7.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":8,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-8.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":9,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-9.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":10,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-10.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":11,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-11.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":12,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-12.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":13,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-13.jpg"},{"diagramId":null,"diagramMagnitude":0,"index":14,"slideLayout":"object","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-14.jpg"},{"index":15,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-15.jpg"},{"index":16,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-16.jpg"},{"index":17,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-17.jpg"},{"index":18,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-18.jpg"},{"index":19,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-19.jpg"},{"index":20,"slideLayout":"sectionHeader","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-20.jpg"},{"index":21,"slideLayout":"closing","thumbnail":"https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-21.jpg"}],"ppt_download_link":"https://sfile.chatglm.cn/islide/625d10f0-d54e-4c0c-b7f4-fbc97dcb75f6.pptx","ppt_preview_link":"https://fc.chatglm.cn/islide/get_pure_link?history_id=7f1070dc-3c73-4a34-a93f-7241a64c97b0&uid=ef6589cf-1aa5-4871-bf66-0c9b1ff1adf2#glmiframe"}\\n\')PPT已经生成,以下是封面图片:\n![封面](https://static.islide.cc/site/content/thumbnail/2025-04-09/190319/QVqpryBpum29z2II.thumbnail-0.jpg)  \n\n您可以点击以下链接在线预览:[在线预览](https://fc.chatglm.cn/islide/get_pure_link?history_id=7f1070dc-3c73-4a34-a93f-7241a64c97b0&uid=ef6589cf-1aa5-4871-bf66-0c9b1ff1adf2#glmiframe)\n\n如果您需要下载PPT,请点击此链接:[下载PPT](https://sfile.chatglm.cn/islide/625d10f0-d54e-4c0c-b7f4-fbc97dcb75f6.pptx)', tool_call_id='call_LshMh6c5EA6tiDcfAXWA6vGa')]
===============================================================================
"""
