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
# ruff: noqa: I001
from .function_tool import (
    FunctionTool,
    get_openai_function_schema,
    get_openai_tool_schema,
    generate_docstring,
)
from .open_api_specs.security_config import openapi_security_config

from .math_toolkit import MathToolkit
from .search_toolkit import SearchToolkit
from .weather_toolkit import WeatherToolkit
from .image_generation_toolkit import ImageGenToolkit, OpenAIImageToolkit
from .ask_news_toolkit import AskNewsToolkit, AsyncAskNewsToolkit
from .linkedin_toolkit import LinkedInToolkit
from .reddit_toolkit import RedditToolkit
from .meshy_toolkit import MeshyToolkit
from .openbb_toolkit import OpenBBToolkit
from .bohrium_toolkit import BohriumToolkit

from .base import BaseToolkit, RegisteredAgentToolkit
from .google_maps_toolkit import GoogleMapsToolkit
from .code_execution import CodeExecutionToolkit
from .github_toolkit import GithubToolkit
from .google_scholar_toolkit import GoogleScholarToolkit
from .google_calendar_toolkit import GoogleCalendarToolkit
from .gmail_toolkit import GmailToolkit
from .arxiv_toolkit import ArxivToolkit
from .slack_toolkit import SlackToolkit
from .whatsapp_toolkit import WhatsAppToolkit
from .wechat_official_toolkit import WeChatOfficialToolkit
from .dingtalk import DingtalkToolkit
from .twitter_toolkit import TwitterToolkit
from .open_api_toolkit import OpenAPIToolkit
from .retrieval_toolkit import RetrievalToolkit
from .notion_toolkit import NotionToolkit
from .human_toolkit import HumanToolkit
from .stripe_toolkit import StripeToolkit
from .video_download_toolkit import VideoDownloaderToolkit
from .dappier_toolkit import DappierToolkit
from .networkx_toolkit import NetworkXToolkit
from .semantic_scholar_toolkit import SemanticScholarToolkit
from .zapier_toolkit import ZapierToolkit
from .sympy_toolkit import SymPyToolkit
from .mineru_toolkit import MinerUToolkit
from .memory_toolkit import MemoryToolkit
from .audio_analysis_toolkit import AudioAnalysisToolkit
from .excel_toolkit import ExcelToolkit
from .video_analysis_toolkit import VideoAnalysisToolkit
from .image_analysis_toolkit import ImageAnalysisToolkit
from .mcp_toolkit import MCPToolkit
from .browser_toolkit import BrowserToolkit
from .async_browser_toolkit import AsyncBrowserToolkit
from .file_toolkit import FileToolkit, FileWriteToolkit
from .pptx_toolkit import PPTXToolkit
from .terminal_toolkit import TerminalToolkit
from .pubmed_toolkit import PubMedToolkit
from .data_commons_toolkit import DataCommonsToolkit
from .thinking_toolkit import ThinkingToolkit
from .pyautogui_toolkit import PyAutoGUIToolkit
from .searxng_toolkit import SearxNGToolkit
from .jina_reranker_toolkit import JinaRerankerToolkit
from .pulse_mcp_search_toolkit import PulseMCPSearchToolkit
from .klavis_toolkit import KlavisToolkit
from .aci_toolkit import ACIToolkit
from .origene_mcp_toolkit import OrigeneToolkit
from .playwright_mcp_toolkit import PlaywrightMCPToolkit
from .resend_toolkit import ResendToolkit
from .wolfram_alpha_toolkit import WolframAlphaToolkit
from .task_planning_toolkit import TaskPlanningToolkit
from .hybrid_browser_toolkit import HybridBrowserToolkit
from .edgeone_pages_mcp_toolkit import EdgeOnePagesMCPToolkit
from .google_drive_mcp_toolkit import GoogleDriveMCPToolkit
from .craw4ai_toolkit import Crawl4AIToolkit
from .markitdown_toolkit import MarkItDownToolkit
from .note_taking_toolkit import NoteTakingToolkit
from .message_agent_toolkit import AgentCommunicationToolkit
from .web_deploy_toolkit import WebDeployToolkit
from .screenshot_toolkit import ScreenshotToolkit
from .message_integration import ToolkitMessageIntegration
from .context_summarizer_toolkit import ContextSummarizerToolkit
from .notion_mcp_toolkit import NotionMCPToolkit
from .vertex_ai_veo_toolkit import VertexAIVeoToolkit
from .minimax_mcp_toolkit import MinimaxMCPToolkit

__all__ = [
    'BaseToolkit',
    'FunctionTool',
    'get_openai_function_schema',
    'get_openai_tool_schema',
    "generate_docstring",
    'openapi_security_config',
    'GithubToolkit',
    'MathToolkit',
    'GoogleMapsToolkit',
    'SearchToolkit',
    'SlackToolkit',
    'WhatsAppToolkit',
    'WeChatOfficialToolkit',
    'DingtalkToolkit',
    'ImageGenToolkit',
    'TwitterToolkit',
    'WeatherToolkit',
    'RetrievalToolkit',
    'OpenAPIToolkit',
    'LinkedInToolkit',
    'RedditToolkit',
    'CodeExecutionToolkit',
    'AskNewsToolkit',
    'AsyncAskNewsToolkit',
    'GoogleScholarToolkit',
    'GoogleCalendarToolkit',
    'GmailToolkit',
    'NotionToolkit',
    'ArxivToolkit',
    'HumanToolkit',
    'VideoDownloaderToolkit',
    'StripeToolkit',
    'MeshyToolkit',
    'OpenBBToolkit',
    'DappierToolkit',
    'NetworkXToolkit',
    'SemanticScholarToolkit',
    'ZapierToolkit',
    'SymPyToolkit',
    'MinerUToolkit',
    'MemoryToolkit',
    'MCPToolkit',
    'AudioAnalysisToolkit',
    'ExcelToolkit',
    'VideoAnalysisToolkit',
    'ImageAnalysisToolkit',
    'BrowserToolkit',
    'AsyncBrowserToolkit',
    'FileToolkit',
    'FileWriteToolkit',  # Deprecated, use FileToolkit instead
    'PPTXToolkit',
    'TerminalToolkit',
    'PubMedToolkit',
    'DataCommonsToolkit',
    'ThinkingToolkit',
    'PyAutoGUIToolkit',
    'SearxNGToolkit',
    'JinaRerankerToolkit',
    'OrigeneToolkit',
    'PulseMCPSearchToolkit',
    'KlavisToolkit',
    'ACIToolkit',
    'PlaywrightMCPToolkit',
    'ResendToolkit',
    'WolframAlphaToolkit',
    'BohriumToolkit',
    'OpenAIImageToolkit',  # Backward compatibility
    'TaskPlanningToolkit',
    'HybridBrowserToolkit',
    'EdgeOnePagesMCPToolkit',
    'GoogleDriveMCPToolkit',
    'Crawl4AIToolkit',
    'MarkItDownToolkit',
    'NoteTakingToolkit',
    'AgentCommunicationToolkit',
    'WebDeployToolkit',
    'ScreenshotToolkit',
    'RegisteredAgentToolkit',
    'ToolkitMessageIntegration',
    'ContextSummarizerToolkit',
    'NotionMCPToolkit',
    'VertexAIVeoToolkit',
    'MinimaxMCPToolkit',
]
