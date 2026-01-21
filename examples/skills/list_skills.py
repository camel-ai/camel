# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Create the model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create a ChatAgent
agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    skills_enabled=True
)

# Example 1: List all skills
print("=" * 60)
print("Example 1: List all skills")
print("=" * 60)

response = agent.step("List all skills you have.")
print(f"Response: {response.msgs[0].content}\n")
"""
===========================================================================
Example 1: List all skills
============================================================
Response: Here are all the skills I have access to:

*   **algorithmic-art**: Creating algorithmic art using p5.js with seeded 
randomness and interactive parameter exploration.
*   **brand-guidelines**: Applies Anthropic's official brand colors and 
typography to any sort of artifact that may benefit from having Anthropic's 
look-and-feel.
*   **canvas-design**: Create beautiful visual art in .png and .pdf 
documents using design philosophy.
*   **doc-coauthoring**: Guide users through a structured workflow for 
co-authoring documentation.
*   **docx**: Comprehensive document creation, editing, and analysis 
with support for tracked changes, comments, formatting preservation, 
and text extraction.
*   **frontend-design**: Create distinctive, production-grade frontend 
interfaces with high design quality.
*   **internal-comms**: A set of resources to help me write all kinds of 
internal communications, using the formats that my company likes to use.
*   **mcp-builder**: Guide for creating high-quality MCP 
(Model Context Protocol) servers that enable LLMs to interact with 
external services through well-designed tools.
*   **pdf**: Comprehensive PDF manipulation toolkit for extracting 
text and tables, creating new PDFs, merging/splitting documents, 
and handling forms.
*   **pptx**: Presentation creation, editing, and analysis.
*   **skill-creator**: Guide for creating effective skills.
*   **slack-gif-creator**: Knowledge and utilities for creating animated 
GIFs optimized for Slack.
*   **theme-factory**: Toolkit for styling artifacts with a theme.
*   **web-artifacts-builder**: Suite of tools for creating elaborate, 
multi-component claude.ai HTML artifacts using modern frontend web 
technologies (React, Tailwind CSS, shadcn/ui).
*   **webapp-testing**: Toolkit for interacting with and testing local 
web applications using Playwright.
*   **xlsx**: Comprehensive spreadsheet creation, editing, and analysis 
with support for formulas, formatting, data analysis, and visualization.
===========================================================================
"""