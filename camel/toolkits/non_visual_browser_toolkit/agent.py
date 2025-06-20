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
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType

from .actions import ActionExecutor
from .nv_browser_session import NVBrowserSession

if TYPE_CHECKING:
    from camel.agents import ChatAgent

logger = logging.getLogger(__name__)


class PlaywrightLLMAgent:
    """High-level orchestration: snapshot ↔ LLM ↔ action executor."""

    # System prompt as class constant to avoid recreation
    SYSTEM_PROMPT = """
You are a web automation assistant.

" Analyse the page snapshot and create a short high-level plan, "
"then output the FIRST action to start with.\n\n"
"Return a JSON object in *exactly* this shape:\n"
"Action format json_object examples:\n"
"{\n  \"plan\": [\"Step 1\", \"Step 2\"],\n  \"action\": {\n    \"type\": 
\"click\",\n    \"ref\": \"e1\"\n  }\n}\n\n"
"If task is already complete:\n"
"{\n  \"plan\": [],\n  \"action\": {\n    \"type\": \"finish\",
\n    \"ref\": null,\n    \"summary\": \"Task was already completed. Summary 
of what was found...\"\n  }\n}"

Available action types:
- 'click': {"type": "click", "ref": "e1"} or {"type": "click", "text": 
"Button Text"} or {"type": "click", "selector": "button"}
- 'type': {"type": "type", "ref": "e1", "text": "search text"} or {"type": 
"type", "selector": "input", "text": "search text"}
- 'select': {"type": "select", "ref": "e1", "value": "option"} or {"type": 
"select", "selector": "select", "value": "option"}
- 'wait': {"type": "wait", "timeout": 2000} or {"type": "wait", "selector": 
"#element"}
- 'scroll': {"type": "scroll", "direction": "down", "amount": 300}
- 'enter': {"type": "enter", "ref": "e1"} or {"type": "enter", "selector": 
"input[name=q]"} or {"type": "enter"}
- 'navigate': {"type": "navigate", "url": "https://example.com"}
- 'finish': {"type": "finish", "ref": null, "summary": "task completion 
summary"}

IMPORTANT: 
- For 'click': Use 'ref' from snapshot, or 'text' for visible text, 
or 'selector' for CSS selectors
- For 'type'/'select': Use 'ref' from snapshot or 'selector' for CSS selectors
- Only use 'ref' values that exist in the snapshot (e.g., ref=e1, ref=e2, etc.)
- Use 'finish' when the task is completed successfully with a summary of 
what was accomplished
- Use 'enter' to press the Enter key (optionally focus an element first)
- Use 'navigate' to open a new URL before interacting further
- click can choose radio, checkbox...
        """

    def __init__(
        self,
        *,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
        model_backend: Optional[BaseModelBackend] = None,
    ):
        self._session = NVBrowserSession(
            headless=headless, user_data_dir=user_data_dir
        )
        from camel.agents import ChatAgent

        # Populated lazily after first page load
        self.action_history: List[Dict[str, Any]] = []
        if model_backend is None:
            model_backend = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                model_config_dict={"temperature": 0, "top_p": 1},
            )
        self.model_backend = model_backend
        # Reuse ChatAgent instance to avoid recreation overhead
        self._chat_agent: Optional[ChatAgent] = None

    async def navigate(self, url: str) -> str:
        try:
            # NVBrowserSession handles waits internally
            logger.debug("Navigated to URL: %s", url)
            await self._session.visit(url)
            return await self._session.get_snapshot(force_refresh=True)
        except Exception as exc:
            return f"Error: could not navigate - {exc}"

    def _get_chat_agent(self) -> "ChatAgent":
        """Get or create the ChatAgent instance."""
        from camel.agents import ChatAgent

        if self._chat_agent is None:
            self._chat_agent = ChatAgent(
                system_message=self.SYSTEM_PROMPT, model=self.model_backend
            )
        return self._chat_agent

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        r"""Safely parse JSON from LLM response with multiple fallback
        strategies.
        """
        # First attempt: direct parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Second attempt: extract JSON-like block using regex
        # Look for content between outermost braces
        json_pattern = re.compile(
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL
        )
        json_matches = json_pattern.findall(content)

        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Third attempt: try to find and parse line by line
        lines = content.split('\n')
        json_lines = []
        in_json = False

        for line in lines:
            line = line.strip()
            if line.startswith('{'):
                in_json = True
                json_lines = [line]
            elif in_json:
                json_lines.append(line)
                if line.endswith('}'):
                    try:
                        json_text = '\n'.join(json_lines)
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        pass
                    in_json = False
                    json_lines = []

        # Fallback: return default structure
        logger.warning(
            "Could not parse JSON from LLM response: %s", content[:200]
        )
        return {
            "plan": ["Could not parse response"],
            "action": {
                "type": "finish",
                "ref": None,
                "summary": "Parsing error",
            },
        }

    def _llm_call(
        self,
        prompt: str,
        snapshot: str,
        is_initial: bool,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Call the LLM (via CAMEL ChatAgent) to get plan & next action."""
        # Build user message
        if is_initial:
            user_content = f"Snapshot:\n{snapshot}\n\nTask: {prompt}"
        else:
            hist_lines = [
                (
                    f"{i + 1}. {'✅' if h['success'] else '❌'} "
                    f"{h['action']['type']} -> {h['result']}"
                )
                for i, h in enumerate(history or [])
            ]
            user_content = (
                f"Snapshot:\n{snapshot}\n\nHistory:\n"
                + "\n".join(hist_lines)
                + f"\n\nTask: {prompt}"
            )

        # Run ChatAgent
        chat_agent = self._get_chat_agent()
        response = chat_agent.step(user_content)
        content = response.msgs[0].content if response.msgs else "{}"

        # Safely parse JSON response
        return self._safe_parse_json(content)

    async def process_command(self, prompt: str, max_steps: int = 15):
        # initial full snapshot
        full_snapshot = await self._session.get_snapshot()
        assert self._session.snapshot is not None
        meta = self._session.snapshot.last_info
        logger.info("Initial snapshot priorities=%s", meta["priorities"])
        logger.debug("Full snapshot:\n%s", full_snapshot)

        plan_resp = self._llm_call(
            prompt, full_snapshot or "", is_initial=True
        )
        plan = plan_resp.get("plan", [])
        action = plan_resp.get("action")

        logger.info("Plan generated: %s", json.dumps(plan, ensure_ascii=False))

        steps = 0
        while action and steps < max_steps:
            if action.get("type") == "finish":
                logger.info("Task finished: %s", action.get("summary", "Done"))
                break

            result = await self._run_action(action)
            logger.debug("Executed action: %s | Result: %s", action, result)

            self.action_history.append(
                {
                    "action": action,
                    "result": result,
                    "success": "Error" not in result,
                }
            )

            diff_snapshot = await self._session.get_snapshot(
                force_refresh=ActionExecutor.should_update_snapshot(action),
                diff_only=True,
            )
            assert self._session.snapshot is not None
            meta = self._session.snapshot.last_info
            logger.debug(
                "Snapshot after action (diff=%s):\n%s",
                meta["is_diff"],
                diff_snapshot,
            )

            # Update full snapshot if page changed
            if meta["is_diff"] and not diff_snapshot.startswith(
                "- Page Snapshot (no structural changes)"
            ):
                assert self._session.snapshot is not None
                full_snapshot = self._session.snapshot.snapshot_data or ""

            action = self._llm_call(
                prompt,
                full_snapshot or "",
                is_initial=False,
                history=self.action_history,
            ).get("action")
            steps += 1

        logger.info("Process completed with %d steps", steps)

    async def _run_action(self, action: Dict[str, Any]) -> str:
        if action.get("type") == "navigate":
            return await self.navigate(action.get("url", ""))
        return await self._session.exec_action(action)

    async def close(self):
        await self._session.close()
