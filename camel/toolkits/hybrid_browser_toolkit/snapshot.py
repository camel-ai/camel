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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from playwright.async_api import Page

# Logging support
from camel.logger import get_logger

from .config_loader import ConfigLoader

logger = get_logger(__name__)


class PageSnapshot:
    """Utility for capturing YAML-like page snapshots and diff-only
    variants."""

    def __init__(self, page: "Page"):
        self.page = page
        self.snapshot_data: Optional[str] = None  # last full snapshot
        self._last_url: Optional[str] = None
        self.last_info: Dict[str, List[int] | bool] = {
            "is_diff": False,
            "priorities": [1, 2, 3],
        }
        self.dom_timeout = ConfigLoader.get_dom_content_loaded_timeout()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def capture(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        """Return current snapshot or just the diff to previous one."""
        try:
            current_url = self.page.url

            # Previously we skipped regeneration when the URL had not changed
            # and no explicit refresh was requested. This prevented the agent
            # from seeing DOM updates that occur without a navigation (e.g.
            # single-page apps, dynamic games such as Wordle). The early-exit
            # logic has been removed so that we always capture a *fresh* DOM
            # snapshot.  If the snapshot happens to be byte-for-byte identical
            # to the previous one we simply return it after the standard
            # comparison step below; otherwise callers receive the updated
            # snapshot even when the URL did not change.

            # ensure DOM stability
            await self.page.wait_for_load_state(
                'domcontentloaded', timeout=self.dom_timeout
            )

            logger.debug("Capturing page snapshot …")
            snapshot_result = await self._get_snapshot_direct()

            # Extract snapshot text from the unified analyzer result
            if (
                isinstance(snapshot_result, dict)
                and 'snapshotText' in snapshot_result
            ):
                snapshot_text = snapshot_result['snapshotText']
            else:
                snapshot_text = snapshot_result

            formatted = self._format_snapshot(snapshot_text or "<empty>")

            output = formatted
            if diff_only and self.snapshot_data:
                output = self._compute_diff(self.snapshot_data, formatted)

            # update cache with *full* snapshot (not diff)
            self._last_url = current_url
            self.snapshot_data = formatted

            # analyse priorities present (only for non-diff)
            priorities_included = self._detect_priorities(
                formatted if not diff_only else self.snapshot_data or formatted
            )
            self.last_info = {
                "is_diff": diff_only and self.snapshot_data is not None,
                "priorities": priorities_included,
            }

            logger.debug(
                "Snapshot captured. Diff_only=%s, priorities=%s",
                diff_only,
                self.last_info["priorities"],
            )
            return output
        except Exception as exc:
            logger.error("Snapshot capture failed: %s", exc)
            return f"Error: Could not capture page snapshot {exc}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    _snapshot_js_cache: Optional[str] = None  # class-level cache

    async def _get_snapshot_direct(
        self,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        r"""Evaluate the snapshot-extraction JS with simple retry logic.

        Playwright throws *Execution context was destroyed* when a new page
        navigation happens between scheduling and evaluating the JS. In that
        case we retry a few times after waiting for the next DOMContentLoaded
        event; for all other exceptions we abort immediately.
        """

        # Load JS once and cache it at class level
        if PageSnapshot._snapshot_js_cache is None:
            js_path = Path(__file__).parent / "unified_analyzer.js"
            PageSnapshot._snapshot_js_cache = js_path.read_text(
                encoding="utf-8"
            )

        js_code = PageSnapshot._snapshot_js_cache

        retries: int = 3
        while retries > 0:
            try:
                return await self.page.evaluate(js_code)
            except Exception as e:
                msg = str(e)

                # Typical error when navigation happens between calls
                nav_err = "Execution context was destroyed"

                if (
                    nav_err in msg
                    or "Most likely because of a navigation" in msg
                ):
                    retries -= 1
                    logger.debug(
                        "Snapshot evaluate failed due to navigation; "
                        "retrying (%d left)…",
                        retries,
                    )

                    # Wait for next DOM stability before retrying
                    try:
                        await self.page.wait_for_load_state(
                            "domcontentloaded", timeout=self.dom_timeout
                        )
                    except Exception:
                        # Even if waiting fails, attempt retry to give it
                        # one more chance
                        pass

                    continue  # retry the evaluate()

                # Any other exception → abort
                logger.warning(
                    "Failed to execute snapshot JavaScript: %s",
                    e,
                )
                return None

        logger.warning("Failed to execute snapshot JavaScript after retries")
        return None

    @staticmethod
    def _format_snapshot(text: str) -> str:
        return "\n".join(["- Page Snapshot", "```yaml", text, "```"])

    @staticmethod
    def _compute_diff(old: str, new: str) -> str:
        if not old or not new:
            return "- Page Snapshot (error: missing data for diff)"

        import difflib

        diff = list(
            difflib.unified_diff(
                old.splitlines(False),
                new.splitlines(False),
                fromfile='prev',
                tofile='curr',
                lineterm='',
            )
        )
        if not diff:
            return "- Page Snapshot (no structural changes)"
        return "\n".join(["- Page Snapshot (diff)", "```diff", *diff, "```"])

    # ------------------------------------------------------------------
    def _detect_priorities(self, snapshot_yaml: str) -> List[int]:
        """Return sorted list of priorities present (1,2,3)."""
        priorities = set()
        for line in snapshot_yaml.splitlines():
            if '[ref=' not in line:
                continue
            lower_line = line.lower()
            if any(
                r in lower_line
                for r in (
                    "input",
                    "button",
                    "select",
                    "textarea",
                    "checkbox",
                    "radio",
                    "link",
                )
            ):
                priorities.add(1)
            elif 'label' in lower_line:
                priorities.add(2)
            else:
                priorities.add(3)
        if not priorities:
            priorities.add(3)
        return sorted(priorities)
