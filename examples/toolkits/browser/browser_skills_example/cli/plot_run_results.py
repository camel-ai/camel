#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot metrics for a `run_webvoyager_tasks.py` run.

Example:
  python -m examples.toolkits.browser.browser_skills_example.cli.plot_run_results \
    --run-dir examples/toolkits/browser_skills_example/runs/run_20260108_184446
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _session_sort_key(session_dir: str) -> str:
    # Typical: .../session_YYYYMMDD_HHMMSS
    m = re.search(r"session_(\d{8}_\d{6})$", session_dir)
    return m.group(1) if m else session_dir


def _collect_sessions_from_results(results: List[Dict[str, Any]]) -> List[str]:
    session_dirs: List[str] = []
    for item in results:
        for h in item.get("attempt_history") or []:
            sd = h.get("session_dir") or ""
            if sd:
                session_dirs.append(sd)
        sd = item.get("session_dir") or ""
        if sd:
            session_dirs.append(sd)

    seen: set[str] = set()
    unique: List[str] = []
    for sd in session_dirs:
        if sd in seen:
            continue
        seen.add(sd)
        unique.append(sd)
    return sorted(unique, key=_session_sort_key)


def _get_main_tokens_total(agent_comm: Dict[str, Any]) -> Optional[int]:
    comms = agent_comm.get("communications") or []
    mains = [c for c in comms if c.get("type") == "main_agent_call"]
    if not mains:
        return None
    tokens = mains[-1].get("tokens")
    if not isinstance(tokens, dict):
        return None
    total = tokens.get("total_tokens")
    if total is None:
        total = tokens.get("total")
    if isinstance(total, int):
        return total
    if isinstance(total, float):
        return int(total)
    return None


@dataclass(frozen=True)
class SessionPoint:
    session_dir: Path
    attempt_index: int
    website: str
    verification_success: Optional[bool]
    reuse_ratio_actions: Optional[float]
    reuse_ratio_calls: Optional[float]
    actions_total: Optional[int]
    actions_in_subtasks: Optional[int]
    subtask_calls: Optional[int]
    browser_tool_calls: Optional[int]
    net_toolcall_savings: Optional[int]
    subtasks_available_before: Optional[int]
    subtasks_available_after: Optional[int]
    main_total_tokens: Optional[int]


def _load_session_points(session_dirs: List[str]) -> List[SessionPoint]:
    points: List[SessionPoint] = []
    for idx, sd in enumerate(session_dirs, start=1):
        session_dir = Path(sd)
        summary_path = session_dir / "summary.json"
        agent_comm_path = session_dir / "agent_communication_log.json"
        if not summary_path.exists():
            continue
        summary = _read_json(summary_path)

        agent_comm: Dict[str, Any] = {}
        if agent_comm_path.exists():
            agent_comm = _read_json(agent_comm_path)

        reuse = summary.get("reuse") or {}
        actions_total = reuse.get("actions_total")
        actions_in_subtasks = reuse.get("actions_in_subtasks")
        subtask_calls = reuse.get("subtask_calls")
        browser_tool_calls = reuse.get("browser_tool_calls")
        savings = None
        if isinstance(actions_in_subtasks, int) and isinstance(
            subtask_calls, int
        ):
            savings = actions_in_subtasks - subtask_calls

        verification = summary.get("verification") or {}
        verification_success = verification.get("success")
        if not isinstance(verification_success, bool):
            verification_success = None

        points.append(
            SessionPoint(
                session_dir=session_dir,
                attempt_index=idx,
                website=str(summary.get("website") or ""),
                verification_success=verification_success,
                reuse_ratio_actions=reuse.get("reuse_ratio_actions"),
                reuse_ratio_calls=reuse.get("reuse_ratio_calls"),
                actions_total=actions_total,
                actions_in_subtasks=actions_in_subtasks,
                subtask_calls=subtask_calls,
                browser_tool_calls=browser_tool_calls,
                net_toolcall_savings=savings,
                subtasks_available_before=summary.get(
                    "subtasks_available_before"
                ),
                subtasks_available_after=summary.get(
                    "subtasks_available_after"
                ),
                main_total_tokens=_get_main_tokens_total(agent_comm),
            )
        )
    return points


def _load_subtask_stats(stats_path: Path) -> Dict[str, Any]:
    if not stats_path.exists():
        return {}
    data = _read_json(stats_path)
    if not isinstance(data, dict):
        return {}
    return data


def _aggregate_subtask_stats_by_name(
    stats: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Returns rows sorted by calls_total desc:
      {subtask_name, calls_total, success, partial_success, error, other, success_rate, partial_rate, ids}
    """
    subtasks = stats.get("subtasks") or {}
    by_name: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "subtask_name": "",
            "calls_total": 0,
            "success": 0,
            "partial_success": 0,
            "error": 0,
            "other": 0,
            "ids": [],
        }
    )

    for sid, row in subtasks.items():
        if not isinstance(row, dict):
            continue
        name = str(row.get("subtask_name") or "").strip() or f"subtask_{sid}"
        agg = by_name[name]
        agg["subtask_name"] = name
        agg["ids"].append(str(sid))
        for k in [
            "calls_total",
            "success",
            "partial_success",
            "error",
            "other",
        ]:
            v = row.get(k, 0)
            if isinstance(v, int):
                agg[k] += v

    out: List[Dict[str, Any]] = []
    for _name, agg in by_name.items():
        total = agg["calls_total"]
        success_rate = (agg["success"] / total) if total else 0.0
        partial_rate = (agg["partial_success"] / total) if total else 0.0
        out.append(
            {
                **agg,
                "success_rate": success_rate,
                "partial_rate": partial_rate,
                "failure_rate": 1.0 - success_rate,
            }
        )
    out.sort(key=lambda r: r["calls_total"], reverse=True)
    return out


def _corr(x: List[float], y: List[float]) -> Optional[float]:
    if len(x) != len(y) or not x:
        return None
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / len(x)
    vx = sum((a - mx) ** 2 for a in x) / len(x)
    vy = sum((b - my) ** 2 for b in y) / len(y)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def plot_run(run_dir: Path, out_dir: Path) -> Dict[str, Any]:
    import matplotlib.pyplot as plt

    results_path = run_dir / "results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"results.json not found: {results_path}")
    results = _read_json(results_path)
    if not isinstance(results, list):
        raise ValueError("results.json must be a JSON list")

    session_dirs = _collect_sessions_from_results(results)
    points = _load_session_points(session_dirs)
    if not points:
        raise RuntimeError(
            "No session summaries found (expected session_dir/summary.json)"
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Figure 1: reuse_ratio_actions over attempts (+ skills growth) ----
    x = [p.attempt_index for p in points]
    reuse_a = [p.reuse_ratio_actions for p in points]
    reuse_a_y = [
        v if isinstance(v, (int, float)) else float("nan") for v in reuse_a
    ]
    skills_after = [
        p.subtasks_available_after
        if isinstance(p.subtasks_available_after, int)
        else float("nan")
        for p in points
    ]
    ok = [p.verification_success for p in points]
    ok_mask = [v is True for v in ok]
    bad_mask = [v is False for v in ok]

    fig = plt.figure(figsize=(12, 6))
    ax1 = fig.add_subplot(111)
    ax1.plot(
        x,
        reuse_a_y,
        color="#1f77b4",
        linewidth=1.5,
        label="Reuse ratio (actions)",
    )
    ax1.scatter(
        [x[i] for i in range(len(x)) if ok_mask[i]],
        [reuse_a_y[i] for i in range(len(x)) if ok_mask[i]],
        color="#2ca02c",
        s=20,
        label="Verified success",
        zorder=3,
    )
    ax1.scatter(
        [x[i] for i in range(len(x)) if bad_mask[i]],
        [reuse_a_y[i] for i in range(len(x)) if bad_mask[i]],
        color="#d62728",
        s=20,
        label="Verified fail",
        zorder=3,
    )
    ax1.set_xlabel("Attempt (chronological)")
    ax1.set_ylabel("Reuse ratio (actions)")
    ax1.set_title("Skill Reuse Over Time (Actions)")
    ax1.set_ylim(0, 1.0)
    ax1.grid(True, alpha=0.2)

    ax2 = ax1.twinx()
    ax2.plot(
        x,
        skills_after,
        color="#9467bd",
        linewidth=1.5,
        alpha=0.8,
        label="Subtasks available (after)",
    )
    ax2.set_ylabel("Subtasks available")

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")

    reuse_over_time_png = out_dir / "reuse_over_time.png"
    fig.tight_layout()
    fig.savefig(reuse_over_time_png, dpi=160)
    plt.close(fig)

    # ---- Figure 2: tokens vs reuse (scatter) ----
    xs: List[float] = []
    ys: List[float] = []
    colors: List[str] = []
    for p in points:
        if not isinstance(p.reuse_ratio_actions, (int, float)):
            continue
        if not isinstance(p.main_total_tokens, int):
            continue
        xs.append(float(p.reuse_ratio_actions))
        ys.append(float(p.main_total_tokens))
        if p.verification_success is True:
            colors.append("#2ca02c")
        elif p.verification_success is False:
            colors.append("#d62728")
        else:
            colors.append("#7f7f7f")

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)
    ax.scatter(xs, ys, c=colors, s=25, alpha=0.85)
    ax.set_xlabel("Reuse ratio (actions)")
    ax.set_ylabel("Main agent total tokens")
    ax.set_title("Tokens vs Reuse (per attempt)")
    ax.grid(True, alpha=0.2)
    corr = _corr(xs, ys)
    if corr is not None:
        ax.text(
            0.02,
            0.98,
            f"corr ≈ {corr:.2f}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=11,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )
    tokens_vs_reuse_png = out_dir / "tokens_vs_reuse.png"
    fig.tight_layout()
    fig.savefig(tokens_vs_reuse_png, dpi=160)
    plt.close(fig)

    # ---- Figure 3: net toolcall savings over time ----
    savings = [
        p.net_toolcall_savings
        if isinstance(p.net_toolcall_savings, int)
        else float("nan")
        for p in points
    ]
    fig = plt.figure(figsize=(12, 5))
    ax = fig.add_subplot(111)
    ax.plot(x, savings, color="#ff7f0e", linewidth=1.5)
    ax.set_xlabel("Attempt (chronological)")
    ax.set_ylabel("Net toolcall savings (actions_in_subtasks - subtask_calls)")
    ax.set_title("Estimated LLM Tool-Call Savings From Skill Replay")
    ax.grid(True, alpha=0.2)
    savings_png = out_dir / "toolcall_savings_over_time.png"
    fig.tight_layout()
    fig.savefig(savings_png, dpi=160)
    plt.close(fig)

    # ---- Figure 4: subtask success/partial rate (top N by calls) ----
    # Guess stats path from first session's skills_dir or run_summary if present.
    stats_path = None
    for p in points:
        # Try infer from summary.json
        summary = _read_json(p.session_dir / "summary.json")
        skills_dir = summary.get("skills_dir")
        if isinstance(skills_dir, str) and skills_dir:
            stats_path = Path(skills_dir) / "subtask_stats.json"
            break
    stats = _load_subtask_stats(stats_path) if stats_path else {}
    by_name = _aggregate_subtask_stats_by_name(stats) if stats else []

    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)
    if by_name:
        top_n = min(10, len(by_name))
        rows = by_name[:top_n]
        names = [r["subtask_name"] for r in rows]
        calls = [r["calls_total"] for r in rows]
        succ_rate = [r["success_rate"] for r in rows]
        partial_rate = [r["partial_rate"] for r in rows]

        y_pos = list(range(top_n))
        ax.barh(
            y_pos, succ_rate, color="#2ca02c", alpha=0.85, label="success_rate"
        )
        ax.barh(
            y_pos,
            partial_rate,
            left=succ_rate,
            color="#ffbb78",
            alpha=0.95,
            label="partial_rate",
        )
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names)
        ax.invert_yaxis()
        ax.set_xlabel("Rate")
        ax.set_title("Top Subtasks by Call Volume (success vs partial)")
        ax.set_xlim(0, 1.0)
        ax.grid(True, axis="x", alpha=0.2)
        ax.legend(loc="lower right")

        # annotate calls
        for i, c in enumerate(calls):
            ax.text(
                1.01,
                i,
                f"{c} calls",
                va="center",
                fontsize=10,
                transform=ax.get_yaxis_transform(),
            )
    else:
        ax.text(
            0.5, 0.5, "subtask_stats.json not found", ha="center", va="center"
        )
        ax.axis("off")

    subtask_rates_png = out_dir / "subtask_success_rates.png"
    fig.tight_layout()
    fig.savefig(subtask_rates_png, dpi=160)
    plt.close(fig)

    # ---- Emit a small JSON report for programmatic consumption ----
    report: Dict[str, Any] = {
        "run_dir": str(run_dir),
        "out_dir": str(out_dir),
        "plots": {
            "reuse_over_time": str(reuse_over_time_png),
            "tokens_vs_reuse": str(tokens_vs_reuse_png),
            "toolcall_savings_over_time": str(savings_png),
            "subtask_success_rates": str(subtask_rates_png),
        },
        "summary": {
            "sessions": len(points),
            "reuse_ratio_actions": {
                "min": float(min(v for v in reuse_a_y if not math.isnan(v))),
                "max": float(max(v for v in reuse_a_y if not math.isnan(v))),
                "avg": float(
                    sum(v for v in reuse_a_y if not math.isnan(v))
                    / len([v for v in reuse_a_y if not math.isnan(v)])
                ),
            },
            "subtasks_available_after": {
                "min": int(min(v for v in skills_after if not math.isnan(v))),
                "max": int(max(v for v in skills_after if not math.isnan(v))),
            },
            "token_reuse_corr": corr,
            "stats_path": str(stats_path) if stats_path else "",
        },
    }
    _write_json(out_dir / "plots_report.json", report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run-dir",
        required=True,
        help="Run directory containing results.json (and optionally run_summary.json).",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output directory for PNGs (default: <run-dir>/plots).",
    )
    args = ap.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    out_dir = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else (run_dir / "plots")
    )

    report = plot_run(run_dir=run_dir, out_dir=out_dir)
    print("OK: wrote plots to", report["out_dir"])
    for k, v in report["plots"].items():
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
