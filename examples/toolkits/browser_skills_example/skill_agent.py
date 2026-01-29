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
# ruff: noqa: E402
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SkillsAgent utilities for `browser_skills_example`.

This module provides `SkillsAgent`, which wraps reusable subtasks as callable
functions and combines them with low-level `HybridBrowserToolkit` tools.
"""

import json
import shutil
import sys
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path first (before camel imports)
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from urllib.parse import urlparse

from utils import (
    create_default_model,
    extract_token_usage,
    get_timestamp_filename,
    get_timestamp_iso,
)

from camel.agents import ChatAgent, observe
from camel.messages import BaseMessage
from camel.terminators import ResponseWordsTerminator
from camel.toolkits.hybrid_browser_toolkit import (
    EvidenceCaptureConfig,
    HybridBrowserToolkit,
)
from camel.utils.constants import Constants

# Define default directories using relative paths
DEFAULT_BROWSER_LOG_DIR = script_dir.parent / "browser_log"
DEFAULT_SESSION_LOGS_DIR = script_dir.parent / "session_logs"

WEB_VOYAGER_GUIDELINES: Dict[str, str] = {
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
            "- Target site: Google Flights (https://www.google.com/travel/flights)",
            "- All tasks must be performed exclusively on Google Flights",
            "- Handle consent dialogs: If any cookie, privacy, or consent pop-ups appear, accept or dismiss them before continuing",
            "- When entering the origin and destination, typing the city name only is sufficient (airport codes are not required)",
            "- The date is for days in 2026 unless otherwise specified",
            "- Date entry procedure: Click the date input field, type the departure date and then the return date into their respective fields, press Enter to confirm the dates, press Enter again to exit the date selector, and ensure the date selector is no longer visible before proceeding",
            "- After entering the origin, destination, and dates, you must explicitly click the Search button to initiate the search; do not assume results are shown automatically",
            "- Before extracting any information, ensure the search results page has loaded",
            "- If you need to check the current page state, call browser_get_page_snapshot",
            "- If the Search button is visible in the page snapshot, this indicates you are still on the input page; verify that all required fields are completed and click the Search button",
            "- Never extract information from the pre-search or input page"
            "- Do use get_page_snapshot consequently as they will have the same results if you do not do any other actions in between",
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
            "- Start by calling browser_get_page_snapshot to see where you are",
            "- Fill the destination and click the dropdown selector. "
            "- Fill the dates using paged calendar selector, carefully selecting the correct month and days. "
            "- Click the Search button to get results.",
            "- Use filters/sorting to find the best match",
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
            "- Handle consent dialogs: If any cookie, privacy, or consent pop-ups appear, accept or dismiss them before continuing",
            "- Initial state check: Start by calling browser_get_page_snapshot to understand the current page structure and available elements.",
            "- Search strategy: Use the site's search bar to enter relevant keywords. Apply available filters (topic, level, language, duration, etc.) when they help narrow down results.",
            "- Execute search: After filling the search field and/or configuring filters, explicitly click the search button to load the results page.",
            "- Data extraction: From the course page, extract key details such as instructor(s), syllabus, ratings, and other relevant metadata.",
            "- Once one the course page, we can just do the extraction without searching again and give me the response directly.",
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
    )
}


NAVI_BENCH_GUIDELINES: Dict[str, str] = {
    "apartments.com": "\n".join(
        [
            "- Target site: https://www.apartments.com/",
            "- Use site search/filters on the page; avoid external search.",
            "- Use short keywords to search, the search input accepts multiple regions search, Click the dropdown suggestions to confirm one search region, ",
            "and repeatly add multiple demand regions, until you've confirmed all required regions are added.",
            "- Only if you've add all regions, you can continue to configure other filter conditions.",
            "- Navi-Bench often verifies the FINAL URL; apply only the filters required by the task (avoid extra filters).",
            "- After applying filters, call browser_get_tab_info to confirm the URL reflects the required constraints.",
            "- If results use infinite scroll or lazy loading, scroll a bit to ensure listings are loaded before you stop.",
            "- If the task asks for an overview, base it on visible results (do not guess counts).",
        ]
    ),
    "craigslist": "\n".join(
        [
            "- Target site: Craigslist",
            "- Prefer applying filters directly on the search page (price, bedrooms, posted today, rent period, etc.)",
            "- Navi-Bench commonly verifies the URL query parameters EXACTLY; apply only the filters required by the task (avoid extra filters).",
            "- After applying filters, call browser_get_tab_info and confirm the URL query parameters reflect the required constraints.",
            "- If asked to extract listing details, open each listing page and capture the required fields + URL",
        ]
    ),
    "opentable": "\n".join(
        [
            "- Target site: OpenTable",
            "- Ensure location/restaurant, date, time, and party size are correctly set (use the UI controls).",
            "- For dropdown/combobox controls (party size, time, filters), prefer browser_select(ref=..., value=...) instead of repeatedly clicking; options may not have clickable refs.",
            "- After changing key constraints (date/time/party size), call browser_get_tab_info and confirm the URL/state reflects the requested constraints before moving on.",
            "- If the task is about availability, stay on the results/reservation page that shows available times (or the no-availability message).",
            "- Scroll within results so availability/no-availability sections are visible before finishing.",
            "- Avoid navigating away at the end; keep the final page on the relevant OpenTable results/restaurant page.",
        ]
    ),
    "resy": "\n".join(
        [
            "- Target site: Resy",
            "- Ensure venue/date/time/party size are correctly set (use the UI controls).",
            "- For dropdown/combobox controls (Guests, Date, Time), prefer browser_select(ref=..., value=...) instead of repeatedly clicking; options may not have clickable refs.",
            "- Resy tasks are often verified via the FINAL URL query (e.g., seats/date/time). After setting party size/date/time, call browser_get_tab_info and confirm URL query matches the task (e.g., seats=11, time=1630, date=YYYY-MM-DD).",
            "- If the UI only provides an approximate option, still ensure the URL uses the exact required value. If it doesn't, directly visit the correct URL.",
            "- If there is no availability, confirm the page shows the no-availability indicator (may require scrolling).",
            "- If a specific time is requested but not available, ensure nearby time slots are visible so the page clearly indicates unavailability.",
            "- Avoid navigating away at the end; keep the final page on the relevant Resy booking page.",
        ]
    )
}


WEBSITE_GUIDELINES = WEB_VOYAGER_GUIDELINES | NAVI_BENCH_GUIDELINES


class SubtaskFunction:
    """Wrapper for a subtask that can be called as a function."""

    def __init__(
        self,
        subtask_id: str,
        name: str,
        description: str,
        variables: Dict[str, Any],
        replayer: Any,
        stats_tracker: Optional[Dict[str, Any]] = None,
        session_log_dir: Optional[Path] = None,
    ):
        """Initialize subtask function.

        Args:
            subtask_id: Subtask ID
            name: Subtask name
            description: Subtask description
            variables: Variable definitions
            replayer: ActionReplayer instance
            stats_tracker: Reference to agent's stats dict for tracking
            session_log_dir: Directory to save session logs
        """
        self.subtask_id = subtask_id
        self.name = name
        self.description = description
        self.variables = variables
        self.replayer = replayer
        self.last_result = None
        self.stats_tracker = stats_tracker
        self.session_log_dir = session_log_dir

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the subtask with given variable values.

        Args:
            **kwargs: Variable values (e.g., departure_city="London")

        Returns:
            Execution result with status and snapshot
        """

        # Track subtask call
        if self.stats_tracker is not None:
            self.stats_tracker['subtask_calls'] += 1
            if self.subtask_id not in self.stats_tracker['subtask_details']:
                self.stats_tracker['subtask_details'][self.subtask_id] = {
                    'name': self.name,
                    'calls': 0,
                    'variables_used': [],
                }
            self.stats_tracker['subtask_details'][self.subtask_id][
                'calls'
            ] += 1
            self.stats_tracker['subtask_details'][self.subtask_id][
                'variables_used'
            ].append(kwargs)

        print(f"\n{'🎯 ' + '=' * 78}")
        print(f"EXECUTING SUBTASK: {self.name}")
        print(f"{'=' * 80}")
        print(f"📋 Subtask ID: {self.subtask_id}")
        print(f"📝 Description: {self.description}")

        if kwargs:
            print("🔧 Input Variables:")
            for key, value in kwargs.items():
                print(f"   • {key} = {value}")
        else:
            print("🔧 No input variables (fixed operation)")
        print()

        # Set variables in replayer
        self.replayer.subtask_id = self.subtask_id
        self.replayer.variable_overrides = kwargs
        self.replayer.load_subtask_config()

        # Debug: Check if agent recovery is enabled
        print(
            f"🔍 Debug: use_agent_recovery = {self.replayer.use_agent_recovery}"
        )
        print(f"🔍 Debug: recovery_agent = {self.replayer.recovery_agent}")

        # Track recovery calls before execution
        recovery_calls_before = len(
            getattr(self.replayer, 'recovery_history', [])
        )

        # Execute replay
        try:
            print("▶️  Starting subtask execution...")
            print(f"{'─' * 80}\n")

            # Execute the subtask
            execution_result = await self.replayer.replay_subtask()

            # Track recovery calls after execution
            recovery_calls_after = len(
                getattr(self.replayer, 'recovery_history', [])
            )
            recovery_calls_made = recovery_calls_after - recovery_calls_before
            if self.stats_tracker is not None and recovery_calls_made > 0:
                self.stats_tracker['agent_recovery_calls'] += (
                    recovery_calls_made
                )

                # Sum up tokens from new recovery calls
                recovery_history = getattr(
                    self.replayer, 'recovery_history', []
                )
                for i in range(recovery_calls_before, recovery_calls_after):
                    if i < len(recovery_history):
                        record = recovery_history[i]
                        prompt_tokens = record.get('prompt_tokens', 0)
                        completion_tokens = record.get('completion_tokens', 0)
                        total_tokens = record.get(
                            'tokens_used', prompt_tokens + completion_tokens
                        )

                        self.stats_tracker['token_details']['recovery_agent'][
                            'prompt'
                        ] += prompt_tokens
                        self.stats_tracker['token_details']['recovery_agent'][
                            'completion'
                        ] += completion_tokens
                        self.stats_tracker['token_details']['recovery_agent'][
                            'total'
                        ] += total_tokens
                        self.stats_tracker['total_tokens'] += total_tokens

            print(f"\n{'─' * 80}")
            print("✅ Subtask Execution Result:")
            print(f"   Status: {execution_result['status']}")
            print(
                f"   Successful actions: {len(execution_result['successful_actions'])}"
            )
            print(
                f"   Failed actions: {len(execution_result['failed_actions'])}"
            )
            print(
                f"   Skipped actions: {len(execution_result['skipped_actions'])}"
            )

            # Get final snapshot
            print("\n📸 Getting final page snapshot...")
            final_snapshot = (
                await self.replayer.toolkit.browser_get_page_snapshot()
            )
            snapshot_preview = (
                final_snapshot[:200] + "..."
                if len(final_snapshot) > 200
                else final_snapshot
            )
            print(f"   Snapshot length: {len(final_snapshot)} chars")
            print(f"   Preview: {snapshot_preview}")

            result = {
                'status': 'success'
                if execution_result['all_successful']
                else 'partial_success',
                'message': f"Subtask '{self.name}' completed. {len(execution_result['successful_actions'])} successful, {len(execution_result['failed_actions'])} failed",
                'snapshot': final_snapshot,
                'variables_used': kwargs,
                'execution_details': execution_result,
            }

            # Save replay actions to separate log file
            if (
                hasattr(self.replayer, 'replay_actions_log')
                and self.replayer.replay_actions_log
            ):
                # Save to session log directory if available, otherwise to browser_log
                if self.session_log_dir:
                    replay_log_file = (
                        self.session_log_dir
                        / f"subtask_{self.subtask_id}_replay_actions.json"
                    )
                else:
                    # Use browser_log default path
                    replay_log_dir = DEFAULT_BROWSER_LOG_DIR
                    replay_log_dir.mkdir(parents=True, exist_ok=True)
                    replay_log_file = (
                        replay_log_dir
                        / f"subtask_replay_actions_{get_timestamp_filename()}.json"
                    )

                replay_log_file.parent.mkdir(parents=True, exist_ok=True)

                with open(replay_log_file, 'w', encoding='utf-8') as f:
                    json.dump(
                        {
                            'subtask_id': self.subtask_id,
                            'subtask_name': self.name,
                            'variables_used': kwargs,
                            'actions': self.replayer.replay_actions_log,
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

                print(f"\n📝 Replay actions logged to: {replay_log_file}")
                print(
                    f"   Total replay actions: {len(self.replayer.replay_actions_log)}"
                )

                # Clear the log for next execution
                self.replayer.replay_actions_log.clear()

            print("\n✅ SUBTASK COMPLETED SUCCESSFULLY")
            print(f"{'=' * 80}\n")

            self.last_result = result
            return result

        except Exception as e:
            print("\n❌ SUBTASK EXECUTION FAILED")
            print(f"   Error: {e!s}")
            print(f"{'=' * 80}\n")

            import traceback

            traceback.print_exc()

            result = {
                'status': 'error',
                'message': f"Subtask '{self.name}' failed: {e!s}",
                'snapshot': '',
                'variables_used': kwargs,
                'error': str(e),
            }
            self.last_result = result
            return result

    def get_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for this subtask.

        Returns:
            OpenAI function schema
        """
        # Build parameters from variables
        parameters = {"type": "object", "properties": {}, "required": []}

        if self.variables:
            for var_name, var_config in self.variables.items():
                parameters["properties"][var_name] = {
                    "type": "string",
                    "description": var_config['description'],
                }
                parameters["required"].append(var_name)

            description = f"{self.description}. Variables: {', '.join(self.variables.keys())}"
        else:
            # No variables - fixed operation
            description = f"{self.description}. This is a fixed operation with no parameters."

        return {
            "name": f"subtask_{self.subtask_id}",
            "description": description,
            "parameters": parameters,
        }


class SkillsAgent:
    """Agent that can execute subtasks as functions."""

    _TASK_DONE_TOKEN = "##TASK_DONE##"

    def __init__(
        self,
        skills_dir: str,
        *,
        website: str,
        session_log_dir: str | Path | None = None,
        start_url: str | None = None,
        use_agent_recovery: bool = True,
        step_timeout: float | None = Constants.TIMEOUT_THRESHOLD,
        step_timeout_max_retries: int = 0,
        tool_execution_timeout: float | None = Constants.TIMEOUT_THRESHOLD,
        enable_skills: bool = True,
    ):
        """Initialize the SkillsAgent.

        Args:
            skills_dir: Path to skills storage directory. Supports:
                - Skills folders: `<skills_dir>/*/SKILL.md` (+ actions.json)
                - Legacy configs: `<skills_dir>/*_subtasks.json`
            use_agent_recovery: Use agent recovery for errors
            website: Website name (e.g., "Allrecipes", "Google Flights")
            start_url: Optional URL to navigate to before executing tasks
            step_timeout: Timeout (seconds) for a single ChatAgent step. Use None to disable.
            step_timeout_max_retries: Maximum retry attempts when a step times out. (default: 0)
            tool_execution_timeout: Timeout (seconds) for individual tool calls. Use None to disable.
            enable_skills: Enable skill loading, usage, and generation (default: True)
        """
        self.skills_dir = Path(skills_dir)
        self.use_agent_recovery = use_agent_recovery
        self.website = website.strip()
        if not self.website:
            raise ValueError(
                "website is required (non-empty). Pass `website=`."
            )
        self.start_url = start_url.strip() if start_url else None
        self.step_timeout = step_timeout
        self.step_timeout_max_retries = step_timeout_max_retries
        self.tool_execution_timeout = tool_execution_timeout
        self.enable_skills = enable_skills

        # Load all subtask configurations from directory
        self.subtask_configs = []  # List of (log_file, config) tuples
        if self.enable_skills:
            self._load_subtask_configs()
        else:
            print("\n⚠️  Skills disabled: Skipping skill loading")
            print("   Agent will operate using browser tools only\n")
            self.subtask_config = {}

        # Initialize components
        self.toolkit: Optional[HybridBrowserToolkit] = None
        self.agent: Optional[ChatAgent] = None
        self.subtask_functions: Dict[str, SubtaskFunction] = {}

        # Session log directory for this run
        self.session_timestamp = get_timestamp_filename()
        self.toolkit_session_id = (
            f"{self.session_timestamp}_{uuid.uuid4().hex[:8]}"
        )
        self.session_log_dir: Optional[Path] = (
            Path(session_log_dir).expanduser().resolve()
            if session_log_dir is not None
            else None
        )

        # Base directory for session logs
        self.session_logs_root = DEFAULT_SESSION_LOGS_DIR

        # Store current user task (actual task being executed)
        self.current_user_task = None
        self.task_start_iso: Optional[str] = None

        # Statistics tracking
        self.stats = {
            'total_tokens': 0,
            'subtask_calls': 0,
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

    def _load_subtask_configs(self):
        """Load all skills/subtasks from the directory."""
        if not self.skills_dir.exists():
            print(
                f"\n⚠️  Subtask config directory not found: {self.skills_dir}"
            )
            print("📁 Creating directory...")
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            print(
                "✓ Directory created. No subtasks available yet (will be populated as tasks are analyzed).\n"
            )
            # Set empty config for backwards compatibility
            self.subtask_config = {}
            return

        if not self.skills_dir.is_dir():
            raise ValueError(f"Path is not a directory: {self.skills_dir}")

        # Prefer Skills folders (SKILL.md) when present.
        skill_dirs = sorted(
            [
                p
                for p in self.skills_dir.iterdir()
                if p.is_dir() and (p / "SKILL.md").exists()
            ]
        )
        if skill_dirs:
            from skill_loader import SkillLoader

            loader = SkillLoader(str(self.skills_dir))
            all_subtasks = loader.load_all_skills()

            if not all_subtasks:
                print(f"\n📝 No skills found in: {self.skills_dir}")
                self.subtask_config = {}
                return

            print(
                f"✓ Loaded {len(all_subtasks)} skill(s) from: {self.skills_dir}"
            )
            for subtask in all_subtasks:
                skill_id = str(subtask.get("id", ""))
                log_file = loader.skill_log_files.get(skill_id)
                self.subtask_configs.append(
                    (log_file, {"subtasks": [subtask]})
                )

            # For backwards compatibility
            self.subtask_config = self.subtask_configs[0][1]
            return

        # Legacy: Find all subtask config files in the directory
        config_files = sorted(self.skills_dir.glob("*_subtasks.json"))

        if not config_files:
            print(f"\n📝 No subtask config files found in: {self.skills_dir}")
            print(
                "   Agent will run without pre-existing subtasks (will create new ones as needed).\n"
            )
            # Set empty config for backwards compatibility
            self.subtask_config = {}
            return

        print(f"Found {len(config_files)} subtask config file(s):")

        for config_file in config_files:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            subtasks = config.get('subtasks', [])
            if not isinstance(subtasks, list) or not subtasks:
                print(
                    f"  ⚠️  Skipping {config_file.name}: missing/empty 'subtasks'"
                )
                continue

            log_file = config.get('log_file')
            if not log_file:
                # Allow configs that embed actions directly in subtasks
                has_embedded_actions = any(
                    bool(st.get('actions'))
                    for st in subtasks
                    if isinstance(st, dict)
                )
                if not has_embedded_actions:
                    print(
                        f"  ⚠️  Skipping {config_file.name}: no 'log_file' and no embedded 'actions'"
                    )
                    continue

            print(
                f"  ✓ {config_file.name}: {len(subtasks)} subtask(s), log: {Path(log_file).name if log_file else '<embedded actions>'}"
            )

            self.subtask_configs.append((log_file, config))

        if not self.subtask_configs:
            print(
                "\n📝 No valid subtask configs loaded; continuing without subtasks.\n"
            )
            self.subtask_config = {}
            return

        print(
            f"\nTotal: {len(self.subtask_configs)} config(s) loaded with {sum(len(cfg.get('subtasks', [])) for _, cfg in self.subtask_configs)} subtask(s)"
        )

        # For backwards compatibility, store first config as main config
        # This allows existing code to use self.subtask_config
        self.subtask_config = (
            self.subtask_configs[0][1] if self.subtask_configs else {}
        )

    async def close(self) -> None:
        """Cleanup toolkit resources and close the browser.

        This closes the browser completely to ensure a fresh state for the next task.
        """
        if not self.toolkit:
            return

        try:
            # Close the browser completely
            await self.toolkit.browser_close()
            print("✓ Browser closed successfully")
        except Exception as e:
            print(f"⚠️  Browser close failed: {e}")

        try:
            await self.toolkit.disconnect_websocket()
        except AttributeError:
            pass  # Expected if browser already closed
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
        print("INITIALIZING SUBTASK AGENT")
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

        # Import ActionReplayer
        from action_replayer import ActionReplayer

        custom_tools = [
            "browser_open",
            "browser_close",
            "browser_visit_page",
            "browser_back",
            "browser_forward",
            "browser_click",
            "browser_type",
            "browser_select",
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
        # Initialize toolkit - launches its own browser (no CDP)
        # Browser language is set to English in browser-session.ts
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
            connect_over_cdp=False,  # Launch own browser instead of CDP
            default_start_url=None,
        )

        # Open browser - this starts a fresh browser instance
        await self.toolkit.browser_open()
        print("✓ Browser launched (language: English)")

        # Create subtask functions from all configs
        if self.enable_skills and self.subtask_configs:
            print("\n" + "=" * 80)
            print("CREATING SUBTASK FUNCTIONS")
            print("=" * 80)

            # Iterate through all loaded configs
            for log_file, config in self.subtask_configs:
                config_name = config.get('metadata', {}).get(
                    'subtask_type', 'unknown'
                )
                print(
                    f"\n📦 Processing config: {Path(log_file).name if log_file else '<embedded actions>'}"
                )
                print(f"   Type: {config_name}")

                # Save config to temp file for ActionReplayer
                # (ActionReplayer expects a file path, not a dict)
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False, encoding='utf-8'
                ) as temp_config:
                    json.dump(config, temp_config, indent=2, ensure_ascii=False)
                    temp_config_path = temp_config.name

                for subtask in config.get('subtasks', []):
                    subtask_id = subtask['id']
                    name = subtask['name']
                    description = subtask['description']
                    variables = subtask.get('variables', {})

                    # Skip if subtask already exists (first config wins)
                    if subtask_id in self.subtask_functions:
                        print(f"  ⚠️  Skipping duplicate subtask: {subtask_id}")
                        continue

                    if not log_file and not bool(subtask.get('actions', [])):
                        print(
                            f"  ⚠️  Subtask {subtask_id} has no log file and no embedded actions"
                        )
                        raise ValueError(
                            f"Subtask {subtask_id} has no log file and no embedded actions"
                        )

                    # Create replayer instance for this subtask
                    replayer = ActionReplayer(
                        log_file=log_file,
                        cdp_port=self.cdp_port,
                        subtask_config=temp_config_path,
                        subtask_id=subtask_id,
                        use_agent_recovery=self.use_agent_recovery,
                    )
                    # Share the same toolkit to avoid WebSocket conflicts
                    replayer.toolkit = self.toolkit

                    # Check if subtask has embedded actions
                    subtask_has_actions = bool(subtask.get('actions', []))

                    if subtask_has_actions:
                        # Initialize with empty list - will be populated by load_subtask_config()
                        replayer.actions = []
                        print(
                            f"  [Info] Subtask {subtask_id} has embedded actions, skipping log file load"
                        )
                    else:
                        # Load from log file for backward compatibility
                        replayer.actions = replayer.load_log_file()
                        print(
                            f"  [Info] Subtask {subtask_id} loading actions from log file"
                        )

                    # Create subtask function with stats tracker and session log dir
                    subtask_func = SubtaskFunction(
                        subtask_id=subtask_id,
                        name=name,
                        description=description,
                        variables=variables,
                        replayer=replayer,
                        stats_tracker=self.stats,
                        session_log_dir=self.session_log_dir,
                    )

                    self.subtask_functions[subtask_id] = subtask_func

                    if variables:
                        print(f"  ✓ Created function: {subtask_id}")
                        print(f"     Variables: {list(variables.keys())}")
                    else:
                        print(f"  ✓ Created function: {subtask_id}")
                        print("     No variables (fixed operation)")

            print(
                f"\n✅ Total subtask functions created: {len(self.subtask_functions)}"
            )
            print(f"   Type: {config_name}")

            # Save config to temp file for ActionReplayer
            # (ActionReplayer expects a file path, not a dict)
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=False, encoding='utf-8'
            ) as temp_config:
                json.dump(config, temp_config, indent=2, ensure_ascii=False)
                temp_config_path = temp_config.name

            for subtask in config.get('subtasks', []):
                subtask_id = subtask['id']
                name = subtask['name']
                description = subtask['description']
                variables = subtask.get('variables', {})

                # Skip if subtask already exists (first config wins)
                if subtask_id in self.subtask_functions:
                    print(f"  ⚠️  Skipping duplicate subtask: {subtask_id}")
                    continue

                if not log_file and not bool(subtask.get('actions', [])):
                    print(
                        f"  ⚠️  Subtask {subtask_id} has no log file and no embedded actions"
                    )
                    raise ValueError(
                        f"Subtask {subtask_id} has no log file and no embedded actions"
                    )

                # Create replayer instance for this subtask
                replayer = ActionReplayer(
                    log_file=log_file,
                    subtask_config=temp_config_path,
                    subtask_id=subtask_id,
                    use_agent_recovery=self.use_agent_recovery,
                )
                # Share the same toolkit to avoid WebSocket conflicts
                replayer.toolkit = self.toolkit

                # Check if subtask has embedded actions
                subtask_has_actions = bool(subtask.get('actions', []))

                if subtask_has_actions:
                    # Initialize with empty list - will be populated by load_subtask_config()
                    replayer.actions = []
                    print(
                        f"  [Info] Subtask {subtask_id} has embedded actions, skipping log file load"
                    )
                else:
                    # Load from log file for backward compatibility
                    replayer.actions = replayer.load_log_file()
                    print(
                        f"  [Info] Subtask {subtask_id} loading actions from log file"
                    )

                # Create subtask function with stats tracker and session log dir
                subtask_func = SubtaskFunction(
                    subtask_id=subtask_id,
                    name=name,
                    description=description,
                    variables=variables,
                    replayer=replayer,
                    stats_tracker=self.stats,
                    session_log_dir=self.session_log_dir,
                )

                self.subtask_functions[subtask_id] = subtask_func

                if variables:
                    print(f"  ✓ Created function: {subtask_id}")
                    print(f"     Variables: {list(variables.keys())}")
                else:
                    print(f"  ✓ Created function: {subtask_id}")
                    print("     No variables (fixed operation)")

        print(
            f"\n✅ Total subtask functions created: {len(self.subtask_functions)}"
        )

        # Create ChatAgent with both subtask functions and toolkit
        print("\n" + "=" * 80)
        print("CREATING CHAT AGENT")
        print("=" * 80)

        model = create_default_model()

        print("✓ Model created")

        # Get toolkit tools - use them directly
        # FunctionTool objects already have proper signatures
        browser_tools = self.toolkit.get_tools()
        print(f"✓ Got {len(browser_tools)} browser tools")

        # Note: We'll log browser tool calls through a different mechanism
        # to avoid breaking the function signatures that ChatAgent expects

        # Create subtask tool wrappers
        subtask_tools = []
        if self.enable_skills and self.subtask_functions:
            print("Creating subtask tool wrappers...")

            for subtask_id, subtask_func in self.subtask_functions.items():
                # Create wrapper with proper signature that logs calls
                if subtask_func.variables:
                    # Build parameter list for the function signature
                    param_list = []
                    param_docs = []
                    for var_name, var_config in subtask_func.variables.items():
                        param_list.append(f"{var_name}: str")
                        param_docs.append(
                            f"    {var_name} (str): {var_config['description']}"
                        )

                    # Build function signature and docstring
                    params_str = ", ".join(param_list)
                    params_doc = "\n".join(param_docs)

                    # Create function code dynamically with logging
                    func_code = f"""
async def subtask_{subtask_func.subtask_id}({params_str}):
    \"\"\"
    {subtask_func.description}

    Args:
{params_doc}

    Returns:
        str: JSON result containing status, message, and page snapshot
    \"\"\"
    import json

    # Log the call
    kwargs = {{{", ".join([f"'{var}': {var}" for var in subtask_func.variables.keys()])}}}

    call_log = {{
        'timestamp': get_timestamp_iso(),
        'type': 'subtask_call',
        'subtask_id': '{subtask_func.subtask_id}',
        'subtask_name': '{subtask_func.name}',
        'arguments': kwargs,
        'result': None
    }}

    result = await _sf.execute(**kwargs)
    call_log['result'] = result

    # Add to agent's communication log
    if hasattr(_agent, 'agent_communication_log'):
        _agent.agent_communication_log.append(call_log)

    return json.dumps(result, ensure_ascii=False)
"""
                else:
                    # No parameters - fixed operation
                    func_code = f"""
async def subtask_{subtask_func.subtask_id}():
    \"\"\"
    {subtask_func.description}. This is a fixed operation with no parameters.

    Returns:
        str: JSON result containing status, message, and page snapshot
    \"\"\"
    import json

    # Log the call
    call_log = {{
        'timestamp': get_timestamp_iso(),
        'type': 'subtask_call',
        'subtask_id': '{subtask_func.subtask_id}',
        'subtask_name': '{subtask_func.name}',
        'arguments': {{}},
        'result': None
    }}

    result = await _sf.execute()
    call_log['result'] = result

    # Add to agent's communication log
    if hasattr(_agent, 'agent_communication_log'):
        _agent.agent_communication_log.append(call_log)

    return json.dumps(result, ensure_ascii=False)
"""

                # Execute the code to create the function
                local_vars = {
                    "_sf": subtask_func,
                    "_agent": self,
                    "get_timestamp_iso": get_timestamp_iso,
                }
                exec(func_code, local_vars)
                wrapper = local_vars[f"subtask_{subtask_func.subtask_id}"]

                subtask_tools.append(wrapper)
                print(f"  ✓ Created wrapper for {subtask_id}: {wrapper.__name__}")

        # Combine all tools
        all_tools = [*browser_tools, *subtask_tools]
        if self.enable_skills and subtask_tools:
            print(
                f"✓ Total tools: {len(all_tools)} ({len(browser_tools)} browser + {len(subtask_tools)} subtask)"
            )
        else:
            print(
                f"✓ Total tools: {len(all_tools)} (browser tools only, skills disabled)"
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
            step_timeout_max_retries=self.step_timeout_max_retries,
            tool_execution_timeout=self.tool_execution_timeout,
            enable_snapshot_clean=False,
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

        # Subtask tools
        for tool in subtask_tools:
            tool_info = {
                'type': 'subtask_function',
                'name': tool.__name__,
                'docstring': tool.__doc__,
            }
            self.tool_definitions.append(tool_info)

        return True

    def get_system_message(self) -> str:
        """Get the system message for the agent."""
        # Check if there are any subtask functions available
        has_subtasks = bool(self.subtask_functions)

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
                "4b. For dropdown/combobox interactions: use browser_select(ref=..., value=...).",
                "   - Do NOT repeatedly click a combobox hoping an option will be selected.",
                "   - If the options you need are visible in the snapshot but have no [ref=...], you cannot click them directly; use browser_select.",
                "5. Do NOT give a final answer unless a page snapshot clearly contains the requested information.",
                "   - If the result is still loading or missing, try other pages.",
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

        if has_subtasks:
            # Generate subtask list
            subtask_list = "\n".join(
                [
                    f"- subtask_{sid}: {sf.description}"
                    + (
                        f" (variables: {list(sf.variables.keys())})"
                        if sf.variables
                        else " (no parameters)"
                    )
                    for sid, sf in self.subtask_functions.items()
                ]
            )
            # Agent with subtasks
            prompt_parts.extend(
                [
                    "AVAILABLE SUBTASK FUNCTIONS (PREFER THESE WHEN APPLICABLE):",
                    subtask_list,
                    "",
                    "GUIDELINES:",
                    "1. **Prefer subtask functions** when they match your goal - they are tested and reliable",
                    "2. **IMPORTANT: Only call subtasks that match the current page URL**",
                    "   - Each subtask has an 'Execution page' specified in its description",
                    "   - Before calling a subtask, verify you are on the correct page using browser_get_page_snapshot",
                    "   - Do not call subtasks designed for different pages (e.g., don't call a subtask for Google Flights when on Google Search)",
                    "3. Use low-level browser tools only under the following conditions:",
                    "   - No suitable high-level subtask function is available.",
                    "   - Fine-grained, manual control of page interactions is required.",
                    "   - A subtask function has failed and manual recovery is necessary.",
                    "   Tool usage constraints:"
                    "   - Do not call browser_get_page_snapshot consecutively! Consecutive calls are redundant because the page state does not change without an intervening action.",
                    "   - Minimize browser_get_page_snapshot calls, as they are token-expensive and should only be used when the page state is expected to change, or you need to get the current state.",
                    "",
                    "4. After executing a subtask function, you will receive:",
                    "   - Status (success/error)",
                    "   - Message describing the result",
                    "   - Current page browser_get_page_snapshot",
                    "   - Variables that were used",
                    "",
                    "5. If a subtask fails, you can either:",
                    "   - Retry with different variables",
                    "   - Use low-level browser tools to fix the issue",
                    "   - Ask for clarification",
                    "   - If a subtask fails repeatedly, consider using browser tools to manually achieve the goal or use alternative subtasks.",
                    "",
                    "Remember: Subtask functions are your first choice - they encapsulate complex multi-step operations!",
                    "If you find some subtask may not finished by reusing previous subtask, you need to do it by yourself!",
                    "",
                ]
            )
        else:
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

    @observe()
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

        # Load all subtask replay action logs from session directory
        replay_log_files = []
        if self.session_log_dir and self.session_log_dir.exists():
            replay_log_files = sorted(
                self.session_log_dir.glob("subtask_*_replay_actions.json")
            )
            print(
                f"\n📂 Reading replay logs from session directory: {self.session_log_dir}"
            )
        else:
            # Fallback to browser_log directory
            replay_log_files = sorted(
                browser_log_dir.glob("subtask_replay_actions_*.json")
            )
            print("\n📂 Reading replay logs from browser_log directory")

        print(f"   Found {len(replay_log_files)} subtask replay log files")

        all_replay_actions = []
        for replay_log_file in replay_log_files:
            try:
                with open(replay_log_file, 'r', encoding='utf-8') as f:
                    replay_data = json.load(f)
                    actions = replay_data.get('actions', [])
                    all_replay_actions.extend(actions)
                    print(
                        f"   • {replay_log_file.name}: {len(actions)} actions"
                    )
            except Exception as e:
                print(f"   ⚠️  Error reading {replay_log_file.name}: {e}")

        print(f"\n   Total replay actions: {len(all_replay_actions)}")

        # Filter out replay actions from browser log
        # Strategy: Create a set of (timestamp, action) pairs from replay logs
        # and exclude browser actions that match
        replay_signatures = set()
        for replay_action in all_replay_actions:
            timestamp = replay_action.get('timestamp', '')
            action_name = replay_action.get('action', '')
            if timestamp and action_name:
                # Use timestamp (to second precision) + action name as signature
                # This is a simple heuristic; actions within the same second with same name are considered duplicates
                ts_seconds = timestamp[:19]  # Keep only YYYY-MM-DDTHH:MM:SS
                replay_signatures.add((ts_seconds, action_name))

        print(
            f"   Created {len(replay_signatures)} replay action signatures for filtering"
        )

        # Filter browser actions
        agent_initiated_actions = []

        for action in all_browser_actions:
            action_timestamp = action.get('timestamp', '')
            action_name = action.get('action', '')

            if not action_timestamp:
                continue

            # Check if this action matches a replay action
            ts_seconds = action_timestamp[:19]
            action_signature = (ts_seconds, action_name)

            if action_signature in replay_signatures:
                # This is a replay action, skip it
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

        print(f"\n🎯 Subtask Calls: {self.stats['subtask_calls']}")
        if self.stats['subtask_details']:
            for subtask_id, details in self.stats['subtask_details'].items():
                print(
                    f"   • {details['name']} ({subtask_id}): {details['calls']} call(s)"
                )
                for i, vars_used in enumerate(details['variables_used'], 1):
                    if vars_used:
                        print(f"      Call {i}: {vars_used}")
                    else:
                        print(f"      Call {i}: (no variables)")

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

        print(
            f"\n🤖 Agent Recovery Calls: {self.stats['agent_recovery_calls']}"
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
        print("   Recovery Agent:")
        print(
            f"      • Prompt: {self.stats['token_details']['recovery_agent']['prompt']} tokens"
        )
        print(
            f"      • Completion: {self.stats['token_details']['recovery_agent']['completion']} tokens"
        )
        print(
            f"      • Total: {self.stats['token_details']['recovery_agent']['total']} tokens"
        )

        print("\n" + "=" * 80)

    def save_communication_log(self):
        """Save all agent communications to a JSON file."""
        # Extract browser tool calls from browser log file
        browser_tool_calls_from_log = self._extract_agent_browser_calls()

        # Collect all recovery agent communications from replayers
        recovery_communications = []
        for subtask_id, subtask_func in self.subtask_functions.items():
            if hasattr(subtask_func.replayer, 'recovery_history'):
                for record in subtask_func.replayer.recovery_history:
                    recovery_communications.append(
                        {
                            'type': 'recovery_agent_call',
                            'subtask_id': subtask_id,
                            **record,
                        }
                    )

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
            'recovery_agent_communications': recovery_communications,
            'statistics': self.stats,
            'summary': {
                'total_communications': len(sorted_communications),
                'subtask_calls': len(
                    [
                        c
                        for c in sorted_communications
                        if c.get('type') == 'subtask_call'
                    ]
                ),
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
                'recovery_calls': len(recovery_communications),
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
            f"   - Subtask calls: {all_communications['summary']['subtask_calls']}"
        )
        print(
            f"   - Browser tool calls: {all_communications['summary']['browser_tool_calls']}"
        )
        print(
            f"   - Recovery calls: {all_communications['summary']['recovery_calls']}"
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

        # Add the toolkits directory to path if needed
        toolkits_dir = Path(__file__).parent
        if str(toolkits_dir) not in sys.path:
            sys.path.insert(0, str(toolkits_dir))

        from analyze_session import analyze_session

        print(f"\n🔍 Analyzing session: {self.session_log_dir}")

        try:
            analyze_session(str(self.session_log_dir))
            print("\n✅ Timeline analysis completed successfully!")
        except Exception as e:
            print(f"\n⚠️  Error during timeline analysis: {e}")
            traceback.print_exc()

    def save_memory(self, path: Path | str | None = None):
        """Save agent memory to a file (if applicable)."""
        if not path:
            path = self.session_log_dir / "agent_memory.json"
        self.agent.save_memory(path)


__all__ = ["SkillsAgent", "SubtaskFunction"]
