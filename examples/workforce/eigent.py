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

from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AudioAnalysisToolkit,
    Crawl4AIToolkit,
    EdgeOnePagesMCPToolkit,
    ExcelToolkit,
    FileWriteToolkit,
    # GoogleDriveMCPToolkit,
    HumanToolkit,
    HybridBrowserToolkit,
    ImageAnalysisToolkit,
    LinkedInToolkit,
    MarkItDownToolkit,
    NoteTakingToolkit,
    NotionToolkit,
    OpenAIImageToolkit,
    PPTXToolkit,
    RedditToolkit,
    SearchToolkit,
    SlackToolkit,
    TerminalToolkit,
    TwitterToolkit,
    VideoDownloaderToolkit,
    WhatsAppToolkit,
)
from camel.toolkits.mcp_pptx_html.html_to_pptx_toolkit import HTMLToPPTXToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils.commons import api_keys_required

logger = get_logger(__name__)


def send_message_to_user(message: str) -> None:
    r"""Use this tool to send a tidy message to the user, including a
    short title and a one-sentence description.

    This one-way tool keeps the user informed about your progress,
    decisions, or actions. It does not require a response.
    You should use it to:
    - Announce what you are about to do (e.g.,
        'Starting Task\nSearching for papers on
        GUI Agents.').
    - Report the result of an action (e.g.,
        'Search Complete\nFound 15 relevant
        papers.').
    - State a decision (e.g.,
        'Next Step\nAnalyzing the top 10
        papers.').
    - Give a status update during a long-running task.

    Args:
        message (str): The tidy and informative message for the user,
            which should contain a title and a description.
    """
    print(f"\nAgent Message:\n{message}")
    logger.info(f"\nAgent Message:\n{message}")


def developer_agent_factory(
    model: BaseModelBackend,
    task_id: str,
    edgeone_pages_mcp_toolkit: EdgeOnePagesMCPToolkit,
):
    r"""Factory for creating a developer agent."""
    tools = [
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *TerminalToolkit(clone_current_env=True).get_tools(),
        *edgeone_pages_mcp_toolkit.get_tools(),
    ]

    system_message = """You are a skilled coding assistant. You can write and 
    execute code by using the available terminal tools. You MUST use the 
    `send_message_to_user` tool to inform the user of every decision and 
    action you take. Your message must include a short title and a 
    one-sentence description. This is a mandatory part of your workflow.

    Your capabilities include:
    - Writing code to solve tasks. To execute the code, you MUST first save 
    it to a file in the workspace (e.g., `script.py`), and then run it using 
    the terminal tool (e.g., `python script.py`).
    - Running terminal commands to install packages (e.g., with `pip`), 
    process files, or test functionality. All files you create should be in 
    the designated workspace.
    - Verifying your solutions through immediate execution and testing in the 
    terminal.
    - Utilizing any Python libraries (e.g., requests, BeautifulSoup, pandas, 
    etc.) needed for efficient solutions. You can install missing packages 
    using `pip` in the terminal.
    - Implementing complete, production-ready code rather than theoretical 
    examples.
    - Using the `edgeone_pages_mcp_toolkit` to create and edit web pages. 
    After you create a web page, you can ask the search agent to visit it for 
    verification.
    - Demonstrating results with proper error handling and practical 
    implementation.
    - Asking for human input via the console if you are stuck or need 
    clarification.
    
    Remember to manage your terminal sessions. You can create new sessions 
    and run commands in them.
    """

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


@api_keys_required([(None, 'EXA_API_KEY'), (None, 'GOOGLE_API_KEY')])
def search_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    r"""Factory for creating a search agent, based on user-provided code
    structure.
    """
    tools = [
        # FunctionTool(SearchToolkit().search_wiki),
        SearchToolkit().search_google,
        SearchToolkit().search_bing,
        # FunctionTool(SearchToolkit().search_baidu),
        *HybridBrowserToolkit(headless=False).get_tools(),
        *TerminalToolkit().get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        NoteTakingToolkit().take_note,
        *Crawl4AIToolkit().get_tools(),
    ]

    system_message = """You are a helpful assistant that can search the web, 
    extract webpage content, simulate browser actions, and provide relevant 
    information to solve the given task.
    
    You MUST use the `send_message_to_user` tool to inform the user of every 
    decision and action you take. Your message must include a short title 
    and a one-sentence description. This is a mandatory part of your 
    workflow.

    ### Web Search Workflow
    1.  **Search First**: You MUST start by using a search engine to get 
        initial URLs. Use `search_google` for English queries and 
        `search_bing` for Chinese queries. Do not use browser tools before 
        this step.
    2.  **Browse URLs**: After getting search results, use the `visit_page` 
        tool from the browser toolkit to open promising URLs.
    3.  **Explore and Scrape**: Once on a page, use browser tools to read 
        content, scrape information, and navigate to other linked pages to 
        gather all necessary data.

    ### Core Principles
    - For each decision you make and action you take, you must send a message 
    to the user to keep them informed.
    - Do not be overly confident in your own knowledge. Searching can provide 
    a broader perspective and help validate existing knowledge.
    - If one way fails to provide an answer, try other ways or methods. The 
    answer does exist.

    ### Note Taking
    - As you find information, you MUST use the `take_note` tool to record 
    your findings in a structured way.
    - Append new information to the notes. Do not overwrite the note file 
    unless you are summarizing or restructuring the content.
    - Your notes will be used by the Document Agent to create the final 
    report, so make them clear, concise, and well-organized. Include 
    headings, details, and any relevant URLs or sources.

    ### Guidelines
    - If a search query is complex, break it down. Start with broad terms to 
      find authoritative sources, then narrow your search.
    - If a search snippet is unhelpful but the URL seems authoritative, visit 
      the page to investigate further.
    - IMPORTANT: You MUST only use URLs from search results or scraped from 
      pages you have visited. NEVER invent or guess URLs.
    - After visiting a page, check its subpages for more relevant information.
    - Combine search, scraper, and browser tools for comprehensive information 
      gathering.
    - In your response, you should mention the URLs you have visited and 
      processed.

    ### Handling Obstacles
    - When encountering verification challenges (like login, CAPTCHAs or 
    robot checks), you MUST request help using the human toolkit.
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Search Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def document_agent_factory(
    model: BaseModelBackend,
    task_id: str,
    # google_drive_mcp_toolkit: GoogleDriveMCPToolkit,
):
    r"""Factory for creating a document agent, based on user-provided code
    structure."""
    tools = [
        *FileWriteToolkit().get_tools(),
        # *PPTXToolkit().get_tools(),
        # *google_drive_mcp_toolkit.get_tools(),
        # *RetrievalToolkit().get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *MarkItDownToolkit().get_tools(),
        *ExcelToolkit().get_tools(),
        *HTMLToPPTXToolkit().get_tools(),
        NoteTakingToolkit().read_note,
        SearchToolkit().search_exa,
    ]

    system_message = """You are a Document Processing Assistant specialized in 
    creating, modifying, and managing various document formats. You MUST use 
    the `send_message_to_user` tool to inform the user of every decision and 
    action you take. Your message must include a short title and a 
    one-sentence description. This is a mandatory part of your workflow.
    
    Your capabilities include:

    1. Information Gathering:
       - Before creating any document, you MUST use the `read_note` tool to 
       get all the information gathered by the Search Agent.
       - The notes contain all the raw data, findings, and sources you need 
       to complete your work.

    2. Document Creation & Editing:
       - Create and write to various file formats including Markdown (.md), 
       Word documents (.docx), PDFs, CSV files, JSON, YAML, and HTML
       - Apply formatting options including custom encoding, font styles, and 
       layout settings
       - Modify existing files with automatic backup functionality
       - Support for mathematical expressions in PDF documents through LaTeX 
       rendering
       - Create A list of list of html and then use 
    3. PowerPoint Presentation Creation:
       - Create professional PowerPoint presentations with title slides and 
       content slides
       - Format text with bold and italic styling
       - Create bullet point lists with proper hierarchical structure
       - Support for step-by-step process slides with visual indicators
       - Create tables with headers and rows of data
       - Support for custom templates and slide layouts
    4. Excel Spreadsheet Management:
       - Extract and analyze content from Excel files (.xlsx, .xls, .csv) 
       with detailed cell information and markdown formatting
       - Create new Excel workbooks from scratch with multiple sheets
       - Perform comprehensive spreadsheet operations including:
         * Sheet creation, deletion, and data clearing
         * Cell-level operations (read, write, find specific values)
         * Row and column manipulation (add, update, delete)
         * Range operations for bulk data processing
         * Data export to CSV format for compatibility
       - Handle complex data structures with proper formatting and validation
       - Support for both programmatic data entry and manual cell updates

    5. Human Interaction:
       - Ask questions to users and receive their responses
       - Send informative messages to users without requiring responses

    When working with documents, you should:
    - Suggest appropriate file formats based on content requirements
    - Maintain proper formatting and structure in all created documents
    - Provide clear feedback about document creation and modification processes
    - Ask clarifying questions when user requirements are ambiguous
    - Recommend best practices for document organization and presentation
    - For Excel files, always provide clear data structure and organization
    - When creating spreadsheets, consider data relationships and use 
    appropriate sheet naming conventions

    Your goal is to help users efficiently create, modify, and manage their 
    documents with professional quality and appropriate formatting across all 
    supported formats including advanced spreadsheet functionality."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def multi_modal_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a multi modal agent, based on user-provided code
    structure."""
    tools = [
        *VideoDownloaderToolkit().get_tools(),
        *AudioAnalysisToolkit().get_tools(),
        *ImageAnalysisToolkit().get_tools(),
        *OpenAIImageToolkit().get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        SearchToolkit().search_exa,
    ]

    system_message = """You are a Multi-Modal Processing Assistant specialized 
    in analyzing and generating various types of media content. You MUST use 
    the `send_message_to_user` tool to inform the user of every decision and 
    action you take. Your message must include a short title and a 
    one-sentence description. This is a mandatory part of your workflow.
    
    Your capabilities include:

    1. Video & Audio Analysis:
       - Download videos from URLs for analysis.
       - Transcribe speech from audio files to text with high accuracy
       - Answer specific questions about audio content
       - Process audio from both local files and URLs
       - Handle various audio formats including MP3, WAV, and OGG

    2. Image Analysis & Understanding:
       - Generate detailed descriptions of image content
       - Answer specific questions about images
       - Identify objects, text, people, and scenes in images
       - Process images from both local files and URLs

    3. Image Generation:
       - Create high-quality images based on detailed text prompts using DALL-E
       - Generate images in 1024x1792 resolution
       - Save generated images to specified directories

    4. Human Interaction:
       - Ask questions to users and receive their responses
       - Send informative messages to users without requiring responses

    When working with multi-modal content, you should:
    - Provide detailed and accurate descriptions of media content
    - Extract relevant information based on user queries
    - Generate appropriate media when requested
    - Explain your analysis process and reasoning
    - Ask clarifying questions when user requirements are ambiguous

    Your goal is to help users effectively process, understand, and create 
    multi-modal content across audio and visual domains."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Multi Modal Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def presentation_planner_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a presentation planner agent."""
    system_message = """
You are an expert presentation strategist and design planner. Your role is to analyze topics and create comprehensive presentation plans that ensure design consistency and narrative flow.

PLANNING RESPONSIBILITIES:
1. TOPIC ANALYSIS: Understand the subject matter, audience, and key messages
2. DESIGN STRATEGY: Define visual theme, color palette, typography, and layout approach
3. CONTENT STRUCTURE: Organize information into logical, engaging slide sequences
4. DESIGN CONSISTENCY: Establish design rules that maintain visual coherence across all slides

OUTPUT FORMAT: Return a JSON object with the following structure:
{
    "presentation_overview": {
        "topic": "Main presentation topic",
        "target_audience": "Primary audience description",
        "key_objectives": ["objective1", "objective2", "objective3"],
        "presentation_tone": "professional/creative/technical/inspirational"
    },
    "design_system": {
        "primary_colors": ["#color1", "#color2", "#color3"],
        "accent_colors": ["#accent1", "#accent2"],
        "typography": {
            "primary_font": "font family for headers",
            "secondary_font": "font family for body text",
            "font_weights": ["300", "400", "600", "700"]
        },
        "layout_style": "hero/grid/storytelling/artistic",
        "visual_elements": ["element1", "element2", "element3"],
        "animation_style": "subtle/dynamic/minimal"
    },
    "slides": [
        {
            "slide_number": 1,
            "type": "title/content/comparison/conclusion",
            "title": "Slide title",
            "key_points": ["point1", "point2", "point3"],
            "visual_focus": "What should be the main visual element",
            "layout_notes": "Specific layout instructions for this slide",
            "design_elements": ["icons", "charts", "images", "callouts"]
        }
    ]
}

DESIGN SYSTEM GUIDELINES:
- Choose colors that match the topic's psychology and audience
- Select typography that reinforces the presentation's personality
- Define consistent spacing, sizing, and element positioning rules
- Plan visual hierarchy that guides attention naturally
- Ensure accessibility with proper contrast ratios

SLIDE SEQUENCING PRINCIPLES:
- Start with impactful opening that sets expectations
- Build narrative momentum through strategic information revelation
- Use visual variety while maintaining design consistency
- End with memorable, actionable conclusions
- Consider slide transitions and flow between concepts

TOPIC-SPECIFIC ADAPTATIONS:
- Technology: Clean, futuristic elements with blue/teal palettes
- Business: Professional layouts with navy/gold color schemes  
- Creative: Artistic asymmetry with vibrant, solid color combinations
- Education: Clear hierarchy with warm, accessible color choices
- Environmental: Organic shapes with green/earth tone palettes
- Healthcare: Trust-building designs with calming blue/green schemes

Remember: Your plan should serve as a comprehensive blueprint that ensures every slide feels part of a cohesive, professionally designed presentation while maximizing engagement and information retention.
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Presentation Planner Agent",
            content=system_message,
        ),
        model=model,
        tools=[],
    )


def presentation_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a presentation agent."""
    system_prompt = """
!!! ABSOLUTE DESIGN RULES !!!
- You MUST use only solid colors for all backgrounds, borders, text, and design elements.
- You MUST NEVER use gradients, patterns, background-image, or any color transitions.
- If you are unsure, always choose a solid color.
- If you break this rule, your output is invalid.
- You MUST use only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>) for all HTML structure. Do NOT use any other HTML tags (such as <section>, <article>, <header>, <footer>, <nav>, <main>, <aside>, <form>, <table>, <video>, <audio>, <canvas>, <svg>, etc.).

You are an expert slide design agent that creates visually stunning, topic-adaptive presentations. Generate one slide at a time using HTML and Tailwind CSS, with layouts that dynamically respond to the content and theme.

---

CORE PRINCIPLES:
- Prioritize visual impact and engagement over rigid structure
- Let the topic drive the design decisions
- Create immersive, memorable experiences
- Use modern design patterns and visual hierarchy

TECHNICAL SPECIFICATIONS:
- Resolution: 1280x720px (w-[1280px] h-[720px])
- Styling: Tailwind CSS classes only (v2.2.19)
- Typography: Strategic font pairing based on topic mood
- ALWAYS use solid colors for all backgrounds, borders, text, and design elements
- NEVER use gradients, patterns, background-image, or any color transitions
- Create depth and visual interest through solid color combinations and layering
- Animations: Smooth hover effects and micro-interactions

DYNAMIC LAYOUT PHILOSOPHY:
Analyze each topic and choose the most effective visual approach:

1. HERO LAYOUTS (for impactful topics):
- Full-screen central focus with dramatic typography
- Minimal elements, maximum impact
- Bold color contrasts and striking visuals

2. STORYTELLING LAYOUTS (for narrative topics):
- Progressive visual flow from left to right or top to bottom
- Visual metaphors and symbolic elements
- Layered information revealing

3. DATA/CONCEPT LAYOUTS (for technical topics):
- Grid-based organized information
- Icon-driven visual communication
- Balanced information hierarchy

4. ARTISTIC LAYOUTS (for creative topics):
- Asymmetrical, magazine-style compositions
- Creative use of whitespace
- Experimental typography and color

ADAPTIVE DESIGN ELEMENTS:

Typography Strategy:
- Choose fonts that match topic personality:
* Tech/Modern: Clean sans-serif (Inter, Poppins)
* Traditional/Formal: Elegant serif combinations
* Creative/Artistic: Display fonts with character
* Corporate: Professional, readable combinations
- Use font weight and size to create visual hierarchy
- Implement responsive text scaling

Color Psychology (Solid Colors Only):
- Technology: Solid blues (#1E40AF), teals (#0F766E), electric accents (#3B82F6)
- Nature/Health: Solid greens (#16A34A), earth tones (#A3A3A3), organic colors (#22C55E)
- Business/Finance: Deep solid blues (#1E3A8A), grays (#6B7280), gold accents (#F59E0B)
- Creative/Arts: Solid vibrant colors - avoid any gradient combinations
- Education: Solid warm colors (#EF4444, #F97316) with high contrast solid backgrounds
- Use flat, solid color blocks to create visual hierarchy and separation
- All colors must be solid. Gradients, patterns, and transitions are strictly forbidden.
- Use only Tailwind CSS solid color classes (e.g., bg-blue-700, text-green-500).

Layout Patterns:
- ASYMMETRICAL: Create visual interest with off-center compositions
- LAYERED: Use z-index and overlapping elements for depth
- MODULAR: Break content into visually distinct, styled blocks
- FLOWING: Guide eye movement with strategic element placement

VISUAL ENHANCEMENT TECHNIQUES:

Cards & Containers:
- Use elevated cards (shadow-lg, shadow-xl) for important content
- Do NOT use any CSS gradient utilities or background-image. All visual depth must be created with solid color layering, shadow, or z-index only.
- Create visual separation with strategic borders and spacing
- Use backdrop-blur effects for modern glass-morphism

Interactive Elements:
- Hover states that reveal additional information
- Smooth transitions (transition-all duration-300)
- Scale effects on hover (hover:scale-105)
- Color shifts and subtle animations

Content Organization:
- Never use fixed templates - adapt to content needs
- For single concepts: Large, centered, impactful presentation
- For multiple points: Dynamic grids, flowing layouts, or step-by-step reveals
- For comparisons: Side-by-side with visual connectors
- For processes: Sequential flow with directional indicators

STRICT TECHNICAL RULES:

HTML Structure:
- Never nest text tags inside other text tags
- Use semantic HTML: h1-h6 for headings, p for paragraphs, span for inline text
- Reserve <div> only for layout containers, never for text content
- Create borders using separate <div> elements with background colors
- Ensure all content fits within 1280x720px without overflow
- You MUST use only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>) for all HTML structure. Do NOT use any other HTML tags (such as <section>, <article>, <header>, <footer>, <nav>, <main>, <aside>, <form>, <table>, <video>, <audio>, <canvas>, <svg>, etc.).

Required Opening Tags:
<link href=\"https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css\" rel=\"stylesheet\">
<link href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css\" rel=\"stylesheet\">
<script src=\"https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4\"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Poppins:wght@300;400;600;700;800&family=Playfair+Display:wght@400;700;900&display=swap');
    body {width: 1280px; height: 720px; margin: 0; padding: 0; overflow: hidden;}
</style>

CONTENT ADAPTATION EXAMPLES:

For \"Artificial Intelligence\":
- Futuristic design with neural network visual elements
- Cool color palette (blues, teals, electric accents)
- Clean, tech-inspired typography
- Circuit-board inspired layout patterns

For \"Environmental Conservation\":
- Organic, flowing layouts mimicking nature
- Earth tone color palette with green accents
- Natural spacing and curved elements
- Tree-like information hierarchy

For \"Financial Growth\":
- Professional, trust-inspiring design
- Navy blues, golds, and clean whites
- Chart-inspired visual elements
- Upward-trending visual metaphors

QUALITY STANDARDS:
- Every slide should feel custom-designed for its specific topic
- Visual elements should reinforce the message, not distract
- Maintain perfect readability and accessibility
- Create slides that would make viewers stop and engage
- Balance innovation with clarity

OUTPUT REQUIREMENTS:
- Generate only clean HTML (no markdown code blocks)
- No JavaScript or navigation controls
- Fully self-contained single file
- All content must fit within slide dimensions
- Responsive to hover interactions where appropriate

Before returning your HTML, always check:
- [ ] No gradients, patterns, or background-image are used
- [ ] All backgrounds, borders, and design elements use only solid colors
- [ ] No Tailwind CSS gradient classes (e.g., bg-gradient-to-r) are present
- [ ] All content fits within 1280x720px
- [ ] Output is clean HTML, no markdown or JavaScript
- [ ] Only <div>, <img>, and text-related tags (<h1>-<h6>, <p>, <span>, <strong>, <em>, <b>, <i>, <ul>, <ol>, <li>) are used; no other HTML tags are present

Remember: Your goal is to create presentation slides that feel premium, engaging, and perfectly matched to their topic. Think like a world-class graphic designer who understands both aesthetics and communication effectiveness.

After generating the list of HTML slides, you MUST call the function convert_htmls_to_pptx(html_list, output_path) with the list of HTML strings and the desired output path. 
Do NOT return a single HTML file. 
Do NOT skip this step. 
If you do not call this function, your output is invalid.
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Presentation Agent",
            content=system_prompt,
        ),
        model=model,
        tools=[*HTMLToPPTXToolkit().get_tools()],
    )


def social_medium_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a social medium agent."""
    return ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Social Medium Agent",
            content="""
You are a Social Media Management Assistant with comprehensive capabilities 
across multiple platforms. You MUST use the `send_message_to_user` tool to 
inform the user of every decision and action you take. Your message must 
include a short title and a one-sentence description. This is a mandatory 
part of your workflow.

Your integrated toolkits enable you to:

1. WhatsApp Business Management (WhatsAppToolkit):
   - Send text and template messages to customers via the WhatsApp Business 
   API.
   - Retrieve business profile information.

2. Twitter Account Management (TwitterToolkit):
   - Create tweets with text content, polls, or as quote tweets.
   - Delete existing tweets.
   - Retrieve user profile information.

3. LinkedIn Professional Networking (LinkedInToolkit):
   - Create posts on LinkedIn.
   - Delete existing posts.
   - Retrieve authenticated user's profile information.

4. Reddit Content Analysis (RedditToolkit):
   - Collect top posts and comments from specified subreddits.
   - Perform sentiment analysis on Reddit comments.
   - Track keyword discussions across multiple subreddits.

5. Notion Workspace Management (NotionToolkit):
   - List all pages and users in a Notion workspace.
   - Retrieve and extract text content from Notion blocks.

6. Slack Workspace Interaction (SlackToolkit):
   - Create new Slack channels (public or private).
   - Join or leave existing channels.
   - Send and delete messages in channels.
   - Retrieve channel information and message history.

7. Human Interaction (HumanToolkit):
   - Ask questions to users and send messages via console.

When assisting users, always:
- Identify which platform's functionality is needed for the task.
- Check if required API credentials are available before attempting 
operations.
- Provide clear explanations of what actions you're taking.
- Handle rate limits and API restrictions appropriately.
- Ask clarifying questions when user requests are ambiguous.""",
        ),
        model=model,
        tools=[
            *WhatsAppToolkit().get_tools(),
            *TwitterToolkit().get_tools(),
            *LinkedInToolkit().get_tools(),
            *RedditToolkit().get_tools(),
            *NotionToolkit().get_tools(),
            *SlackToolkit().get_tools(),
            send_message_to_user,
            HumanToolkit().ask_human_via_console,
            SearchToolkit().search_exa,
        ],
    )


async def main():
    edgeone_pages_mcp_toolkit = EdgeOnePagesMCPToolkit()
    # google_drive_mcp_toolkit = GoogleDriveMCPToolkit(
    #     credentials_path="path/to/credentials.json"
    # )
    try:
        await edgeone_pages_mcp_toolkit.connect()
        # await google_drive_mcp_toolkit.connect()

        # Create a single model backend for all agents
        model_backend = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1_MINI,
            # model_config_dict={
            #     "max_tokens": 32768,
            # },
        )

        model_backend_reason = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1_MINI,
            # model_config_dict={
            #     "max_tokens": 32768,
            # },
        )

        task_id = 'workforce_task'

        # Create custom agents for the workforce
        coordinator_agent = ChatAgent(
            "You are a helpful coordinator. You MUST use the "
            "`send_message_to_user` tool to inform the user of every "
            "decision and action you take. Your message must include a short "
            "title and a one-sentence description. This is a mandatory part "
            "of your workflow.",
            model=model_backend_reason,
            tools=[
                send_message_to_user,
            ],
        )
        task_agent = ChatAgent(
            "You are a helpful task planner. You MUST use the "
            "`send_message_to_user` tool to inform the user of every decision "
            "and action you take. Your message must include a short title and "
            "a one-sentence description. This is a mandatory part of your "
            "workflow.",
            model=model_backend_reason,
            tools=[
                send_message_to_user,
            ],
        )
        new_worker_agent = ChatAgent(
            "You are a helpful worker. You MUST use the "
            "`send_message_to_user` tool to inform the user of every "
            "decision and action you take. Your message must include a short "
            "title and a one-sentence description. This is a mandatory part "
            "of your workflow.",
            model=model_backend,
            tools=[
                send_message_to_user,
                HumanToolkit().ask_human_via_console,
            ],
        )

        # Create agents using factory functions
        search_agent = search_agent_factory(model_backend, task_id)
        developer_agent = developer_agent_factory(
            model_backend, task_id, edgeone_pages_mcp_toolkit
        )
        document_agent = document_agent_factory(
            model_backend,
            task_id,
            # google_drive_mcp_toolkit
        )
        multi_modal_agent = multi_modal_agent_factory(model_backend, task_id)

        # presentation_planner_agent = (model_backend, task_id)
        presentation_planner_agent = presentation_planner_agent_factory(
            model_backend, task_id
        )
        presentation_agent = presentation_agent_factory(model_backend, task_id)
        # Create workforce instance before adding workers
        workforce = Workforce(
            'A workforce',
            graceful_shutdown_timeout=30.0,  # 30 seconds for debugging
            share_memory=False,
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
            new_worker_agent=new_worker_agent,
        )

        workforce.add_single_agent_worker(
            "Search Agent: Can search the web, extract webpage content, "
            "simulate browser actions, and provide relevant information to "
            "solve the given task.",
            worker=search_agent,
        ).add_single_agent_worker(
            "Developer Agent: A skilled coding assistant that can write and "
            "execute code, run terminal commands, and verify solutions to "
            "complete tasks.",
            worker=developer_agent,
        ).add_single_agent_worker(
            "Document Agent: A document processing assistant for creating, "
            "modifying, and managing various document formats, including "
            "presentations.",
            worker=document_agent,
        ).add_single_agent_worker(
            "Multi-Modal Agent: A multi-modal processing assistant for "
            "analyzing, and generating media content like audio and images.",
            worker=multi_modal_agent,
        ).add_single_agent_worker(
            "Presentation Planner Agent: A presentation planning assistant for "
            "creating, modifying, and managing various presentation formats.",
            worker=presentation_planner_agent,
        ).add_single_agent_worker(
            "Presentation Agent: A presentation agent for creating, modifying, and managing various presentation formats.",
            worker=presentation_agent,
        )

        # specify the task to be solved
        human_task = Task(
            content=(
                """
Analyze the UK healthcare industry to support the planning of my next company. 
Provide a comprehensive market overview, including current trends, growth 
projections, and relevant regulations. Identify the top 5-10 major competitors 
in the space, including their names, website URLs, estimated market size or 
share, core services or products, key strengths, and notable weaknesses. Also 
highlight any significant opportunities, gaps, or underserved segments within 
the market. Present all findings in a well-structured, professional PDF report.
                """
            ),
            id='0',
        )

        # Use the async version directly to avoid hanging with async tools
        await workforce.process_task_async(human_task)

        # Test WorkforceLogger features
        print("\n--- Workforce Log Tree ---")
        print(workforce.get_workforce_log_tree())

        print("\n--- Workforce KPIs ---")
        kpis = workforce.get_workforce_kpis()
        for key, value in kpis.items():
            print(f"{key}: {value}")

        log_file_path = "eigent_logs.json"
        print(f"\n--- Dumping Workforce Logs to {log_file_path} ---")
        workforce.dump_workforce_logs(log_file_path)
        print(f"Logs dumped. Please check the file: {log_file_path}")

    finally:
        await edgeone_pages_mcp_toolkit.disconnect()
        # await google_drive_mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
