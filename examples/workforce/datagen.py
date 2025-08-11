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
import datetime
import os
import platform
import uuid

from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AgentCommunicationToolkit,
    AudioAnalysisToolkit,
    Crawl4AIToolkit,
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
    ScreenshotToolkit,
    SearchToolkit,
    SlackToolkit,
    TerminalToolkit,
    ToolkitMessageIntegration,
    TwitterToolkit,
    VideoDownloaderToolkit,
    WebDeployToolkit,
    WhatsAppToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.utils.commons import api_keys_required

logger = get_logger(__name__)

WORKING_DIRECTORY = os.environ.get("CAMEL_WORKDIR") or os.path.abspath(
    "working_dir/"
)


def send_message_to_user(
    message_title: str,
    message_description: str,
    message_attachment: str = "",
) -> str:
    r"""Use this tool to send a tidy message to the user, including a
    short title, a one-sentence description, and an optional attachment.

    This one-way tool keeps the user informed about your progress,
    decisions, or actions. It does not require a response.
    You should use it to:
    - Announce what you are about to do.
      For example:
      message_title="Starting Task"
      message_description="Searching for papers on GUI Agents."
    - Report the result of an action.
      For example:
      message_title="Search Complete"
      message_description="Found 15 relevant papers."
    - Report a created file.
      For example:
      message_title="File Ready"
      message_description="The report is ready for your review."
      message_attachment="report.pdf"
    - State a decision.
      For example:
      message_title="Next Step"
      message_description="Analyzing the top 10 papers."
    - Give a status update during a long-running task.

    Args:
        message_title (str): The title of the message.
        message_description (str): The short description.
        message_attachment (str): The attachment of the message,
            which can be a file path or a URL.

    Returns:
        str: Confirmation that the message was successfully sent.
    """
    print(f"\nAgent Message:\n{message_title} " f"\n{message_description}\n")
    if message_attachment:
        print(message_attachment)
    logger.info(
        f"\nAgent Message:\n{message_title} "
        f"{message_description} {message_attachment}"
    )
    return (
        f"Message successfully sent to user: '{message_title} "
        f"{message_description} {message_attachment}'"
    )


def developer_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    r"""Factory for creating a developer agent."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    screenshot_toolkit = ScreenshotToolkit(working_directory=WORKING_DIRECTORY)
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
    web_deploy_toolkit = WebDeployToolkit()

    # Add messaging to toolkits
    terminal_toolkit = message_integration.register_toolkits(terminal_toolkit)
    note_toolkit = message_integration.register_toolkits(note_toolkit)
    web_deploy_toolkit = message_integration.register_toolkits(
        web_deploy_toolkit
    )
    screenshot_toolkit = message_integration.register_toolkits(
        screenshot_toolkit
    )

    # Get enhanced tools
    tools = [
        HumanToolkit().ask_human_via_console,
        *terminal_toolkit.get_tools(),
        *note_toolkit.get_tools(),
        *web_deploy_toolkit.get_tools(),
        *screenshot_toolkit.get_tools(),
    ]

    system_message = f"""
<role>
你是数据合成工程师，负责将多来源数据整理、融合并生成指定
条数的高质量合成数据集。
</role>

<context>
- 系统: {platform.system()} ({platform.machine()})
- 工作目录: `{WORKING_DIRECTORY}`。所有本地读写必须在该目录内，
  且所有文件操作一律使用绝对路径。
- 当前日期: {datetime.date.today()}。
</context>

<input_confirmation>
在开始前，必须向用户确认：
1) 数据来源清单（链接与/或本地文件绝对路径）
2) 需要合成的条数 N（默认 100）
3) 输出格式（JSONL/CSV/Parquet/Excel 等）
4) 输出位置（工作目录下的绝对路径）
5) QA 类型：纯 QA 或 QA+COT
6) 若未指定格式，是否采用默认 OpenAI 对话格式
</input_confirmation>

<mandatory_instructions>
- 必须使用 note 工具读取与记录其他代理的信息。
- 完成后，最终回复需提供清晰的工作摘要与结果。
</mandatory_instructions>

<qa_output_schema>
- 目标：最终数据为 QA 或含 COT 的 QA。
- 用户可自定义格式；未指定时使用默认格式。
- 默认1：OpenAI 对话格式（JSONL，每行一个 messages 数组）。
  纯QA示例：
  [{{"role":"user","content":"问题"}},
   {{"role":"assistant","content":"答案"}}]
  QA+COT示例：
  [{{"role":"user","content":"问题"}},
   {{"role":"assistant","content":"思考过程"}},
   {{"role":"assistant","content":"最终答案"}}]
- 默认2：扁平 JSON（JSONL）。
  纯QA：{{"question":"...","answer":"..."}}
  QA+COT：{{"question":"...","cot":"...","answer":"..."}}
- 建议默认落盘为 JSONL，文件名 data.jsonl。
</qa_output_schema>

<capabilities>
- 解析与加载多种数据源：网页、CSV、JSON、Excel、文本、图像、
  音频、视频（如需，可调用其他代理）。
- 数据清洗与标准化：字段映射、缺失处理、类型校验、去重。
- 数据合成：依据 schema/规则合成或扩增记录，直到满足 N 条。
- 质量评估与筛选：唯一性、完整性、字段约束、数值范围、分布、
  一致性、敏感词/毒性过滤、重复检测等，未通过者剔除。
- 结构校验：确保与用户自定义或默认 QA 格式一致。
- COT 泄露检查：按可见性要求，确保 COT 不泄露到 answer/最终回复；
  若需隐藏 COT，则仅保留最终答案。
- 文件输出：按确认的格式与路径保存；若目录不存在则创建。
- 质量报告：生成 .md 或 .html 报告，与数据置于同一目录。
- 溯源与参数：记录来源列表、字段定义、规则、评估指标与结果。
- 终端能力：编写并运行脚本，使用 awk/sed/grep/jq 等 CLI 工具。
</capabilities>

<workflow>
1) 读取笔记与用户输入；如缺失，用 ask_human_via_console 澄清。
2) 拉取/读取数据源，生成来源清单（含链接/路径、说明、时间）。
3) 统一 schema，完成清洗、标准化与初步去重。
4) 合成/扩增数据直至满足 N 条（按 QA 或 QA+COT）。
5) 执行质量评估与筛选，仅保留通过记录；做格式一致性校验。
6) 以指定格式与路径落盘；生成质量报告。
7) 在笔记中记录溯源、参数与评估摘要。
</workflow>

<constraints>
- 始终使用绝对路径；谨慎覆盖已有文件。
- 仅在 `{WORKING_DIRECTORY}` 内创建/修改本地文件。
</constraints>

<final_output>
- 合成数据文件路径（建议 JSONL: data.jsonl）
- 质量报告路径（.md 或 .html）
- 关键统计与通过率摘要
</final_output>
    """

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
        # toolkits_to_register_agent=[screenshot_toolkit],
    )


@api_keys_required(
    [
        (None, 'GOOGLE_API_KEY'),
        (None, 'SEARCH_ENGINE_ID'),
        (None, 'EXA_API_KEY'),
    ]
)
def search_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    r"""Factory for creating a search agent, based on user-provided code
    structure.
    """
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Generate a unique identifier for this agent instance
    agent_id = str(uuid.uuid4())[:8]

    custom_tools = [
        "browser_open",
        "browser_close",
        "browser_back",
        "browser_forward",
        "browser_click",
        "browser_type",
        "browser_enter",
        "browser_switch_tab",
        "browser_visit_page",
        "browser_get_som_screenshot",
    ]
    web_toolkit_custom = HybridBrowserToolkit(
        mode="python",
        headless=False,
        enabled_tools=custom_tools,
        browser_log_to_file=True,
        stealth=True,
        session_id=agent_id,
        viewport_limit=False,
        cache_dir=WORKING_DIRECTORY,
        default_start_url="https://search.brave.com/",
    )

    # Initialize toolkits
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
    search_toolkit = SearchToolkit().search_google
    terminal_toolkit_basic = TerminalToolkit()

    # Add messaging to toolkits
    web_toolkit_custom = message_integration.register_toolkits(
        web_toolkit_custom
    )
    terminal_toolkit = message_integration.register_toolkits(terminal_toolkit)
    note_toolkit = message_integration.register_toolkits(note_toolkit)
    search_toolkit = message_integration.register_functions([search_toolkit])
    enhanced_shell_exec = message_integration.register_functions(
        [terminal_toolkit_basic.shell_exec]
    )

    tools = [
        # *web_toolkit_custom.get_tools(),
        *enhanced_shell_exec,
        HumanToolkit().ask_human_via_console,
        *note_toolkit.get_tools(),
        *search_toolkit,
        *terminal_toolkit.get_tools(),
        *Crawl4AIToolkit().get_tools(),
    ]

    system_message = f"""
<role>
你是数据来源研究员，负责发现、核验并整理用于数据合成的来源。
你的目标是帮助团队获得可用、合法且高质量的数据输入。
</role>

<context>
- 系统: {platform.system()} ({platform.machine()})
- 工作目录: `{WORKING_DIRECTORY}`，所有本地操作用绝对路径。
- 当前日期: {datetime.date.today()}。
</context>

<mandatory_instructions>
- 所有链接必须来自搜索工具或已访问页面，禁止编造 URL。
- 不可凭主观知识回答，信息需来自网页与工具结果。
- 必须使用笔记工具详尽记录：关键内容原文、URL、时间戳。
- 交付时需明确四项确认：来源、条数 N、输出格式、输出位置。
</mandatory_instructions>

<capabilities>
- 搜索与浏览：定位可靠来源、下载或提取示例数据片段。
- 来源评估：可用性、覆盖度、噪声水平、许可与合规性；
  对 QA/QA+COT 的适配性（是否有足够上下文以生成可靠答案、
  是否包含可提取/转写的信息、是否存在版权或隐私风险）。
- 结构化建议：对字段、schema、格式与落盘位置给出建议，
  并建议是否采用 OpenAI 对话格式或扁平 JSONL。
- 与用户澄清：当四项不明确时，主动发问以取得确认。
</capabilities>

<workflow>
1) 初搜：使用 search_google / search_exa 获取候选来源列表。
2) 浏览：用 browser_* 打开页面，核验内容与可访问性。
3) 提取：抓取字段示例、样本条数、下载方式与速率限制。
4) 合规：识别许可证、使用限制与风险，必要时提示用户。
5) 确认：与用户确认 N、格式与输出位置；记录到笔记。
6) 交付：输出「来源清单」与「落盘与格式建议」。
</workflow>

<deliverables>
- 来源清单（URL/路径、简介、获取方式、许可、备注）。
- 建议的条数 N（如用户未给，提出合理建议）。
- 建议的输出格式与位置（含绝对路径）。
- 已访问与处理的 URL 列表。
</deliverables>
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Search Agent",
            content=system_message,
        ),
        model=model,
        # toolkits_to_register_agent=[web_toolkit_custom],
        tools=tools,
        prune_tool_calls_from_memory=True,
    )


def document_agent_factory(
    model: BaseModelBackend,
    task_id: str,
    # google_drive_mcp_toolkit: GoogleDriveMCPToolkit,
):
    r"""Factory for creating a document agent, based on user-provided code
    structure."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    file_write_toolkit = FileWriteToolkit(working_directory=WORKING_DIRECTORY)
    pptx_toolkit = PPTXToolkit(working_directory=WORKING_DIRECTORY)
    mark_it_down_toolkit = MarkItDownToolkit()
    excel_toolkit = ExcelToolkit(working_directory=WORKING_DIRECTORY)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
    search_toolkit = SearchToolkit().search_exa
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)

    # Add messaging to toolkits
    file_write_toolkit = message_integration.register_toolkits(
        file_write_toolkit
    )
    pptx_toolkit = message_integration.register_toolkits(pptx_toolkit)
    mark_it_down_toolkit = message_integration.register_toolkits(
        mark_it_down_toolkit
    )
    excel_toolkit = message_integration.register_toolkits(excel_toolkit)
    note_toolkit = message_integration.register_toolkits(note_toolkit)
    search_toolkit = message_integration.register_functions([search_toolkit])
    terminal_toolkit = message_integration.register_toolkits(terminal_toolkit)

    tools = [
        *file_write_toolkit.get_tools(),
        *pptx_toolkit.get_tools(),
        HumanToolkit().ask_human_via_console,
        *mark_it_down_toolkit.get_tools(),
        *excel_toolkit.get_tools(),
        *note_toolkit.get_tools(),
        *search_toolkit,
        *terminal_toolkit.get_tools(),
    ]

    system_message = f"""
<role>
你是文档与数据交付专员，负责把合成结果与评估报告以用户确认的
格式与路径输出，并确保可读、可追溯与可复用。
</role>

<context>
- 系统: {platform.system()} ({platform.machine()})
- 工作目录: `{WORKING_DIRECTORY}`。
- 当前日期: {datetime.date.today()}。
</context>

<mandatory_instructions>
- 在生成任何文件前，使用 read_note 汇总来源清单、N、格式与位置。
- 主要产出必须是文件（数据文件与质量报告）。
- 如无报告模板，默认生成 HTML 与 MD 两个版本的报告。
</mandatory_instructions>

<qa_output_schema>
- 最终数据为 QA 或 QA+COT。
- 如果用户未自定义格式，采用默认：
  A) OpenAI 对话格式（JSONL，每行一个 messages 数组）
  B) 扁平 JSON（JSONL），含 question/answer 或 question/cot/answer
- 推荐主输出为 JSONL；如需 CSV/Excel，则增加列映射与转义策略。
</qa_output_schema>

<capabilities>
- 读取与整理：从笔记与中间产物抽取 schema、指标与统计数据。
- 文件输出：JSONL/CSV/Parquet/Excel/HTML/Markdown 的写入与校验。
- 图表生成：当数据量较大，自动生成概览图（分布、TopN 等）。
- 表格与演示：按需生成 Excel 或 PPTX 以便审阅与汇报。
- 终端与脚本：使用 shell_exec/awk/sed/jq 等快速汇总与转换。
</capabilities>

<workflow>
1) 读取笔记，确认 N、输出格式与输出路径（绝对路径）。
2) 将合成数据按确认格式落盘；若不存在目标目录则创建。
3) 生成质量报告：通过率、错误分布、字段统计与示例切片。
4) 若为 OpenAI 对话格式，抽检 messages 结构与角色序；
   若为扁平 JSONL，抽检字段完整性与转义。
5) 可选：生成 Excel（多 Sheet）或 PPTX（概览与流程）。
6) 在笔记记录交付物清单与最终路径。
</workflow>

<report_sections>
- 结构一致性通过率（按选定格式）
- COT 泄露检出率与处置策略（隐藏或保留）
- 唯一性/完整性/字段约束/数值范围/分布/一致性统计
- 示例切片与异常样本 TopN
</report_sections>

<deliverables>
- 合成数据文件（JSONL 为主，或用户要求的其他格式）。
- 质量评估报告（.md 与/或 .html），包含上述报告章节。
- 可选：Excel/PPTX 辅助审阅文件。
- 汇总笔记：包含所有最终路径与关键信息。
</deliverables>
    """

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
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    video_downloader_toolkit = VideoDownloaderToolkit(
        working_directory=WORKING_DIRECTORY
    )
    # audio_analysis_toolkit = AudioAnalysisToolkit()
    # image_analysis_toolkit = ImageAnalysisToolkit()
    # openai_image_toolkit = OpenAIImageToolkit(
    #     model="dall-e-3",
    #     response_format="b64_json",
    #     size="1024x1024",
    #     quality="standard",
    #     working_directory=WORKING_DIRECTORY,
    # )
    search_toolkit = SearchToolkit().search_exa
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)

    # Add messaging to toolkits
    video_downloader_toolkit = message_integration.register_toolkits(
        video_downloader_toolkit
    )
    # audio_analysis_toolkit = message_integration.register_toolkits(
    #     audio_analysis_toolkit
    # )
    # image_analysis_toolkit = message_integration.register_toolkits(
    #     image_analysis_toolkit
    # )
    # openai_image_toolkit = message_integration.register_toolkits(
    #     openai_image_toolkit
    # )
    search_toolkit = message_integration.register_functions([search_toolkit])
    terminal_toolkit = message_integration.register_toolkits(terminal_toolkit)
    note_toolkit = message_integration.register_toolkits(note_toolkit)

    tools = [
        *video_downloader_toolkit.get_tools(),
        # *audio_analysis_toolkit.get_tools(),
        # *image_analysis_toolkit.get_tools(),
        # *openai_image_toolkit.get_tools(),
        HumanToolkit().ask_human_via_console,
        *search_toolkit,
        *terminal_toolkit.get_tools(),
        *note_toolkit.get_tools(),
    ]

    system_message = f"""
<role>
你是多模态数据助手，负责支持数据合成场景下的图像/音频/视频等
非结构化数据的解析、抽取与生成，用于扩充或验证数据集。
</role>

<context>
- 系统: {platform.system()} ({platform.machine()})
- 工作目录: `{WORKING_DIRECTORY}`。
- 当前日期: {datetime.date.today()}。
</context>

<mandatory_instructions>
- 使用 read_note 获取已确认的来源、N、输出格式与位置。
- 仅在合规范围内下载、抽取或生成多媒体内容。
</mandatory_instructions>

<capabilities>
- 图像/视频/音频解析：OCR/ASR/关键帧/元数据提取。
- 毒性与敏感内容检测：过滤或标注不可用样本。
- 合成生成：在用户同意下生成示例图片或音频片段用于扩充。
- 媒体转码与切片：使用 ffmpeg 等工具进行格式与片段处理。
</capabilities>

<workflow>
1) 根据笔记指引，解析来源中的多媒体并结构化提取。
2) 对提取结果做质量筛选与敏感性检测。
3) 如需补量，按规则合成生成并标注。
4) 输出中间产物至工作目录供后续合成与报告使用。
</workflow>

<deliverables>
- 结构化提取结果文件路径。
- 敏感/不可用样本清单。
- 可选的合成多媒体样本与说明。
</deliverables>
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Multi Modal Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def social_medium_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a social medium agent."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    whatsapp_toolkit = WhatsAppToolkit()
    twitter_toolkit = TwitterToolkit()
    linkedin_toolkit = LinkedInToolkit()
    reddit_toolkit = RedditToolkit()
    notion_toolkit = NotionToolkit()
    slack_toolkit = SlackToolkit()
    search_toolkit = SearchToolkit().search_exa
    terminal_toolkit = TerminalToolkit()
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)

    # Add messaging to toolkits
    whatsapp_toolkit = message_integration.register_toolkits(whatsapp_toolkit)
    twitter_toolkit = message_integration.register_toolkits(twitter_toolkit)
    linkedin_toolkit = message_integration.register_toolkits(linkedin_toolkit)
    reddit_toolkit = message_integration.register_toolkits(reddit_toolkit)
    notion_toolkit = message_integration.register_toolkits(notion_toolkit)
    slack_toolkit = message_integration.register_toolkits(slack_toolkit)
    search_toolkit = message_integration.register_functions([search_toolkit])
    terminal_toolkit = message_integration.register_toolkits(terminal_toolkit)
    note_toolkit = message_integration.register_toolkits(note_toolkit)

    return ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Social Medium Agent",
            content=f"""
<role>
你是沟通协调专员，负责在数据合成项目中对外沟通（可选），以及
在团队内部同步来源征集、参数确认与交付结果。
</role>

<capabilities>
- 与用户或干系人同步四项确认：来源、条数 N、格式、位置。
- 汇总问题清单并用 send_message_to_user 提醒需要确认的要点。
- 可将最终路径与报告摘要发至指定渠道（如需并已配置）。
</capabilities>

<team_structure>
- 与 研发/研究/文档/多模态 代理保持信息通畅。
</team_structure>

<operating_environment>
- 工作目录: `{WORKING_DIRECTORY}`。
</operating_environment>

<mandatory_instructions>
- 使用 `send_message_to_user` 简明告知关键决定与进展。
- 不进行任何未授权的对外发布；若需要，先征得用户同意。
</mandatory_instructions>""",
        ),
        model=model,
        tools=[
            *whatsapp_toolkit.get_tools(),
            *twitter_toolkit.get_tools(),
            *linkedin_toolkit.get_tools(),
            *reddit_toolkit.get_tools(),
            *notion_toolkit.get_tools(),
            *slack_toolkit.get_tools(),
            HumanToolkit().ask_human_via_console,
            *search_toolkit,
            *terminal_toolkit.get_tools(),
            *note_toolkit.get_tools(),
        ],
    )


async def main():
    # Ensure working directory exists
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)

    # google_drive_mcp_toolkit = GoogleDriveMCPToolkit(
    #     credentials_path="path/to/credentials.json"
    # )

    # Initialize the AgentCommunicationToolkit
    msg_toolkit = AgentCommunicationToolkit(max_message_history=100)

    # Initialize message integration for use in coordinator and task agents
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # await google_drive_mcp_toolkit.connect()

    # Create a single model backend for all agents
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.ZHIPU,
        model_type="glm-4.5",
        model_config_dict={
            "stream": False,
        },
    )

    model_backend_reason = ModelFactory.create(
        model_platform=ModelPlatformType.ZHIPU,
        model_type="glm-4.5",
        model_config_dict={
            "stream": False,
        },
    )

    task_id = 'workforce_task'

    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        system_message=(
            f""""
你是数据合成协调者，负责统筹各子代理围绕“数据来源、条数 N、
输出格式与位置、评估筛选”四项要求推进，保证进度与质量。

- 系统: {platform.system()} ({platform.machine()})
- 工作目录: `{WORKING_DIRECTORY}`。所有本地操作使用绝对路径。
- 当前日期: {datetime.date.today()}。

- 若其他代理执行失败，请将任务转派给 Developer_Agent 协助解决。
- 定期使用笔记工具同步关键结论与待确认事项。
            """
        ),
        model=model_backend_reason,
        tools=[
            *NoteTakingToolkit(
                working_directory=WORKING_DIRECTORY
            ).get_tools(),
        ],
    )
    task_agent = ChatAgent(
        f"""

你是数据合成任务规划者，负责将用户目标分解为可执行步骤，特别是
围绕四项确认：来源、条数 N、输出格式与位置、评估筛选。

- 系统: {platform.system()} ({platform.machine()})
- 工作目录: `{WORKING_DIRECTORY}`（仅用绝对路径）。
- 当前日期: {datetime.date.today()}。

请输出分阶段计划：
1) 澄清与确认输入（四项）
2) 数据获取与清洗标准化
3) 合成与补量策略
4) 质量评估与筛选指标
5) 落盘与报告生成
6) 风险与回退方案
        """,
        model=model_backend_reason,
        tools=[
            *NoteTakingToolkit(
                working_directory=WORKING_DIRECTORY
            ).get_tools(),
        ],
    )
    new_worker_agent = ChatAgent(
        f"You are a helpful worker. When you complete your task, your "
        "final response "
        f"must be a comprehensive summary of your work, presented in a clear, "
        f"detailed, and easy-to-read format. Avoid using markdown tables for "
        f"presenting data; use plain text formatting instead. You are now "
        f"working in "
        f"`{WORKING_DIRECTORY}` All local file operations must occur here, "
        f"but you can access files from any place in the file system. For all "
        f"file system operations, you MUST use absolute paths to ensure "
        f"precision and avoid ambiguity."
        "directory. You can also communicate with other agents "
        "using messaging tools - use `list_available_agents` to see "
        "available team members and `send_message` to coordinate work "
        "and ask for help when needed. "
        "### Note-Taking: You have access to comprehensive note-taking tools "
        "for documenting work progress and collaborating with team members. "
        "Use create_note, append_note, read_note, and list_note to track "
        "your work, share findings, and access information from other agents. "
        "Create notes for work progress, discoveries, and collaboration "
        "points.",
        model=model_backend,
        tools=[
            HumanToolkit().ask_human_via_console,
            *message_integration.register_toolkits(
                NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
            ).get_tools(),
        ],
    )

    # Create agents using factory functions
    search_agent = search_agent_factory(model_backend, task_id)
    developer_agent = developer_agent_factory(
        model_backend_reason,
        task_id,
    )
    document_agent = document_agent_factory(
        model_backend_reason,
        task_id,
        # google_drive_mcp_toolkit
    )
    multi_modal_agent = multi_modal_agent_factory(model_backend, task_id)
    # social_medium_agent = social_medium_agent_factory(
    #     model_backend, task_id
    # )

    # Register all agents with the communication toolkit
    # msg_toolkit.register_agent("Coordinator", coordinator_agent)
    # msg_toolkit.register_agent("Task_Planner", task_agent)
    msg_toolkit.register_agent("Worker", new_worker_agent)
    msg_toolkit.register_agent("Search_Agent", search_agent)
    msg_toolkit.register_agent("Developer_Agent", developer_agent)
    msg_toolkit.register_agent("Document_Agent", document_agent)
    msg_toolkit.register_agent("Multi_Modal_Agent", multi_modal_agent)
    # msg_toolkit.register_agent("Social_Medium_Agent",
    # social_medium_agent)

    # # Add communication tools to all agents
    # communication_tools = msg_toolkit.get_tools()
    # for agent in [
    #     coordinator_agent,
    #     task_agent,
    #     new_worker_agent,
    #     search_agent,
    #     developer_agent,
    #     document_agent,
    #     multi_modal_agent,
    #     # social_medium_agent,
    # ]:
    #     for tool in communication_tools:
    #         agent.add_tool(tool)

    # Create workforce instance before adding workers
    workforce = Workforce(
        'A workforce',
        graceful_shutdown_timeout=30.0,  # 30 seconds for debugging
        share_memory=False,
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        new_worker_agent=new_worker_agent,
        use_structured_output_handler=False,
        task_timeout_seconds=900.0,
    )

    workforce.add_single_agent_worker(
        "Search Agent: 数据来源研究员，负责发现、核验并整理可用于数据合成的"
        "来源，给出格式与落盘位置建议，并记录可用性与合规性。",
        worker=search_agent,
    ).add_single_agent_worker(
        "Developer Agent: 数据合成工程师，负责清洗、标准化、合成/扩增数据，"
        "执行质量评估与筛选，并按指定格式与路径落盘，生成质量报告。",
        worker=developer_agent,
    ).add_single_agent_worker(
        "Document Agent: 文档与数据交付专员，负责输出最终数据文件与评估报告，"
        "并可按需生成 Excel/PPTX 以便审阅与汇报。",
        worker=document_agent,
    ).add_single_agent_worker(
        "Multi-Modal Agent: 多模态数据助手，负责图像/音频/视频等非结构化数据的"
        "解析与生成，用于扩充或验证数据集。",
        worker=multi_modal_agent,
    )

    # specify the task to be solved
    human_task = Task(
        content=(
            """
执行“数据合成（QA/QA+COT）”任务，请严格按照以下步骤与要求：

1. 数据来源
   - 向用户索取数据源链接与/或本地文件的绝对路径。
   - 支持多来源：网页、CSV、JSON、Excel、文本、图片、音频、视频。
   - 记录来源清单（含链接/路径、说明、时间）。

2. 条数
   - 向用户确认需合成的数据条数 N（默认 100）。

3. 输出格式与位置
   - 向用户确认输出格式：JSONL/CSV/Parquet/Excel 等。
   - 默认采用 JSONL：
     A) OpenAI 对话格式（每行一个 messages 数组）或
     B) 扁平 JSON（question/answer 或 question/cot/answer）。
   - 向用户确认输出位置（绝对路径，位于工作目录下）。
   - 若目录不存在则创建；写入完成后回传文件路径。

4. 评估与筛选
   - 设计并执行质量评估与筛选：
     唯一性、完整性、字段约束、数值范围、分布、一致性、
     敏感词/毒性过滤、重复检测、结构一致性校验与 COT 泄露检查。
   - 仅保留通过校验的数据。
   - 生成质量报告（通过率、失败原因统计、描述性统计等）。

交付物
- 合成数据文件（按确认的格式与位置保存）。
- 质量评估报告（.md 或 .html，置于同一目录）。
- 在笔记中记录来源清单、参数设置、评估指标与结果摘要。

如需澄清，使用 ask_human_via_console 与用户交互后继续。
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


if __name__ == "__main__":
    asyncio.run(main())
