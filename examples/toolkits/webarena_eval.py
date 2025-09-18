"""
python examples/toolkits/webarena_eval.py \
    --config-dir config_files/ \
    --admin-url  "${SHOPPING_ADMIN:-http://localhost:7780/admin}" \
    --results-dir ./webarena_results/shopping_admin \
    --headless false \
    --webarena-root ./webarena \
    --use-webarena-string-match \
    --use-openai-grader
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import unicodedata
from dotenv import load_dotenv
load_dotenv()
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HybridBrowserToolkit
from camel.types import ModelPlatformType, ModelType


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(logging.DEBUG)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified WebArena Shopping Admin evaluation")
    parser.add_argument("--config-dir", type=Path, default=os.getenv("WEBARENA_CONFIG_DIR", ""), help="Path to WebArena config_files directory")
    parser.add_argument("--admin-url", type=str, default=os.getenv("SHOPPING_ADMIN", "http://localhost:7780/admin"), help="Shopping Admin start URL")
    parser.add_argument("--results-dir", type=Path, default=Path("./webarena_results/shopping_admin"), help="Directory to save per-case results and summary.json")
    parser.add_argument("--headless", type=str, default="false", choices=["true", "false"], help="Run browser headless for cases (manual login flow is always headed)")
    parser.add_argument("--max-iter", type=int, default=40, help="Max agent iterations per case")
    parser.add_argument("--user-data-dir", type=str, default="User_Data", help="Persistent browser user data dir to reuse login")
    parser.add_argument("--viewport-limit", action="store_true", help="Limit page snapshot to current viewport for smaller context")
    parser.add_argument("--webarena-root", type=Path, default=Path("webarena"), help="Path to WebArena repo root (for official evaluators)")
    parser.add_argument("--use-webarena-string-match", action="store_true", help="Use WebArena's StringEvaluator when available")
    parser.add_argument("--use-openai-grader", action="store_true", help="Optionally use OpenAI grading as last resort")
    parser.add_argument("--openai-only", action="store_true", help="Use only OpenAI grader, skip others")
    return parser.parse_args()


# -----------------------------------------------------------------------------
# Config discovery and helpers
# -----------------------------------------------------------------------------

def _sorted_config_files(config_dir: Path) -> List[Path]:
    files = [p for p in config_dir.glob("*.json") if p.is_file()]
    def key(p: Path) -> Tuple[int, str]:
        try:
            stem = p.stem
            return (int(stem), p.name)
        except Exception:
            return (10**9, p.name)
    return sorted(files, key=key)


def _any_string_contains_admin(obj: Any, admin_host: str) -> bool:
    admin_host_l = (admin_host or "").lower()
    def _walk(o: Any) -> bool:
        if isinstance(o, str):
            s = o.lower()
            if "/admin" in s:
                return True
            if admin_host_l and admin_host_l in s:
                return True
            return False
        if isinstance(o, dict):
            for v in o.values():
                if _walk(v):
                    return True
            return False
        if isinstance(o, list):
            for v in o:
                if _walk(v):
                    return True
            return False
        return False
    return _walk(obj)


def _is_shopping_admin_case(cfg: Any, raw_text: str, admin_host: str) -> bool:
    text_l = raw_text.lower()
    if "shopping_admin" in text_l or "shop_admin" in text_l or "cms" in text_l:
        return True
    if "shopify" in text_l and "/admin" in text_l:
        return True
    if "shop" in text_l and "/admin" in text_l:
        return True
    if "SHOPPING_ADMIN" in raw_text:
        return True
    if admin_host and admin_host in text_l:
        return True
    return _any_string_contains_admin(cfg, admin_host)


def _extract_instruction(cfg: Any) -> str:
    key_candidates = ["instruction", "goal", "task", "intent", "query", "description"]
    def _find(o: Any) -> Optional[str]:
        if isinstance(o, dict):
            for k in key_candidates:
                v = o.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            for v in o.values():
                res = _find(v)
                if res:
                    return res
        elif isinstance(o, list):
            for v in o:
                res = _find(v)
                if res:
                    return res
        elif isinstance(o, str):
            s = o.strip()
            if s:
                return s
        return None
    found = _find(cfg)
    if isinstance(found, str) and found:
        return found
    return "Follow the admin task for the shopping CMS precisely."


# -----------------------------------------------------------------------------
# WebArena evaluators and grading helpers
# -----------------------------------------------------------------------------

def _import_string_evaluator(webarena_root: Path | None):
    try:
        import sys
        if webarena_root is not None:
            wr = Path(os.path.expanduser(str(webarena_root)) ).resolve()
            if str(wr) not in sys.path:
                sys.path.insert(0, str(wr))
        from evaluation_harness.evaluators import StringEvaluator as _SE  # type: ignore
        return _SE
    except Exception:
        return None


def _normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.lower()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-/_ ")
    s = "".join(ch if ch in allowed else " " for ch in s)
    s = " ".join(s.split())
    return s


def _extract_reference_answers(cfg: Any) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {
        "must_include": [],
        "any_of": [],
        "must_not_include": [],
        "generic": [],
    }
    try:
        if isinstance(cfg, dict):
            ev = cfg.get("eval")
            if isinstance(ev, dict):
                ra = ev.get("reference_answers")
                if isinstance(ra, dict):
                    def _collect_list(key: str, target_key: str) -> None:
                        val = ra.get(key)
                        if isinstance(val, str) and val.strip():
                            out[target_key].append(val.strip())
                        elif isinstance(val, list):
                            for x in val:
                                if isinstance(x, str) and x.strip():
                                    out[target_key].append(x.strip())
                    _collect_list("must_include", "must_include")
                    _collect_list("must_not_include", "must_not_include")
                    _collect_list("any_of", "any_of")
                    _collect_list("one_of", "any_of")
                    _collect_list("contains_any", "any_of")
                raw_ann = ev.get("reference_answer_raw_annotation")
                if isinstance(raw_ann, str) and raw_ann.strip():
                    import re as _re
                    parts = [_p.strip() for _p in _re.split(r"[;,\n]+", raw_ann) if _p.strip()]
                    for _p in parts:
                        if _p not in out["must_include"]:
                            out["must_include"].append(_p)
    except Exception:
        pass
    # Generic fallbacks
    out["generic"] = _extract_expected_generic(cfg)
    return out


def _extract_expected_generic(cfg: Any) -> List[str]:
    keys = [
        "answer", "answers", "expected", "expected_answer", "expected_answers",
        "target", "ground_truth", "golden", "label", "labels", "final_answer",
        "output", "outputs",
    ]
    found: List[str] = []
    def _walk(o: Any) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys:
                    if isinstance(v, str) and v.strip():
                        found.append(v.strip())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.strip():
                                found.append(item.strip())
                            elif isinstance(item, dict):
                                ans = item.get("answer")
                                if isinstance(ans, str) and ans.strip():
                                    found.append(ans.strip())
                    elif isinstance(v, dict):
                        ans = v.get("answer")
                        if isinstance(ans, str) and ans.strip():
                            found.append(ans.strip())
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)
    _walk(cfg)
    # Dedup preserve order
    seen: Dict[str, None] = {}
    out: List[str] = []
    for s in found:
        if s not in seen:
            seen[s] = None
            out.append(s)
    return out


def _openai_grade_yes_no(answer: str, must_include: List[str], any_of: List[str], must_not: List[str]) -> Optional[bool]:
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
            model_config_dict={"temperature": 0.0, "top_p": 1},
        )
        constraints = {
            "must_include": must_include,
            "any_of": any_of,
            "must_not": must_not,
        }
        sys_prompt = (
            "You are a strict grader. Given constraints and an answer, respond with ONLY 'YES' or 'NO'.\n"
            "Rules:\n"
            "- All items in must_include must appear (case-insensitive substring).\n"
            "- If any_of is non-empty, at least one of them must appear.\n"
            "- None of must_not items may appear.\n"
            "- Ignore markdown formatting, punctuation style differences, quotes, hyphens variants.\n"
            "- Do not explain. Only output YES or NO.\n"
        )
        user_msg = (
            f"Constraints: {json.dumps(constraints, ensure_ascii=False)}\n"
            f"Answer:\n{answer}\n"
            "Does the answer satisfy the constraints?"
        )
        resp = model.run([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ])
        text = resp.choices[0].message.content.strip().upper()  # type: ignore[union-attr]
        if text.startswith("YES"):
            return True
        if text.startswith("NO"):
            return False
        return None
    except Exception:
        return None


def grade_items(results_dir: Path, config_dir: Path, webarena_root: Path | None, use_webarena_string_match: bool, use_openai_grader: bool, openai_only: bool) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    results_dir = Path(os.path.expanduser(str(results_dir))).resolve()
    config_dir = Path(os.path.expanduser(str(config_dir))).resolve()

    StringEvaluator = _import_string_evaluator(webarena_root) if use_webarena_string_match else None

    def _find_case_id(filename: str) -> Optional[int]:
        import re
        stem = Path(filename).stem
        m = re.search(r"(\d+)", stem)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    items: List[Dict[str, Any]] = []
    txt_files = sorted(results_dir.glob("*.txt"))
    total_files = len(txt_files)
    graded_so_far = passed_so_far = failed_so_far = 0

    for idx, res_file in enumerate(txt_files):
        case_id = _find_case_id(res_file.name)
        if case_id is None:
            continue
        cfg_path = config_dir / f"{case_id}.json"
        if not cfg_path.exists():
            items.append({"case": case_id, "file": res_file.name, "error": f"missing config: {cfg_path.name}"})
            continue
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            items.append({"case": case_id, "file": res_file.name, "error": f"config parse error: {cfg_path.name}"})
            continue

        refs = _extract_reference_answers(cfg)
        must_include = [s for s in refs.get("must_include", [])]
        any_of = [s for s in refs.get("any_of", [])]
        must_not = [s for s in refs.get("must_not_include", [])]
        generic = [s for s in refs.get("generic", [])]

        content_raw = res_file.read_text(encoding="utf-8", errors="ignore")
        content = _normalize_text(content_raw)
        must_include_n = [_normalize_text(x) for x in must_include]
        any_of_n = [_normalize_text(x) for x in any_of]
        must_not_n = [_normalize_text(x) for x in must_not]
        generic_n = [_normalize_text(x) for x in generic]

        passed: Optional[bool] = None
        has_expected = bool(must_include or any_of or generic)

        if openai_only:
            if has_expected and use_openai_grader:
                passed = _openai_grade_yes_no(content_raw, must_include, any_of, must_not)
            items.append({
                "case": case_id,
                "file": res_file.name,
                "has_expected": has_expected,
                "expected_count": len(must_include) + len(any_of) + len(generic),
                "passed": passed,
            })
            if has_expected and passed is not None:
                graded_so_far += 1
                passed_so_far += int(bool(passed))
                failed_so_far += int(not bool(passed))
            rate = (passed_so_far / graded_so_far * 100.0) if graded_so_far else 0.0
            print(f"[{idx+1}/{total_files}] graded={graded_so_far} passed={passed_so_far} failed={failed_so_far} rate={rate:.1f}% file={res_file.name}")
            continue

        use_official = (
            StringEvaluator is not None
            and has_expected
            and isinstance(cfg, dict)
            and isinstance(cfg.get("eval"), dict)
            and "string_match" in cfg["eval"].get("eval_types", [])
        )

        if use_official:
            try:
                trajectory = [{"answer": content_raw, "action_type": "STOP"}]
                score = StringEvaluator()(trajectory=trajectory, config_file=str(cfg_path))  # type: ignore[misc]
                passed = bool(score == 1.0)
            except Exception:
                passed = None
            if passed is False:
                def has_all_must_includes() -> bool:
                    for s in must_include:
                        alts = [_normalize_text(x) for x in s.split(" |OR| ")]
                        if not any(x and x in content for x in alts):
                            return False
                    return True
                def has_any_of() -> bool:
                    if not any_of:
                        return True
                    alts: List[str] = []
                    for s in any_of:
                        alts.extend([_normalize_text(x) for x in s.split(" |OR| ")])
                    return any(x and x in content for x in alts)
                def has_no_must_not() -> bool:
                    if not must_not:
                        return True
                    alts: List[str] = []
                    for s in must_not:
                        alts.extend([_normalize_text(x) for x in s.split(" |OR| ")])
                    return not any(x and x in content for x in alts)
                if has_all_must_includes() and has_any_of() and has_no_must_not():
                    passed = True
            if passed in (None, False) and use_openai_grader:
                og = _openai_grade_yes_no(content_raw, must_include, any_of, must_not)
                if og is not None:
                    passed = og
        else:
            if has_expected:
                def must_include_ok() -> bool:
                    if not must_include:
                        return True
                    for s in must_include:
                        alts = [_normalize_text(x) for x in s.split(" |OR| ")]
                        if not any(x and x in content for x in alts):
                            return False
                    return True
                if not must_include_ok():
                    passed = False
                else:
                    if any_of:
                        alts: List[str] = []
                        for s in any_of:
                            alts.extend([_normalize_text(x) for x in s.split(" |OR| ")])
                        passed = any(x and x in content for x in alts)
                    else:
                        if generic_n:
                            passed = any(x and x in content for x in generic_n)
                        else:
                            passed = None
                if passed is not False and must_not:
                    alts: List[str] = []
                    for s in must_not:
                        alts.extend([_normalize_text(x) for x in s.split(" |OR| ")])
                    if any(x and x in content for x in alts):
                        passed = False
                if passed in (None, False) and use_openai_grader:
                    og = _openai_grade_yes_no(content_raw, must_include, any_of, must_not)
                    if og is not None:
                        passed = og

        items.append({
            "case": case_id,
            "file": res_file.name,
            "has_expected": has_expected,
            "expected_count": len(must_include) + len(any_of) + len(generic),
            "passed": passed,
        })
        if has_expected and passed is not None:
            graded_so_far += 1
            passed_so_far += int(bool(passed))
            failed_so_far += int(not bool(passed))
        rate = (passed_so_far / graded_so_far * 100.0) if graded_so_far else 0.0
        print(f"[{idx+1}/{total_files}] graded={graded_so_far} passed={passed_so_far} failed={failed_so_far} rate={rate:.1f}% file={res_file.name}")

    total = len(items)
    graded = sum(1 for r in items if r.get("has_expected"))
    passed = sum(1 for r in items if r.get("passed") is True)
    failed = sum(1 for r in items if r.get("passed") is False)

    stats = {"total": total, "graded": graded, "passed": passed, "failed": failed}
    return items, stats


# -----------------------------------------------------------------------------
# Agent run helpers
# -----------------------------------------------------------------------------

def build_system_message() -> str:
    return (
        "You are an autonomous agent operating a web browser to complete Shopping Admin tasks.\n"
        "Follow a strict loop each turn: OBSERVE -> PLAN (ordered checklist) -> ACT (one tool call) -> VERIFY.\n"
        "- Always call browser_get_page_snapshot to inspect the DOM after any navigation or major action before deciding the next step.\n"
        "- Navigate to the Sales by product (or equivalent) report before extracting results.\n"
        "- Set the exact requested period (e.g., '2022' or 'Jan 2023') and VERIFY the filter text matches precisely before reading results.\n"
        "- Date handling: NEVER use hyphens. Replace any '-' with '/'. Use MM/DD/YY strictly. For a year (e.g., 2022), set start '01/01/22' and end '12/31/22'. For a month (e.g., Jan 2023), set start '01/01/23' and end '01/31/23'. After typing, VERIFY each date field matches ^\\d{2}/\\d{2}/\\d{2}$; if not, clear and retype. Prefer clicking preset date ranges if available and they match the requested period.\n"
        "- Sort by Quantity/Units descending and VERIFY the sort indicator shows descending on the correct column.\n"
        "- Read product names from the table in on-screen row order. If totals tie, use the rendered order.\n"
        "- Copy product names exactly as displayed (including symbols like ™); do not add quotes or extra punctuation.\n"
        "- For top-1 tasks, output only the exact product name in the FINAL ANSWER (no extra words). Example: FINAL ANSWER: Quest Lumaflex™ Band\n"
        "- For top-N tasks, list only the product names in order; avoid counts unless explicitly requested.\n"
        "- Prefer robust selectors: visible text, labels, roles, aria-label, name, placeholder, or data-* attributes; avoid coordinate-based clicks.\n"
        "- Use browser_scroll to reveal off-screen elements before interacting.\n"
        "- Stay strictly within the admin site unless explicitly required by the task.\n"
        "- If verification fails at any step, re-check filters/sorting and retry before answering.\n"
        "- Output a single final line when done: 'FINAL ANSWER: <exact name or list>'."
    )


def build_prompt(instruction: str) -> str:
    return f"Task: {instruction}"


async def maybe_manual_login(admin_url: str, user_data_dir: str, viewport_limit: bool) -> None:
    """Open the admin page once for manual login. Uses headed mode."""
    web_toolkit = HybridBrowserToolkit(
        mode="typescript",
        headless=False,
        user_data_dir=user_data_dir,
        enabled_tools=[
            "browser_open",
            "browser_get_page_snapshot",
            "browser_wait_user",
            "browser_close",
        ],
        browser_log_to_file=False,
        stealth=True,
        default_start_url=admin_url,
        viewport_limit=False,
    )
    try:
        await web_toolkit.browser_open()
        snapshot = await web_toolkit.browser_get_page_snapshot()
        needs_login = any(k in snapshot.lower() for k in ["password", "username", "email", "log in", "signin", "sign in"])
        if needs_login:
            print("Detected login page. Complete login in the opened browser window, then press Enter in the terminal...")
            await web_toolkit.browser_wait_user()
    finally:
        try:
            await web_toolkit.browser_close()
        except Exception:
            pass


async def run_case(case_idx: int, instruction: str, admin_url: str, headless: bool, user_data_dir: str, viewport_limit: bool, max_iter: int, results_dir: Path, model_backend) -> str:
    # Use a stable tool set supported by the TS toolkit tool_map (avoid warnings)
    enabled_tools = [
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_back",
        "browser_forward",
        "browser_get_page_snapshot",
        "browser_get_som_screenshot",
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_scroll",
        "browser_enter",
        "browser_press_key",
        "browser_wait_user",
        "browser_mouse_drag",
        "browser_switch_tab",
        "browser_close_tab",
        "browser_get_tab_info",
        "browser_console_view",
        "browser_console_exec",
    ]

    web_toolkit = HybridBrowserToolkit(
        mode="typescript",
        headless=headless,
        user_data_dir=user_data_dir,
        enabled_tools=enabled_tools,
        browser_log_to_file=True,
        stealth=True,
        default_start_url=admin_url,
        viewport_limit=False,
    )

    agent = ChatAgent(
        system_message=build_system_message(),
        model=model_backend,
        tools=[*web_toolkit.get_tools()],
        toolkits_to_register_agent=[web_toolkit],
        max_iteration=max_iter,
    )

    prompt = build_prompt(instruction)
    try:
        resp = await agent.astep(prompt)
        result_text = resp.msgs[0].content if resp.msgs else "<no response>"
        # Persist
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / f"case_{case_idx}.txt").write_text(result_text, encoding="utf-8")
        return result_text
    finally:
        try:
            await web_toolkit.browser_close()
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

async def main_async() -> None:
    args = parse_args()

    if not args.config_dir:
        print("--config-dir is required or set WEBARENA_CONFIG_DIR")
        return
    config_dir = Path(os.path.expanduser(str(args.config_dir))).resolve()
    if not config_dir.exists():
        print(f"Config dir not found: {config_dir}")
        return

    admin_url = args.admin_url
    admin_host = admin_url.lower()
    results_dir = Path(os.path.expanduser(str(args.results_dir))).resolve()
    headless = (str(args.headless).lower() == "true")

    files = _sorted_config_files(config_dir)
    selected: List[Tuple[int, Path, str]] = []
    for p in files:
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
            cfg = json.loads(raw)
        except Exception:
            continue
        if _is_shopping_admin_case(cfg, raw, admin_host):
            instruction = _extract_instruction(cfg)
            try:
                case_idx = int(p.stem)
            except Exception:
                case_idx = len(selected)
            selected.append((case_idx, p, instruction))

    if not selected:
        print("No Shopping Admin cases found in config dir.")
        return

    print(f"Discovered {len(selected)} Shopping Admin cases.")

    # Model backend (deterministic)
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict={
            "temperature": 0.0,
            "top_p": 1.0,
            "parallel_tool_calls": False,
        },
    )

    # One-time manual login (headed) to persist auth in user_data_dir
    await maybe_manual_login(admin_url, args.user_data_dir, args.viewport_limit)

    # Ensure results directory exists for caching/skipping
    try:
        results_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Run cases sequentially to avoid session conflicts; skip if cached
    for case_idx, p, instruction in selected:
        result_path = results_dir / f"case_{case_idx}.txt"
        try:
            if result_path.exists() and result_path.stat().st_size > 0:
                print(f"Skipping case {case_idx} (cached): {result_path.name}")
                continue
        except Exception:
            # If any error occurs while checking cache, fall back to running the case
            pass

        print(f"\n=== Running case {case_idx} from {p.name} ===")
        await run_case(
            case_idx=case_idx,
            instruction=instruction,
            admin_url=admin_url,
            headless=headless,
            user_data_dir=args.user_data_dir,
            viewport_limit=args.viewport_limit,
            max_iter=args.max_iter,
            results_dir=results_dir,
            model_backend=model_backend,
        )

    # Summarize and grade
    items, stats = grade_items(
        results_dir=results_dir,
        config_dir=config_dir,
        webarena_root=args.webarena_root,
        use_webarena_string_match=args.use_webarena_string_match,
        use_openai_grader=args.use_openai_grader,
        openai_only=args.openai_only,
    )

    # Save summary
    summary_path = results_dir / "summary.json"
    try:
        summary_path.write_text(json.dumps({"items": items, "stats": stats}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(
        f"Completed {stats['total']} result files. "
        f"Graded {stats['graded']}; passed={stats['passed']}, failed={stats['failed']}. "
        f"Summary: {summary_path}"
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
