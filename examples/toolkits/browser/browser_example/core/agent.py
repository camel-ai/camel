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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Browser Agent utilities.
This module provides Browser agent with low-level `HybridBrowserToolkit` tools.
"""

import json
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.terminators import ResponseWordsTerminator
from camel.toolkits.hybrid_browser_toolkit import (
    EvidenceCaptureConfig,
    HybridBrowserToolkit,
)
from camel.utils.constants import Constants
from examples.toolkits.browser.browser_example.cli.analyze_session import (
    analyze_session,
)
from examples.toolkits.browser.browser_example.core.modeling import (
    create_default_model,
    extract_token_usage,
)
from examples.toolkits.browser.utils.utils import (
    get_timestamp_filename,
    get_timestamp_iso,
)

script_dir = Path(__file__).resolve().parent

# Define default directories using relative paths
DEFAULT_BROWSER_LOG_DIR = script_dir.parent / "browser_log"
DEFAULT_SESSION_LOGS_DIR = script_dir.parent / "session_logs"

WEBSITE_GUIDELINES: dict[str, str] = {
    "allrecipes": "\n".join(
        [
            "- Target site: Allrecipes",
            "- Use the site search to find the recipe/page relevant to the task",
            "- Prefer opening the actual recipe page before extracting information",
            "- If asked about reviews: scroll to the Reviews section and identify the latest review (most recent date/time)",
            "- When multiple similar recipes exist, choose the one that best matches the exact recipe title requested",
        ]
    ),
    "google flights": "\n".join(
        [
            "- All tasks are to be performed on Google Flights",
            "- When entering the date, make sure to click on the date input field first and then type the date in the textbox. Both the date and the departure/destination fields can be confirmed by pressing Enter (enter after input).",
            "- When entering the origin and destination, you do not need to be overly specific; entering the city name is sufficient.",
            "- The date entry process is as follows: first click on the date input field, then type the departure date and the return date into the date fields respectively. Press Enter to confirm the date input and Press Enter to exit the date selection field, and then Click Search to initiate the search.(Only works when all necessary information has been entered, and date selector is invisible).",
            "- If you want to check the current state of the page, call browser_get_page_snapshot. If the Search button is visible in snapshot, this indicates that you have not yet entered the results page. In that case, ensure that all required information (departure, destination, and date) has been fully entered, and then click the Search button to initiate the search.",
            "- The date is for days in 2026 unless otherwise specified.",
        ]
    ),
    "amazon": "\n".join(
        [
            "- Target site: Amazon",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Prefer the site's search box over external search",
            "- Use filters (department, price, rating, Prime) when applicable",
        ]
    ),
    "apple": "\n".join(
        [
            "- Target site: Apple",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use site navigation/menus to reach the relevant product/support page",
            "- Prefer official product specs pages when extracting details",
        ]
    ),
    "arxiv": "\n".join(
        [
            "- Target site: ArXiv",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use ArXiv search and filter/sort when needed (date, relevance)",
            "- Open the paper abstract page before extracting title/authors/links",
        ]
    ),
    "bbc news": "\n".join(
        [
            "- Target site: BBC News",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use site search or section navigation to locate the article",
            "- Open the specific article page before extracting details",
        ]
    ),
    "booking": "\n".join(
        [
            "- Target site: Booking.com",
            "- Always start by calling browser_get_page_snapshot to check the current page state.",
            "- If a cookies/privacy prompt appears, accept it. If a sign-up or account creation window appears, close it.",
            "- Carefully fill in all required fields: destination, dates, and number of guests.",
            "- For date selection:",
            "   • Click the calendar search box to open the calendar widget. once opened, the current month is displayed. now you should select the check-in and check-out dates first without click other element outside the calender, the calendar will close if you do that.",
            "   • To change months, click 'next month' or 'previous month' as needed. You can click these buttons multiple times.",
            "   • Select the check-in date first, then the check-out date in the calendar.",
            "   • To close the calendar widget, click any other element on the page.",
            "- Use available filters and sorting options to find the best match for your criteria.",
            "- Before extracting hotel or property details, open the specific hotel/property page.",
        ]
    ),
    "cambridge dictionary": "\n".join(
        [
            "- Target site: Cambridge Dictionary",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use the dictionary search box to find the word/phrase",
            "- Extract the relevant sense/definition matching the question context",
        ]
    ),
    "coursera": "\n".join(
        [
            "- Target site: Coursera",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use the site search and filters (level, language, duration) when helpful",
            "- Open the course page before extracting details (instructor, syllabus, ratings)",
            "- If there are cookies/privacy popups, close them before proceeding",
        ]
    ),
    "espn": "\n".join(
        [
            "- Target site: ESPN",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use site navigation/search to locate the relevant sport/team/game",
            "- Prefer official boxscore or recap pages for factual details",
        ]
    ),
    "github": "\n".join(
        [
            "- Target site: GitHub",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use repository search/issues/pulls tabs as appropriate",
            "- Open the specific file/issue/PR page before extracting details",
        ]
    ),
    "google map": "\n".join(
        [
            "- Target site: Google Maps",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use the search box to find places and then open the place details panel",
            "- Confirm address/hours/ratings from the place details panel",
        ]
    ),
    "google search": "\n".join(
        [
            "- Target site: Google Search",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Refine the query if results are not relevant",
            "- Open the most relevant result in a new tab before extracting details",
        ]
    ),
    "huggingface": "\n".join(
        [
            "- Target site: Hugging Face",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Use the search box and filters (models, datasets, spaces) as needed",
            "- Open the specific model/dataset page before extracting details",
        ]
    ),
    "wolfram alpha": "\n".join(
        [
            "- Target site: Wolfram Alpha",
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Enter the query precisely and run it",
            "- Extract the relevant result pod(s) matching the question",
        ]
    ),
}


class BrowserAgent:
    """A simple browser agent."""

    _TASK_DONE_TOKEN = "##TASK_DONE##"

    def __init__(
        self,
        *,
        website: str,
        session_log_dir: str | Path | None = None,
        start_url: str | None = None,
        cdp_port: int = 9223,
        use_agent_recovery: bool = True,
        step_timeout: float | None = Constants.TIMEOUT_THRESHOLD,
        tool_execution_timeout: float | None = Constants.TIMEOUT_THRESHOLD,
    ):
        """Initialize the SkillsAgent.
        Args:
            cdp_port: CDP port number
            use_agent_recovery: Use agent recovery for errors
            website: Website name (e.g., "Allrecipes", "Google Flights")
            start_url: Optional URL to navigate to before executing tasks
            step_timeout: Timeout (seconds) for a single ChatAgent step. Use None to disable.
            tool_execution_timeout: Timeout (seconds) for individual tool calls. Use None to disable.
        """
        self.cdp_port = cdp_port
        self.use_agent_recovery = use_agent_recovery
        self.website = website.strip()
        if not self.website:
            raise ValueError(
                "website is required (non-empty). Pass `website=`."
            )
        self.start_url = start_url.strip() if start_url else None
        self.step_timeout = step_timeout
        self.tool_execution_timeout = tool_execution_timeout

        # Initialize components
        self.toolkit: HybridBrowserToolkit | None = None
        self.agent: ChatAgent | None = None

        # Session log directory for this run
        self.session_timestamp = get_timestamp_filename()
        self.toolkit_session_id = (
            f"{self.session_timestamp}_{uuid.uuid4().hex[:8]}"
        )
        self.session_log_dir: Path | None = (
            Path(session_log_dir).expanduser().resolve()
            if session_log_dir is not None
            else None
        )

        # Base directory for session logs
        self.session_logs_root = DEFAULT_SESSION_LOGS_DIR

        # Store current user task (actual task being executed)
        self.current_user_task = None
        self.task_start_iso: str | None = None

        # Statistics tracking
        self.stats = {
            'total_tokens': 0,
            'browser_tool_calls': 0,
            'agent_recovery_calls': 0,
            'token_details': {
                'main_agent': {'prompt': 0, 'completion': 0, 'total': 0},
                'recovery_agent': {'prompt': 0, 'completion': 0, 'total': 0},
            },
            'subtask_details': {},  # Track each subtask call
            'browser_tool_details': {},  # Track each browser tool call
        }

        # Agent communication log
        self.agent_communication_log = []

        # Store system prompt and tool definitions for logging
        self.system_prompt = None
        self.tool_definitions = []

    async def close(self) -> None:
        """Cleanup toolkit resources for this run.

        In CDP mode, this disconnects the toolkit without closing the browser.
        """
        if not self.toolkit:
            return

        try:
            await self.toolkit.disconnect_websocket()
        except AttributeError:
            print(
                "⚠️  Python Toolkit does not have disconnect_websocket method"
            )
        except Exception as e:
            print(f"⚠️  Toolkit cleanup failed: {e}")
        finally:
            self.toolkit = None

    def _get_website_guidelines(self) -> str:
        """Return website-specific browsing guidelines (match-or-fail)."""
        website = self.website.lower()
        try:
            return WEBSITE_GUIDELINES[website]
        except KeyError as e:
            known = ", ".join(sorted(WEBSITE_GUIDELINES))
            raise ValueError(
                f"Unsupported website: {self.website!r}. Add it to WEBSITE_GUIDELINES. Known: {known}"
            ) from e

    async def _pre_navigate_if_needed(self) -> None:
        """Optionally navigate to start_url to keep tasks website-agnostic."""
        if not self.toolkit or not self.start_url:
            return

        try:
            tabs = await self.toolkit.browser_get_tab_info()
            current_url = None
            if isinstance(tabs, list):
                for tab in tabs:
                    if isinstance(tab, dict) and tab.get("is_current"):
                        current_url = tab.get("url")
                        break

            if (not current_url) or current_url == "about:blank":
                print(
                    f"\n🌐 Pre-navigate: current URL is blank, visiting {self.start_url}"
                )
                await self.toolkit.browser_visit_page(self.start_url)
                return

            cur = urlparse(current_url)
            tgt = urlparse(self.start_url)
            if cur.netloc and tgt.netloc and cur.netloc != tgt.netloc:
                print(
                    f"\n🌐 Pre-navigate: switching domain {cur.netloc} → {tgt.netloc}"
                )
                await self.toolkit.browser_visit_page(self.start_url)
        except Exception as e:
            print(f"⚠️  Pre-navigation failed: {e}")

    async def initialize(self):
        """Initialize toolkit and agent."""
        print("=" * 80)
        print("INITIALIZING BROWSER AGENT")
        print("=" * 80)

        # Create session log directory (caller can override the directory so that
        # all outputs are grouped under a single run folder).
        if self.session_log_dir is None:
            self.session_log_dir = (
                self.session_logs_root / f"session_{self.session_timestamp}"
            )
        self.session_log_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Session log directory: {self.session_log_dir}")
        print("   All logs for this session will be saved here\n")

        # Use a per-session browser log dir to avoid mixing logs across runs.
        browser_log_dir = self.session_log_dir / "browser_log"
        browser_log_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Browser log directory: {browser_log_dir}\n")
        # cdp_url = None
        # try:
        #     # Use /json/version to get the browser-level WebSocket endpoint
        #     with urlopen(
        #         f'http://localhost:{self.cdp_port}/json/version', timeout=5
        #     ) as response:
        #         version_info = json.loads(response.read().decode('utf-8'))
        #         cdp_url = version_info.get('webSocketDebuggerUrl')
        #         print(
        #             f"✓ Connected to browser: {version_info.get('Browser', 'N/A')}"
        #         )
        #         print(f"   CDP endpoint: {cdp_url}")
        # except Exception as e:
        #     print(f"Error connecting to browser: {e}")
        #     return False

        # if not cdp_url:
        #     print("Error: Could not get browser CDP endpoint")
        #     return False

        custom_tools = [
            "browser_visit_page",
            "browser_back",
            "browser_forward",
            "browser_click",
            "browser_type",
            "browser_switch_tab",
            "browser_get_tab_info",
            "browser_enter",
            "browser_get_page_snapshot",
            # "browser_get_som_screenshot",
            # remove it to achieve faster operation
            # "browser_press_key",
            # "browser_console_view",
            # "browser_console_exec",
            # "browser_mouse_drag",
        ]
        # Vision-WebJudge evidence should live at session root so the session
        # directory is portable and can be evaluated offline.
        evidence_dir = Path(self.session_log_dir) / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        # Initialize toolkit (single instance, shared by agent and replay)
        self.toolkit = HybridBrowserToolkit(
            enabled_tools=custom_tools,
            headless=False,
            stealth=True,
            cache_dir=str(evidence_dir),
            evidence_capture=EvidenceCaptureConfig(
                enabled=True, snapshot=True, screenshot=True
            ),
            browser_log_to_file=True,
            log_dir=str(browser_log_dir),
            viewport_limit=False,
            session_id=self.toolkit_session_id,
            connect_over_cdp=True,
            # cdp_url=cdp_url,
            default_start_url=None,
            # cdp_keep_current_page=True,  # Important: Keep existing page when connecting via CDP
        )

        # When connecting via CDP, browser is already open, no need to call browser_open()
        # await self.toolkit.browser_open()
        print("✓ Browser connected via CDP")

        # Create ChatAgent with both subtask functions and toolkit
        print("\n" + "=" * 80)
        print("CREATING CHAT AGENT")
        print("=" * 80)

        model = create_default_model()

        print("✓ Model created")

        # Get toolkit tools - use them directly without wrapping
        # FunctionTool objects already have proper signatures
        browser_tools = self.toolkit.get_tools()
        print(f"✓ Got {len(browser_tools)} browser tools")

        # Combine all tools
        all_tools = [*browser_tools]
        print(
            f"✓ Total tools: {len(all_tools)} ({len(browser_tools)} browser)"
        )

        # Get system prompt before creating agent
        self.system_prompt = self.get_system_message()

        # Create agent with system message
        print("Creating ChatAgent...")
        system_message = BaseMessage.make_assistant_message(
            role_name="Browser Automation Agent", content=self.system_prompt
        )

        self.agent = ChatAgent(
            model=model,
            tools=all_tools,
            system_message=system_message,
            step_timeout=self.step_timeout,
            tool_execution_timeout=self.tool_execution_timeout,
            response_terminators=[
                ResponseWordsTerminator({self._TASK_DONE_TOKEN: 1})
            ],
            max_iteration=50,
        )

        print("✓ Agent created successfully with system prompt")

        # Collect tool definitions (name + docstring)
        self.tool_definitions = []

        # Browser tools
        for tool in browser_tools:
            tool_info = {
                'type': 'browser_tool',
                'name': tool.func.__name__
                if hasattr(tool.func, '__name__')
                else str(tool),
                'docstring': tool.func.__doc__
                if hasattr(tool.func, '__doc__')
                else None,
            }
            self.tool_definitions.append(tool_info)
        return True

    def get_system_message(self) -> str:
        """Get the system message for the agent."""
        # Build prompt parts dynamically
        prompt_parts = []

        # Base prompt (always)
        prompt_parts.extend(
            [
                "You are a browser automation agent.",
                "",
                "MANDATORY RULES:",
                "1. You MUST use browser tools to complete the task. Do not answer from memory.",
                "2. Your FIRST action MUST be calling browser_get_page_snapshot.",
                "3. If you are not on the target website, navigate there using browser_visit_page.",
                "4. After key actions (navigation/click/type), call browser_get_page_snapshot to verify state.",
                "5. Do NOT give a final answer unless a page snapshot clearly contains the requested information.",
                "   - If the result is still loading or missing, keep using tools (snapshot/scroll/click) until it appears.",
                "6. When you are fully done (success OR you have exhausted reasonable attempts), end your final message with:",
                f"   {self._TASK_DONE_TOKEN}",
                "",
            ]
        )

        if self.website:
            prompt_parts.append(f"WEBSITE NAME: {self.website}")
        if self.start_url:
            prompt_parts.append(f"START URL: {self.start_url}")
        if self.website or self.start_url:
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "WEBSITE-SPECIFIC GUIDELINES:",
                self._get_website_guidelines(),
                "",
            ]
        )
        # Agent without subtasks - simpler prompt
        prompt_parts.extend(
            [
                "GUIDELINES:",
                "1. Use the available browser tools to complete the task step by step",
                "2. Always verify the current state of the page before taking actions",
                "3. If an action fails, analyze the page state and adjust your approach",
                "",
            ]
        )
        return "\n".join(prompt_parts)

    async def run(self, user_task: str):
        """Run the agent with a user task.

        Args:
            user_task: The task for the agent to complete
        """
        # Store the current user task for logging
        self.current_user_task = user_task
        self.task_start_iso = get_timestamp_iso()

        print("\n" + "=" * 80)
        print("AGENT EXECUTION")
        print("=" * 80)
        print(f"Task: {user_task}")
        print()

        print("\n" + "🤖 " + "=" * 78)
        print("AGENT STARTING TO PROCESS TASK")
        print("=" * 80)

        # Log the user task
        timestamp = self.task_start_iso

        communication_entry = {
            'timestamp': timestamp,
            'type': 'main_agent_call',
            'user_task': user_task,
            'response': None,
            'tool_calls': [],  # Will store all tool calls made by agent
            'tokens': {'prompt': 0, 'completion': 0, 'total': 0},
        }

        await self._pre_navigate_if_needed()

        # Use astep like hybrid_browser_toolkit_example.py
        print("\nSending task to agent...")
        task_with_context = f"{user_task}\n\nTARGET WEBSITE:\n- web_name: {self.website}\n- web: {self.start_url or ''}\n"
        print(f"\nFull task with context:\n{task_with_context}\n")
        response = await self.agent.astep(task_with_context)

        # Log the response
        if response.msgs:
            for msg in response.msgs:
                content = msg.content or ""
                communication_entry['response'] = content.replace(
                    self._TASK_DONE_TOKEN, ""
                ).strip()

                # Extract tool calls from the message
                if hasattr(msg, 'info') and msg.info:
                    if 'tool_calls' in msg.info:
                        tool_calls_info = msg.info['tool_calls']
                        if isinstance(tool_calls_info, list):
                            for tool_call in tool_calls_info:
                                if isinstance(tool_call, dict):
                                    communication_entry['tool_calls'].append(
                                        tool_call
                                    )

        print("\n" + "=" * 80)
        print("AGENT EXECUTION COMPLETED")
        print("=" * 80)
        print("Response:")
        if response.msgs:
            print(
                (response.msgs[0].content or "")
                .replace(self._TASK_DONE_TOKEN, "")
                .strip()
            )
        else:
            print("<no response>")
        print()

        # Extract token usage from agent response
        if hasattr(response, 'info') and response.info:
            if 'usage' in response.info:
                token_usage = extract_token_usage(response.info['usage'])
                prompt_tokens = token_usage['prompt']
                completion_tokens = token_usage['completion']
                total_tokens = token_usage['total']

                if total_tokens > 0:
                    self.stats['token_details']['main_agent']['prompt'] += (
                        prompt_tokens
                    )
                    self.stats['token_details']['main_agent'][
                        'completion'
                    ] += completion_tokens
                    self.stats['token_details']['main_agent']['total'] += (
                        total_tokens
                    )
                    self.stats['total_tokens'] += total_tokens

                    # Update communication entry
                    communication_entry['tokens'] = {
                        'prompt': prompt_tokens,
                        'completion': completion_tokens,
                        'total': total_tokens,
                    }

                    print("\n📊 Tokens used in this agent call:")
                    print(f"   • Prompt: {prompt_tokens}")
                    print(f"   • Completion: {completion_tokens}")
                    print(f"   • Total: {total_tokens}")

        # Save communication entry
        self.agent_communication_log.append(communication_entry)

        # Note: Browser tool calls are extracted from the browser log file
        # in save_communication_log() method, not from response.info
        # This ensures we capture all browser actions with full details

        return response

    def _extract_agent_browser_calls(self):
        """Extract browser tool calls made directly by agent (not from subtask replay).

        Returns:
            List of browser action records from the log file that were initiated by the agent.
        """

        print("\n" + "=" * 80)
        print("🔍 EXTRACTING AGENT BROWSER CALLS FROM LOG FILE")
        print("=" * 80)

        # Find the browser log file
        browser_log_dir = DEFAULT_BROWSER_LOG_DIR
        if self.session_log_dir:
            session_browser_log_dir = self.session_log_dir / "browser_log"
            if session_browser_log_dir.exists():
                browser_log_dir = session_browser_log_dir

        if not browser_log_dir.exists():
            print("⚠️  Warning: Browser log directory not found")
            print(f"   Expected: {browser_log_dir}")
            return []

        print(f"✓ Browser log directory found: {browser_log_dir.absolute()}")

        # Get the most recent browser log file (contains ALL actions)
        all_log_files = sorted(
            [
                f
                for f in browser_log_dir.glob("hybrid_browser_toolkit*.log")
                if not f.name.startswith('typescript')
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not all_log_files:
            print("⚠️  Warning: No browser log files found")
            return []

        browser_log_file = all_log_files[0]
        print(f"\n📂 Reading complete browser log from: {browser_log_file}")

        # Read all actions from browser log
        # The log file contains multiple JSON objects concatenated together
        # separated by newlines (format: }\n{)
        all_browser_actions = []
        try:
            with open(browser_log_file, 'r', encoding='utf-8') as f:
                content = f.read()

                # Split by }\n{ to separate JSON objects
                # Add back the braces that were removed by split
                json_strings = content.split('}\n{')

                for i, json_str in enumerate(json_strings):
                    if not json_str.strip():
                        continue

                    # Add back the braces
                    if i == 0:
                        # First object: already has opening {, needs closing }
                        json_str = json_str + '}'
                    elif i == len(json_strings) - 1:
                        # Last object: already has closing }, needs opening {
                        json_str = '{' + json_str
                    else:
                        # Middle objects: need both braces
                        json_str = '{' + json_str + '}'

                    try:
                        action = json.loads(json_str)
                        all_browser_actions.append(action)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Failed to parse JSON object {i + 1}: {e}")
                        # Show first 100 chars for debugging
                        print(f"   Content preview: {json_str[:100]}")
                        continue

        except Exception as e:
            print(f"⚠️  Error reading browser log: {e}")
            import traceback

            traceback.print_exc()
            return []

        print(
            f"   Found {len(all_browser_actions)} total browser actions in log"
        )
        if self.toolkit_session_id:
            all_browser_actions = [
                a
                for a in all_browser_actions
                if a.get('session_id') == self.toolkit_session_id
            ]
            print(
                f"   Filtered to {len(all_browser_actions)} actions for session_id={self.toolkit_session_id}"
            )

        # Filter browser actions
        agent_initiated_actions = []

        for action in all_browser_actions:
            action_timestamp = action.get('timestamp', '')
            action_name = action.get('action', '')

            if not action_timestamp:
                continue

            # This is an agent-initiated action
            agent_initiated_actions.append(
                {
                    'timestamp': action_timestamp,
                    'type': 'browser_tool_call',
                    'tool_name': f"browser_{action_name}",
                    'arguments': action.get('inputs', {}),
                    'result': action.get('outputs', {}),
                    'execution_time_ms': action.get('execution_time_ms', 0),
                }
            )

        print(f"\n   Agent-initiated actions: {len(agent_initiated_actions)}")
        print(
            f"   Replay actions (filtered out): {len(all_browser_actions) - len(agent_initiated_actions)}"
        )

        # Update statistics
        self.stats['browser_tool_calls'] = len(agent_initiated_actions)
        for action in agent_initiated_actions:
            tool_name = action['tool_name']
            if tool_name not in self.stats['browser_tool_details']:
                self.stats['browser_tool_details'][tool_name] = 0
            self.stats['browser_tool_details'][tool_name] += 1

        return agent_initiated_actions

    def print_statistics(self):
        """Print comprehensive statistics about the task execution."""
        print("\n" + "=" * 80)
        print("📊 TASK EXECUTION STATISTICS")
        print("=" * 80)

        print(f"\n🔧 Browser Tool Calls: {self.stats['browser_tool_calls']}")
        if self.stats['browser_tool_details']:
            for tool_name, count in self.stats['browser_tool_details'].items():
                print(f"   • {tool_name}: {count} call(s)")
        elif self.stats['browser_tool_calls'] == 0:
            print(
                "   Note: Browser tool calls made by the agent are not tracked separately."
            )
            print(
                "   Tool calls within subtasks are included in subtask execution."
            )

        print(f"\n💰 Total Tokens Used: {self.stats['total_tokens']}")
        print("   Main Agent:")
        print(
            f"      • Prompt: {self.stats['token_details']['main_agent']['prompt']} tokens"
        )
        print(
            f"      • Completion: {self.stats['token_details']['main_agent']['completion']} tokens"
        )
        print(
            f"      • Total: {self.stats['token_details']['main_agent']['total']} tokens"
        )
        print("\n" + "=" * 80)

    def save_communication_log(self):
        """Save all agent communications to a JSON file."""
        # Extract browser tool calls from browser log file
        browser_tool_calls_from_log = self._extract_agent_browser_calls()

        # Merge browser tool calls from log into agent communication log
        all_communications_list = (
            self.agent_communication_log + browser_tool_calls_from_log
        )

        # Sort all communications by timestamp
        sorted_communications = sorted(
            all_communications_list, key=lambda x: x.get('timestamp', '')
        )

        # Combine all communications
        # Use current user task if available, otherwise fall back to config task
        task_desc = self.current_user_task or self.subtask_config.get(
            'task_description', ''
        )

        all_communications = {
            'session_start': get_timestamp_iso(),
            'task_start': self.task_start_iso,
            'task_description': task_desc,
            'website': self.website,
            'start_url': self.start_url,
            'toolkit_session_id': self.toolkit_session_id,
            'system_prompt': self.system_prompt,  # Add system prompt
            'tool_definitions': self.tool_definitions,  # Add tool definitions
            'communications': sorted_communications,  # All communications in chronological order
            'statistics': self.stats,
            'summary': {
                'total_communications': len(sorted_communications),
                'browser_tool_calls': len(
                    [
                        c
                        for c in sorted_communications
                        if c.get('type') == 'browser_tool_call'
                    ]
                ),
                'main_agent_calls': len(
                    [
                        c
                        for c in sorted_communications
                        if c.get('type') == 'main_agent_call'
                    ]
                ),
                'total_tools': len(self.tool_definitions),
            },
        }

        # Save to session directory if available
        if self.session_log_dir:
            log_path = self.session_log_dir / "agent_communication_log.json"
        else:
            log_filename = (
                f"agent_communication_log_{get_timestamp_filename()}.json"
            )
            log_path = Path("camel_logs") / log_filename
            log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(all_communications, f, indent=2, ensure_ascii=False)

        print(f"\n📝 Agent communication log saved to: {log_path}")
        print(
            f"   Total communications logged: {all_communications['summary']['total_communications']}"
        )
        print(
            f"   - Main agent calls: {all_communications['summary']['main_agent_calls']}"
        )
        print(
            f"   - Browser tool calls: {all_communications['summary']['browser_tool_calls']}"
        )
        # Copy browser log to session directory
        if self.session_log_dir:
            browser_log_dir = self.session_log_dir / "browser_log"
            if not browser_log_dir.exists():
                browser_log_dir = DEFAULT_BROWSER_LOG_DIR

            if browser_log_dir.exists():
                # Get the most recent browser log
                all_log_files = sorted(
                    [
                        f
                        for f in browser_log_dir.glob(
                            "hybrid_browser_toolkit*.log"
                        )
                        if not f.name.startswith('typescript')
                    ],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if all_log_files:
                    browser_log_file = all_log_files[0]
                    dest_file = (
                        self.session_log_dir / "complete_browser_log.log"
                    )
                    shutil.copy2(browser_log_file, dest_file)
                    print(f"\n📋 Complete browser log copied to: {dest_file}")
                    print(f"   Source: {browser_log_file}")

        # Auto-generate timeline analysis
        self._generate_timeline_analysis()

    def _generate_timeline_analysis(self):
        """Auto-generate timeline analysis from session logs."""
        if not self.session_log_dir or not self.session_log_dir.exists():
            print(
                "\n⚠️  Session directory not found, skipping timeline analysis"
            )
            return

        print("\n" + "=" * 80)
        print("📊 GENERATING TIMELINE ANALYSIS")
        print("=" * 80)

        try:
            print(f"\n🔍 Analyzing session: {self.session_log_dir}")

            # Run the analysis
            analyze_session(str(self.session_log_dir))

            print("\n✅ Timeline analysis completed successfully!")

        except Exception as e:
            print(f"\n⚠️  Error during timeline analysis: {e}")
            import traceback

            traceback.print_exc()

    def save_memory(self, path: Path | str | None = None):
        """Save agent memory to a file (if applicable)."""
        if not path:
            path = self.session_log_dir / "agent_memory.json"
        self.agent.save_memory(path)


__all__ = ["BrowserAgent"]
