"""
python examples/toolkits/saved_eval.py \
    --config-dir config_files/ \
    --results-dir ./webarena_results/shopping_admin \
    --webarena-root ./webarena \
    --use-webarena-string-match \
    --use-openai-grader
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Reuse the grading logic from the unified eval script (same directory)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from webarena_shopping_admin_unified_eval import grade_items  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate saved WebArena Shopping Admin results from .txt files"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=os.getenv("WEBARENA_CONFIG_DIR", ""),
        help="Path to WebArena config_files directory (where <id>.json live)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("./webarena_results/shopping_admin"),
        help="Directory containing saved case_<id>.txt and where summary.json will be written",
    )
    parser.add_argument(
        "--webarena-root",
        type=Path,
        default=Path("webarena"),
        help="Path to WebArena repo root (only needed if using official evaluator)",
    )
    parser.add_argument(
        "--use-webarena-string-match",
        action="store_true",
        help="Use WebArena's StringEvaluator when available",
    )
    parser.add_argument(
        "--use-openai-grader",
        action="store_true",
        help="Optionally use OpenAI grading as last resort",
    )
    parser.add_argument(
        "--openai-only",
        action="store_true",
        help="Use only OpenAI grader (skip others)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve and validate paths
    if not args.config_dir:
        print("--config-dir is required or set WEBARENA_CONFIG_DIR")
        return
    config_dir = Path(os.path.expanduser(str(args.config_dir))).resolve()
    if not config_dir.exists():
        print(f"Config dir not found: {config_dir}")
        return

    results_dir = Path(os.path.expanduser(str(args.results_dir))).resolve()
    if not results_dir.exists():
        print(f"Results dir not found: {results_dir}")
        return

    txt_files = list(results_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt result files found in {results_dir}")
        return

    # Grade using shared function
    items, stats = grade_items(
        results_dir=results_dir,
        config_dir=config_dir,
        webarena_root=args.webarena_root,
        use_webarena_string_match=args.use_webarena_string_match,
        use_openai_grader=args.use_openai_grader,
        openai_only=args.openai_only,
    )
    
    # Collect failed indices and case IDs for convenience
    failed_item_indices = [i for i, r in enumerate(items) if r.get("passed") is False]
    failed_cases = [r.get("case") for r in items if r.get("passed") is False]

    # Save summary
    summary_path = results_dir / "summary.json"
    try:
        summary_path.write_text(
            json.dumps(
                {
                    "items": items,
                    "stats": stats,
                    "failed_item_indices": failed_item_indices,
                    "failed_cases": failed_cases,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    print(
        f"Completed {stats['total']} result files. "
        f"Graded {stats['graded']}; passed={stats['passed']}, failed={stats['failed']}. "
        f"Summary: {summary_path}"
    )
    if failed_cases:
        print(f"Failed case IDs: {failed_cases}")
        print(f"Failed item indices: {failed_item_indices}")


if __name__ == "__main__":
    main()
