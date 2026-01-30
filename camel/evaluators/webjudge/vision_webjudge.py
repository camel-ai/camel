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

import base64
import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Literal

from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage

from .session_utils import (
    get_url_before_after,
    parse_json_objects_log,
    truncate_middle,
    clean_lines,
)

if TYPE_CHECKING:
    from camel.agents import ChatAgent


@dataclass(frozen=True)
class WebJudgeStageError(Exception):
    stage: str
    prompt: str
    response: str
    parse_error: str

    def __str__(self) -> str:
        return f"{self.stage} stage JSON parse failed: {self.parse_error}"


@dataclass(frozen=True)
class VisionEvidenceFrame:
    frame_id: str
    action_step: int
    timestamp: str
    action: str
    url_before: Optional[str]
    url_after: Optional[str]
    screenshot_path: str
    snapshot_path: Optional[str] = None


@dataclass
class WebJudgeVisionConfig:
    """ Configuration for Vision-WebJudge evaluator.
    Args:
        vision_type: Type of vision input, either 'image' or 'dom'.
            image will use screenshots, dom will use DOM snapshots.
    """
    model_platform: ModelPlatformType = ModelPlatformType.AZURE
    model_type: ModelType = ModelType.GPT_4_1
    vision_type: Literal["image", "dom"] = "dom"
    step_timeout: Optional[float] = 360.0
    tool_execution_timeout: Optional[float] = 360.0
    max_frames: int = 10_000
    action_history_max_chars: int = 4000
    evidence_score_threshold: int = 3
    evidence_top_k: int = 4
    min_images_for_outcome: int = 3
    max_images_for_outcome: int = 16
    include_raw: bool = False

    def __post_init__(self) -> None:
        self.max_frames = max(1, int(self.max_frames))
        self.action_history_max_chars = max(
            512, int(self.action_history_max_chars)
        )
        self.evidence_score_threshold = int(self.evidence_score_threshold)
        self.evidence_top_k = max(1, int(self.evidence_top_k))
        self.min_images_for_outcome = max(
            1, int(self.min_images_for_outcome)
        )
        self.max_images_for_outcome = max(1, int(self.max_images_for_outcome))
        self.max_images_for_outcome = max(
            self.max_images_for_outcome, self.min_images_for_outcome
        )
        if self.step_timeout is not None:
            self.step_timeout = float(self.step_timeout)
        if self.tool_execution_timeout is not None:
            self.tool_execution_timeout = float(self.tool_execution_timeout)


class WebJudgeVisionEvaluator:
    r"""Vision-WebJudge for `browser_skills_example` sessions.

    This consumes stable pre-capture screenshots stored under
    `session_dir/evidence/` and indexed from `complete_browser_log.log`
    via `pre_capture_screenshot_path`.

    Note: This evaluator is intentionally aligned with the original
    Online-Mind2Web WebJudge prompting style (natural language outputs and
    string-based parsing), rather than strict JSON-only judge steps.
    """

    def __init__(self, config: Optional[WebJudgeVisionConfig] = None):
        self.config = config or WebJudgeVisionConfig()
        from camel.models import ModelFactory

        self._model = ModelFactory.create(
            model_platform=self.config.model_platform,
            model_type=self.config.model_type,
            model_config_dict={
                "temperature": 0.0,
                "parallel_tool_calls": False},
        )

    def evaluate_session(
        self,
        *,
        task: str,
        session_dir: Path,
        agent_response: str = "",
        website: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_dir = Path(session_dir).expanduser().resolve()
        debug_path = session_dir / "webjudge_debug.json"
        debug_payload: Dict[str, Any] = {
            "generated_at": datetime.datetime.now().isoformat(),
            "evaluator": "WebJudgeVisionEvaluator",
            "session_dir": str(session_dir),
            "inputs": {
                "task": task,
                "website": website,
                "agent_response": agent_response,
            },
            "stages": {},
        }
        try:
            artifacts = self._load_session_artifacts(session_dir)
            candidates: List[VisionEvidenceFrame] = artifacts["candidates"]
            action_history: str = artifacts["action_history"]
            debug_payload["artifacts"] = {
                "action_history": action_history,
                "candidate_frames": [
                    {
                        "frame_id": f.frame_id,
                        "action_step": f.action_step,
                        "timestamp": f.timestamp,
                        "action": f.action,
                        "url_before": f.url_before,
                        "url_after": f.url_after,
                        "screenshot_path": f.screenshot_path,
                        "snapshot_path": f.snapshot_path,
                    }
                    for f in candidates
                ],
            }

            if not candidates:
                result = {
                    "success": False,
                    "reasoning": "No screenshot evidence found in session logs.",
                    "suggestions": "Enable pre-capture evidence (session_dir/evidence) and re-run.",
                    "debug_path": str(debug_path),
                }
                debug_payload["result"] = result
                self._try_write_debug_json(debug_path, debug_payload)
                return result

            raw: Dict[str, Any] = {}

            key_points, key_points_text, raw_kp = self._identify_key_points(
                task
            )
            debug_payload["stages"]["key_points"] = raw_kp
            if self.config.include_raw:
                raw["key_points"] = raw_kp

            candidates = self._select_candidate_subset(candidates)
            debug_payload["artifacts"]["candidate_subset"] = [
                f.frame_id for f in candidates
            ]
            scores, score_thoughts, raw_scores = self._score_evidence(
                task, key_points_text, candidates
            )
            debug_payload["stages"]["evidence_scoring"] = raw_scores
            debug_payload["artifacts"]["evidence_scoring_compact"] = [
                {
                    "evidence_no": pf.get("evidence_no"),
                    "frame_id": pf.get("frame_id"),
                    "parsed_score": (
                        (pf.get("parsed") or {}).get("score")
                        if isinstance(pf.get("parsed"), dict)
                        else None
                    ),
                    "response": pf.get("response", ""),
                }
                for pf in (raw_scores.get("per_frame") or [])
                if isinstance(pf, dict)
            ]
            debug_payload["artifacts"]["evidence_scores"] = scores
            debug_payload["artifacts"]["evidence_thoughts"] = score_thoughts
            if self.config.include_raw:
                raw["evidence_scoring"] = raw_scores

            selected, selected_meta = self._select_evidence(candidates, scores)
            debug_payload["artifacts"]["selected_evidence"] = [
                f.frame_id for f in selected
            ]
            debug_payload["artifacts"]["selected_evidence_meta"] = selected_meta
            selected_thoughts = [
                {
                    "frame_id": f.frame_id,
                    "score": scores.get(f.frame_id),
                    "reasoning": score_thoughts.get(f.frame_id, ""),
                }
                for f in selected
            ]
            debug_payload["artifacts"]["selected_evidence_thoughts"] = (
                selected_thoughts
            )

            verdict, raw_verdict = self._judge_outcome(
                task=task,
                action_history=action_history,
                key_points_text=key_points_text,
                evidence=selected,
                evidence_thoughts=selected_thoughts,
            )
            debug_payload["stages"]["outcome"] = raw_verdict
            if self.config.include_raw:
                raw["outcome"] = raw_verdict

            result = {
                "success": bool(verdict.get("success", False)),
                "reasoning": str(verdict.get("reasoning", "")),
                "suggestions": str(verdict.get("suggestions", "")),
                "key_points": key_points,
                "evidence": [
                    {
                        "frame_id": f.frame_id,
                        "action_step": f.action_step,
                        "timestamp": f.timestamp,
                        "action": f.action,
                        "url_before": f.url_before,
                        "url_after": f.url_after,
                        "screenshot_path": f.screenshot_path,
                        "snapshot_path": f.snapshot_path,
                        "score": scores.get(f.frame_id),
                    }
                    for f in selected
                ],
                # Rich outcome details (when provided by the judge model).
                "key_point_checks": verdict.get("key_point_checks", []),
                "frame_descriptions": verdict.get("frame_descriptions", []),
                "debug_path": str(debug_path),
            }
            if self.config.include_raw:
                result["raw"] = raw
            debug_payload["result"] = result
            self._try_write_debug_json(debug_path, debug_payload)
            return result
        except WebJudgeStageError as e:
            debug_payload["stages"][e.stage] = {
                "prompt": e.prompt,
                "response": e.response,
                "parse_error": e.parse_error,
            }
            result = {
                "success": False,
                "reasoning": f"Vision-WebJudge evaluation failed: {e!s}",
                "suggestions": "Check session_dir evidence and retry.",
                "debug_path": str(debug_path),
            }
            debug_payload["error"] = {
                "type": type(e).__name__,
                "message": str(e),
            }
            debug_payload["result"] = result
            self._try_write_debug_json(debug_path, debug_payload)
            return result
        except Exception as e:
            result = {
                "success": False,
                "reasoning": f"Vision-WebJudge evaluation failed: {e!s}",
                "suggestions": "Check session_dir evidence and retry.",
                "debug_path": str(debug_path),
            }
            debug_payload["error"] = {
                "type": type(e).__name__,
                "message": str(e),
            }
            debug_payload["result"] = result
            self._try_write_debug_json(debug_path, debug_payload)
            return result

    def _try_write_debug_json(
        self, path: Path, payload: Dict[str, Any]
    ) -> None:
        try:
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception:
            return

    def _make_agent(
        self, *, role_name: str, system_content: str
    ) -> "ChatAgent":
        from camel.agents import ChatAgent
        from camel.messages import BaseMessage

        system_message = BaseMessage.make_assistant_message(
            role_name=role_name, content=system_content
        )
        return ChatAgent(
            system_message=system_message,
            model=self._model,
            tools=[],
            step_timeout=self.config.step_timeout,
            tool_execution_timeout=self.config.tool_execution_timeout,
        )

    def _user_message(
        self, content: str, *, images: Optional[List[str]] = None
    ):
        if self.config.vision_type == "image":
            return BaseMessage.make_user_message(
                role_name="User", content=content, image_list=images
            )
        elif self.config.vision_type == "dom":
            # Inline DOM snapshots with clear separators
            if images:
                dom_blocks = "\n\n".join(
                    f"--- DOM Snapshot {i+1} ---\n{img}\n--- end DOM Snapshot {i+1} ---"
                    for i, img in enumerate(images)
                )
                content = f"{content}\n\n{dom_blocks}"
                return BaseMessage.make_user_message(
                    role_name="User", content=content
                )
            else:
                return BaseMessage.make_user_message(
                    role_name="User", content=content
                )
        else:
            raise ValueError(f"Unsupported vision_type: {self.config.vision_type}")


    def _identify_key_points(
        self, task: str
    ) -> Tuple[List[str], str, Dict[str, Any]]:
        agent = self._make_agent(
            role_name="WebJudge: Key Point Identifier",
            system_content=(
                "You are an expert tasked with analyzing a given task to identify the key points explicitly stated in the task description.\n\n"
                "**Objective**: Carefully analyze the task description and extract the critical elements explicitly mentioned in the task for achieving its goal.\n\n"
                "**Instructions**:\n"
                "1. Read the task description carefully.\n"
                "2. Identify and extract **key points** directly stated in the task description.\n"
                "   - A **key point** is a critical element, condition, or step explicitly mentioned in the task description.\n"
                "   - Do not infer or add any unstated elements.\n"
                '   - Words such as "best," "highest," "cheapest," "latest," "most recent," "lowest," "closest," "highest-rated," "largest," and "newest" must go through the sort function(e.g., the key point should be "Filter by highest").\n\n'
                "**Respond with**:\n"
                "- **Key Points**: A numbered list of the explicit key points for completing this task, one per line, without explanations or additional details."
            ),
        )
        prompt = f"Task: {task}"
        try:
            user_message = self._user_message(prompt)
            resp = agent.step(user_message)
            response_text = resp.msg.content or ""
        except Exception as ex:
            raise WebJudgeStageError(
                stage="key_points",
                prompt=prompt,
                response="",
                parse_error=f"agent.step failed: {ex}",
            )
        key_points_text = self._normalize_key_points_text(response_text)
        key_points = self._key_points_text_to_list(key_points_text)
        return (
            key_points,
            key_points_text,
            {
                "prompt": prompt,
                "response": response_text,
                "key_points_text": key_points_text,
            },
        )

    def _score_evidence(
        self,
        task: str,
        key_points_text: str,
        frames: List[VisionEvidenceFrame],
    ) -> Tuple[Dict[str, int], Dict[str, str], Dict[str, Any]]:
        data = "image" if self.config.vision_type == "image" else "DOM snapshot"
        system_msg = (
            f"You are an expert evaluator tasked with determining whether an {data} or text from DOM contains information about the necessary steps to complete a task.\n\n"
            f"**Objective**: Analyze the provided {data} and decide if it shows essential steps or evidence required for completing the task. Use your reasoning to explain your decision before assigning a score.\n\n"
            "**Instructions**:\n"
            f"1. Provide a detailed description of the {data}, including its contents, visible elements, text (if any), and any notable features.\n\n"
            f"2. Carefully examine the {data} and evaluate whether it contains necessary steps or evidence crucial to task completion:  \n"
            "- Identify key points that could be relevant to task completion, such as actions, progress indicators, tool usage, applied filters, or step-by-step instructions.  \n"
            f"- Does the {data} show actions, progress indicators, or critical information directly related to completing the task?  \n"
            "- Is this information indispensable for understanding or ensuring task success?\n"
            f"- If the {data} contains partial but relevant information, consider its usefulness rather than dismissing it outright.\n\n"
            "3. Provide your response in the following format:  \n"
            f"- **Reasoning**: Explain your thought process and observations. Mention specific elements in the {data} that indicate necessary steps, evidence, or lack thereof.  \n"
            "- **Score**: Assign a score based on the reasoning, using the following scale:  \n"
            f"    - **1**: The {data} does not contain any necessary steps or relevant information.  \n"
            f"    - **2**: The {data} contains minimal or ambiguous information, unlikely to be essential.  \n"
            f"    - **3**: The {data} includes some relevant steps or hints but lacks clarity or completeness.  \n"
            f"    - **4**: The {data} contains important steps or evidence that are highly relevant but not fully comprehensive.  \n"
            f"    - **5**: The {data} clearly displays necessary steps or evidence crucial for completing the task.\n\n"
            "Respond with:  \n"
            "1. **Reasoning**: [Your explanation]  \n"
            "2. **Score**: [1-5]\n"
        )

        scores: Dict[str, int] = {}
        thoughts: Dict[str, str] = {}
        per_frame: List[Dict[str, Any]] = []

        for evidence_no, f in enumerate(frames, start=1):
            agent = self._make_agent(
                role_name="WebJudge: Evidence Scorer",
                system_content=system_msg,
            )
            if self.config.vision_type == "image":
                resolved = self._resolve_path(f.screenshot_path)
                images = [self._file_to_data_url(resolved)] if resolved else [""]
            elif self.config.vision_type == "dom":
                resolved = self._resolve_path(f.snapshot_path)
                images = [self._file_to_dom_text(resolved)] if resolved else [""]
            else:
                raise ValueError(
                    f"Unsupported vision_type: {self.config.vision_type}"
                )
            prompt = (
                "**Task**: "
                f"{task}\n\n"
                "**Key Points for Task Completion**: "
                f"{key_points_text}\n\n" + "\n\n"
                f"The snapshot of the web page is shown in the {data}.\n\n"
            )
            resp = agent.step(self._user_message(prompt, images=images))
            response_text = resp.msg.content or ""
            score, reasoning = self._parse_score_reasoning(response_text)
            if score is not None:
                scores[f.frame_id] = max(1, min(5, score))
            if reasoning:
                thoughts[f.frame_id] = reasoning.replace("\n", " ").strip()

            per_frame.append(
                {
                    "evidence_no": evidence_no,
                    "frame_id": f.frame_id,
                    "screenshot_path": f.screenshot_path,
                    "prompt": prompt,
                    "response": response_text,
                    "parsed": {"score": score, "reasoning": reasoning},
                }
            )

        return (
            scores,
            thoughts,
            {
                "per_frame": per_frame,
            },
        )

    def _judge_outcome(
        self,
        *,
        task: str,
        action_history: str,
        key_points_text: str,
        evidence: List[VisionEvidenceFrame],
        evidence_thoughts: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        agent = self._make_agent(
            role_name="WebJudge: Outcome Judge",
            system_content=(
                "You are an expert in evaluating the performance of a web navigation agent. The agent is designed to help a human user navigate a website to complete a task. Given the user's task, the agent's action history, key points for task completion, some potentially important web pages in the agent's trajectory and their reasons, your goal is to determine whether the agent has completed the task and achieved all requirements.\n\n"
                "Your response must strictly follow the following evaluation criteria!\n"
                "*Important Evaluation Criteria*:\n"
                "1: The filtered results must be displayed correctly. If filters were not properly applied (i.e., missing selection, missing confirmation, or no visible effect in results), the task is not considered successful.\n"
                '2: You must carefully check whether these snapshots and action history meet these key points. Ensure that specific filter conditions, such as "best," "highest," "cheapest," "latest," "most recent," "lowest," "closest," "highest-rated," "largest," and "newest" are correctly applied using the filter function(e.g., sort function).\n'
                "3: Certain key points or requirements should be applied by the filter. Otherwise, a search with all requirements as input will be deemed a failure since it cannot guarantee that all results meet the requirements!\n"
                "4: If the task requires filtering by a specific range of money, years, or the number of beds and bathrooms, the applied filter must exactly match the given requirement. Any deviation results in failure. To ensure the task is successful, the applied filter must precisely match the specified range without being too broad or too narrow.\n"
                "Examples of Failure Cases:\n"
                "- If the requirement is less than $50, but the applied filter is less than $25, it is a failure.\n"
                "- If the requirement is $1500-$2500, but the applied filter is $2000-$2500, it is a failure.\n"
                "- If the requirement is $25-$200, but the applied filter is $0-$200, it is a failure.\n"
                "- If the required years are 2004-2012, but the filter applied is 2001-2012, it is a failure.\n"
                "- If the required years are before 2015, but the applied filter is 2000-2014, it is a failure.\n"
                "- If the task requires exactly 2 beds, but the filter applied is 2+ beds, it is a failure.\n"
                "5: Some tasks require a submission action or a display of results to be considered successful.\n"
                "6: If the retrieved information is invalid or empty(e.g., No match was found), but the agent has correctly performed the required action, it should still be considered successful.\n"
                "7: If the current page already displays all available items, then applying a filter is not necessary. As long as the agent selects items that meet the requirements (e.g., the cheapest or lowest price), the task is still considered successful.\n"
                "\n"
                "*IMPORTANT*\n"
                "Format your response into two lines as shown below:\n\n"
                "Thoughts: <your thoughts and reasoning process based on double-checking each key points and the evaluation criteria>\n"
                'Status: "success" or "failure"\n'
            ),
        )

        images: List[str] = []
        for f in evidence:
            if self.config.vision_type == "image":
                resolved = self._resolve_path(f.screenshot_path)
                images.append(self._file_to_data_url(resolved) if resolved else "")
            elif self.config.vision_type == "dom":
                resolved = self._resolve_path(f.snapshot_path)
                images.append(self._file_to_dom_text(resolved) if resolved else "")
            else:
                raise ValueError("Unsupported vision_type")    

        whole_thoughts: List[str] = []
        for t in evidence_thoughts:
            if not isinstance(t, dict):
                continue
            thought = str(t.get("reasoning", "")).strip()
            if thought:
                whole_thoughts.append(thought)

        action_lines = [
            ln.strip() for ln in action_history.splitlines() if ln.strip()
        ]
        last_actions_text = "\n".join(
            f"{i + 1}. {action}" for i, action in enumerate(action_lines)
        )

        if images:
            prompt = (
                f"User Task: {task}\n\n"
                f"Key Points: {key_points_text}\n\n"
                "Action History:\n"
                f"{last_actions_text}\n\n"
                "The potentially important snapshots of the webpage in the agent's trajectory and their reasons:\n"
                + "\n".join(
                    f"{i + 1}. {thought}"
                    for i, thought in enumerate(whole_thoughts)
                )
            )
        else:
            prompt = (
                f"User Task: {task}\n\n"
                f"Key Points: {key_points_text}\n\n"
                "Action History:\n"
                f"{last_actions_text}"
            )

        resp = agent.step(
            self._user_message(prompt, images=images if images else None)
        )
        response_text = resp.msg.content or ""
        success = self._extract_success_from_status(response_text)
        raison = response_text.strip()
        verdict = {
            "success": bool(success),
            "reasoning": raison,
            "suggestions": raison,
            "key_point_checks": [],
            "frame_descriptions": [],
        }
        return verdict, {
            "prompt": prompt,
            "response": response_text,
            "parsed": verdict,
        }

    def _select_evidence(
        self, frames: List[VisionEvidenceFrame], scores: Dict[str, int]
    ) -> Tuple[List[VisionEvidenceFrame], Dict[str, Any]]:
        threshold = int(self.config.evidence_score_threshold)
        selected_by_score = [
            f for f in frames if scores.get(f.frame_id, 0) >= threshold
        ]

        padded_ids: List[str] = []
        selected_ids = {f.frame_id for f in selected_by_score}
        selected = list(selected_by_score)
        if len(selected) < int(self.config.min_images_for_outcome):
            for f in reversed(frames):
                if f.frame_id in selected_ids:
                    continue
                selected.append(f)
                selected_ids.add(f.frame_id)
                padded_ids.append(f.frame_id)
                if len(selected) >= int(self.config.min_images_for_outcome):
                    break

        selected = sorted(selected, key=lambda x: x.action_step)[
            : int(self.config.max_images_for_outcome)
        ]
        return selected, {
            "threshold": threshold,
            "min_images_for_outcome": int(self.config.min_images_for_outcome),
            "max_images_for_outcome": int(self.config.max_images_for_outcome),
            "selected_by_score": [f.frame_id for f in selected_by_score],
            "padded_with_tail": padded_ids,
        }

    def _select_candidate_subset(
        self, frames: List[VisionEvidenceFrame]
    ) -> List[VisionEvidenceFrame]:
        if len(frames) <= self.config.max_frames:
            return frames

        important_actions = {
            "visit_page",
            "click",
            "type",
            "select",
            "press_key",
            "switch_tab",
            "scroll",
            "enter",
        }

        keep: List[VisionEvidenceFrame] = []
        keep_ids: set[str] = set()

        def add(f: VisionEvidenceFrame) -> None:
            if f.frame_id in keep_ids:
                return
            keep.append(f)
            keep_ids.add(f.frame_id)

        add(frames[0])
        add(frames[-1])

        last_url = None
        for f in frames:
            if len(keep) >= self.config.max_frames:
                break
            if f.url_after and f.url_after != last_url:
                add(f)
                last_url = f.url_after

        for f in frames:
            if len(keep) >= self.config.max_frames:
                break
            if f.action in important_actions:
                add(f)

        return sorted(keep, key=lambda x: x.action_step)[
            : self.config.max_frames
        ]

    def _normalize_key_points_text(self, key_points_response: str) -> str:
        text = (key_points_response or "").replace("\r\n", "\n").strip()
        text = text.replace("\n\n", "\n")
        try:
            text = text.split("**Key Points**:")[1]
        except Exception:
            text = text.split("Key Points:")[-1]
        text = "\n".join(line.lstrip() for line in text.splitlines())
        return text.strip()

    def _key_points_text_to_list(self, key_points_text: str) -> List[str]:
        points: List[str] = []
        for raw_line in (key_points_text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^\s*[\-\*\u2022]\s*", "", line)
            line = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", line)
            line = line.strip()
            if line:
                points.append(line)
        return points

    def _parse_score_reasoning(
        self, response_text: str
    ) -> Tuple[Optional[int], str]:
        text = (response_text or "").strip()
        score: Optional[int] = None
        try:
            score_text = re.split(
                r"Score", text, flags=re.IGNORECASE, maxsplit=1
            )[1]
            m = re.search(r"\b([1-5])\b", score_text)
            if m:
                score = int(m.group(1))
        except Exception:
            score = None

        reasoning = ""
        if "**Reasoning**:" in text:
            reasoning = text.split("**Reasoning**:")[-1].strip()
            reasoning = (
                reasoning.lstrip("\n").split("\n\n")[0].replace("\n", " ")
            )
        elif "Reasoning:" in text:
            reasoning = text.split("Reasoning:")[-1].strip()
            reasoning = reasoning.split("\n\n")[0].replace("\n", " ")
        return score, reasoning.strip()

    def _extract_success_from_status(self, response_text: str) -> bool:
        text = (response_text or "").strip().lower()
        if "status:" in text:
            after = text.split("status:", 1)[1]
            return "success" in after
        return "status" in text and "success" in text

    def _load_session_artifacts(self, session_dir: Path) -> Dict[str, Any]:
        timeline_path = session_dir / "action_timeline.json"
        complete_log_path = session_dir / "complete_browser_log.log"

        timeline: Dict[str, Any] = {}
        if timeline_path.exists():
            loaded = json.loads(
                timeline_path.read_text(encoding="utf-8", errors="ignore")
            )
            if isinstance(loaded, dict):
                timeline = loaded

        actions = parse_json_objects_log(complete_log_path)
        candidates = self._extract_screenshot_candidates(session_dir, actions)
        candidates = self._append_final_candidate(session_dir, candidates)
        candidates = sorted(candidates, key=lambda x: x.action_step)

        action_history = self._build_action_history(timeline, actions)
        action_history = truncate_middle(
            action_history, self.config.action_history_max_chars
        )

        return {
            "timeline": timeline,
            "actions": actions,
            "action_history": action_history,
            "candidates": candidates,
        }

    def _build_action_history(
        self, timeline: Dict[str, Any], actions: List[Dict[str, Any]]
    ) -> str:
        timeline_entries = timeline.get("timeline", [])
        if isinstance(timeline_entries, list) and timeline_entries:
            lines = []
            for entry in timeline_entries:
                if not isinstance(entry, dict):
                    continue
                ts = entry.get("timestamp", "")
                action_type = entry.get("action_type", "")
                url = entry.get("url_after") or entry.get("url_before") or ""
                if action_type == "subtask_replay":
                    name = entry.get("subtask_name", "")
                    variables = entry.get("variables_used", {})
                    lines.append(
                        f"[{ts}] subtask_replay: {name} variables={variables} url={url}"
                    )
                else:
                    action = entry.get("action", "")
                    args = entry.get("args", [])
                    label = entry.get("element_label")
                    lines.append(
                        f"[{ts}] action: {action} label={label} args={args} url={url}"
                    )
            return "\n".join(lines)

        excluded = {
            "get_tab_info",
            "get_page_snapshot",
            "get_snapshot_for_ai",
            "get_som_screenshot",
        }
        lines = []
        for i, a in enumerate(actions):
            action = a.get("action", "")
            if action in excluded:
                continue
            ts = a.get("timestamp", "")
            url_before, url_after = get_url_before_after(actions, i)
            inputs = (
                a.get("inputs", {})
                if isinstance(a.get("inputs"), dict)
                else {}
            )
            args = (
                inputs.get("args", [])
                if isinstance(inputs.get("args"), list)
                else []
            )
            lines.append(
                f"[{ts}] action: {action} args={args} url={url_after or url_before or ''}"
            )
        return "\n".join(lines)

    def _extract_screenshot_candidates(
        self, session_dir: Path, actions: List[Dict[str, Any]]
    ) -> List[VisionEvidenceFrame]:
        """ Load screenshots or DOM snapshots and actions to VisionEvidenceFrame. """
        frames: List[VisionEvidenceFrame] = []
        excluded_for_alignment = {
            "get_tab_info",
            "get_page_snapshot",
            "get_snapshot_for_ai",
            "get_som_screenshot",
            "open_browser",
            "close_browser",
        }
        for idx, action in enumerate(actions):
            screenshot_path = action.get("pre_capture_screenshot_path")
            if not isinstance(screenshot_path, str) or not screenshot_path:
                continue
            resolved = self._resolve_path_in_session(
                session_dir, screenshot_path
            )
            if resolved is None or not resolved.exists():
                continue

            snapshot_path = action.get("pre_capture_snapshot_path")
            if not isinstance(snapshot_path, str) or not snapshot_path:
                snapshot_path = None
            else:
                resolved_snapshot = self._resolve_path_in_session(
                    session_dir, snapshot_path
                )
                if resolved_snapshot is None or not resolved_snapshot.exists():
                    snapshot_path = None
                else:
                    snapshot_path = str(resolved_snapshot)

            # Next-step pre-capture alignment:
            # pre_capture at action[idx] represents the post-state of action[idx-1]
            target_idx = max(0, idx - 1)
            while (
                target_idx > 0
                and actions[target_idx].get("action") in excluded_for_alignment
            ):
                target_idx -= 1

            url_before, url_after = get_url_before_after(actions, target_idx)
            ts = action.get("pre_capture_captured_at") or action.get(
                "timestamp", ""
            )

            frames.append(
                VisionEvidenceFrame(
                    frame_id=f"post{target_idx}_pre{idx}",
                    action_step=target_idx,
                    timestamp=str(ts),
                    action=str(actions[target_idx].get("action", "")),
                    url_before=url_before,
                    url_after=url_after,
                    screenshot_path=str(resolved),
                    snapshot_path=snapshot_path,
                )
            )
        return frames

    def _append_final_candidate(
        self, session_dir: Path, frames: List[VisionEvidenceFrame]
    ) -> List[VisionEvidenceFrame]:
        """ Add final frame if available. """
        final_png = session_dir / "evidence" / "final.png"
        if final_png.exists():
            target_idx = frames[-1].action_step if frames else 10**9
            final_snapshot = session_dir / "evidence" / "final.snapshot.txt"
            frames.append(
                VisionEvidenceFrame(
                    frame_id="final",
                    action_step=target_idx,
                    timestamp="",
                    action="final_pre_capture",
                    url_before=None,
                    url_after=None,
                    screenshot_path=str(final_png),
                    snapshot_path=str(final_snapshot)
                    if final_snapshot.exists()
                    else None,
                )
            )
        return frames

    def _resolve_path_in_session(
        self, session_dir: Path, path_str: str
    ) -> Optional[Path]:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return session_dir / p

    def _resolve_path(self, path_str: str) -> Optional[Path]:
        p = Path(path_str)
        if p.exists():
            return p
        return None

    def _file_to_data_url(self, path: Path) -> str:
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:image/png;base64,{data}"

    def _file_to_dom_text(self, path: Path) -> str:
        """ Get DOM snapshot text from file. """
        try:
            dom = path.read_text(encoding="utf-8", errors="ignore")
            cleaned = clean_lines(dom)
            name = path.stem + ".cleaned.txt"
            with open(path.parent/name, "w", encoding="utf-8") as f:
                f.write(cleaned)
            return cleaned
        except Exception:
            return ""
        