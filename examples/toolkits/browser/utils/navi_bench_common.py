# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License i s distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
"""Common Navi-Bench runner utilities for browser agents and skills agents."""
from dataclasses import dataclass
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from camel.evaluators.webjudge import (
    WebJudgeVisionConfig,
    WebJudgeVisionEvaluator,
    WebJudgeEvaluationResult,
)


@dataclass
class AttemptResult:
    task_id: str
    domain: str
    website: str
    attempt: int
    success: bool
    score: Optional[float]
    eval_result_path: Optional[str]
    session_dir: Optional[str]
    error: Optional[str] = None
    suggestions: str = ""


class WebJudgeTaskVerifier:
    """WebJudge-based verifier using session evidence (vision-only)."""

    def __init__(
        self,
        *,
        model_platform,
        model_type,
        vision_config: WebJudgeVisionConfig | None = None,
    ):
        resolved_config = vision_config or WebJudgeVisionConfig(
            model_platform=model_platform,
            model_type=model_type,
        )
        self.vision_evaluator = WebJudgeVisionEvaluator(config=resolved_config)

    def verify_task(
        self,
        task_description: str,
        agent_response: str,
        *,
        session_dir: Path | None = None,
        website: str | None = None,
    ):
        """Verify task completion using WebJudge.
        
        Returns:
            WebJudgeEvaluationResult dataclass with success, reasoning, suggestions,
            execution_time, token_usage, etc.
        """
        if session_dir is None:
            return WebJudgeEvaluationResult(
                success=False,
                reasoning="WebJudge verifier requires session_dir evidence",
                suggestions="Re-run with session logging enabled and pass session_dir to the verifier.",
                debug_path="",
            )
        return self.vision_evaluator.evaluate_session(
            task=task_description,
            session_dir=session_dir,
            agent_response=agent_response,
            website=website,
        )


# === Safe Name ===
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")

def safe_name(value: str) -> str:
    value = (value or "").strip()
    value = _SAFE_NAME_RE.sub("_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"

# === Pydantic Dump ===
def pydantic_dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    return obj

# === Score Extraction ===
def score_from_result(result: Any) -> Optional[float]:
    score = getattr(result, "score", None)
    if isinstance(score, (int, float)):
        return float(score)
    if isinstance(result, dict):
        raw = result.get("score")
        if isinstance(raw, (int, float)):
            return float(raw)
    return None

# === Token Usage Extraction ===
def extract_token_usage_from_payload(payload: Any) -> Optional[Dict[str, Any]]:
    def _merge(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
        for k, v in src.items():
            if k not in dst:
                dst[k] = v
    def _walk(obj: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if obj is None:
            return out
        if isinstance(obj, dict):
            usage = obj.get("usage")
            if isinstance(usage, dict):
                _merge(out, usage)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if isinstance(obj.get(k), (int, float)):
                    out[k] = obj.get(k)
            for k in ("input_tokens", "output_tokens"):
                if isinstance(obj.get(k), (int, float)):
                    out[k] = obj.get(k)
            for v in obj.values():
                _merge(out, _walk(v))
            return out
        if isinstance(obj, (list, tuple)):
            for v in obj:
                _merge(out, _walk(v))
            return out
        return out
    extracted = _walk(payload)
    return extracted or None

# === Website Key Normalization ===
def normalize_website_key(website: str) -> str:
    return " ".join((website or "").strip().lower().split())

# === Domain to Website Mapping ===
def domain_to_website(domain: str) -> str:
    d = (domain or "").strip().lower()
    mapping = {
        "google_flights": "Google Flights",
        "opentable": "OpenTable",
        "craigslist": "Craigslist",
        "resy": "Resy",
        "apartments": "Apartments.com",
    }
    return mapping.get(d, (domain or "").strip() or "Unknown")

# === Dataset Loader ===
def load_dataset_items_from_jsonl(jsonl_path: Path) -> List[Any]:
    from navi_bench.base import DatasetItem
    rows: List[Any] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            try:
                rows.append(DatasetItem.model_validate(raw))
            except Exception as e:
                raise ValueError(
                    f"Invalid DatasetItem at {jsonl_path}:{line_no}: "
                    f"{type(e).__name__}: {e}"
                ) from e
    return rows

# === Dataset Item Selector ===
def select_items(
    items: List[Any],
    *,
    domain_filter: str = "",
    task_id: str = "",
    start: int = 0,
    max_tasks: Optional[int] = None,
) -> List[Any]:
    selected = items
    if task_id.strip():
        wanted = task_id.strip()
        selected = [it for it in selected if it.task_id == wanted]
        return selected
    if domain_filter.strip():
        wanted = domain_filter.strip().lower()
        selected = [
            it for it in selected if (it.domain or "").lower() == wanted
        ]
    if start > 0:
        selected = selected[start:]
    if max_tasks is not None:
        selected = selected[: max(0, int(max_tasks))]
    return selected
