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
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from playwright.async_api import Page

# Logging support
from camel.logger import get_logger

logger = get_logger(__name__)


class PageSnapshot:
    """Utility for capturing YAML-like page snapshots and diff-only
    variants."""

    MAX_TIMEOUT_MS = 5000  # wait_for_load_state timeout

    def __init__(self, page: "Page"):
        self.page = page
        self.snapshot_data: Optional[str] = None  # last full snapshot
        self._last_url: Optional[str] = None
        self.last_info: Dict[str, List[int] | bool] = {
            "is_diff": False,
            "priorities": [1, 2, 3],
        }

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def capture(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        """Return current snapshot or just the diff to previous one."""
        try:
            current_url = self.page.url

            # Serve cached copy (unless diff requested)
            if (
                not force_refresh
                and current_url == self._last_url
                and self.snapshot_data
                and not diff_only
            ):
                return self.snapshot_data

            # ensure DOM stability
            await self.page.wait_for_load_state(
                'domcontentloaded', timeout=self.MAX_TIMEOUT_MS
            )

            logger.debug("Capturing page snapshot …")
            snapshot_text = await self._get_snapshot_direct()
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

    async def _get_snapshot_direct(self) -> Optional[str]:
        try:
            if PageSnapshot._snapshot_js_cache is None:
                js_path = Path(__file__).parent / "snapshot.js"
                PageSnapshot._snapshot_js_cache = js_path.read_text(
                    encoding="utf-8"
                )
            return await self.page.evaluate(PageSnapshot._snapshot_js_cache)
        except Exception as e:
            logger.warning("Failed to execute snapshot JavaScript: %s", e)
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
