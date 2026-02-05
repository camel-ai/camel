#!/usr/bin/env python3
"""Summarize websites in dataset JSONL files (WebVoyager + Navi-Bench).

This script is intended to keep WEBSITE_GUIDELINES in sync with datasets.

Supported inputs:
- WebVoyager JSONL rows: {"web_name", "id", "ques", "web", ...}
- Navi-Bench JSONL rows: {"task_id", "domain", "task_generation_config_json", ...}
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from examples.toolkits.browser.browser_skills_example.core.skill_agent import (
    WEBSITE_GUIDELINES,
)


def _domain_to_display_website(domain: str) -> str:
    d = (domain or "").strip().lower()
    mapping = {
        "google_flights": "Google Flights",
        "opentable": "OpenTable",
        "craigslist": "Craigslist",
        "resy": "Resy",
        "apartments": "Apartments.com",
    }
    return mapping.get(d, domain.strip() or "Unknown")


def _try_parse_json(value: Any) -> Optional[dict]:
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _infer_website_from_row(row: dict) -> Tuple[str, str]:
    """Return (display_website, normalized_guidelines_key)."""
    if "web_name" in row:
        display = str(row.get("web_name") or "").strip() or "Unknown"
        return display, display.lower()

    domain = str(row.get("domain") or "").strip()
    display = _domain_to_display_website(domain)
    return display, display.lower()


def _infer_start_url_from_row(row: dict) -> str:
    if "web_name" in row:
        return str(row.get("web") or "").strip()

    cfg = _try_parse_json(row.get("task_generation_config_json"))
    if cfg and isinstance(cfg.get("url"), str):
        return cfg["url"].strip()
    return ""


def _host(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


@dataclass
class WebsiteStats:
    display: str
    guideline_key: str
    count: int = 0
    start_urls: Counter[str] = None  # type: ignore[assignment]
    hosts: Counter[str] = None  # type: ignore[assignment]
    samples: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.start_urls is None:
            self.start_urls = Counter()
        if self.hosts is None:
            self.hosts = Counter()
        if self.samples is None:
            self.samples = []


def load_jsonl(path: Path) -> Iterable[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_no}: {type(e).__name__}: {e}"
                ) from e
            if not isinstance(obj, dict):
                continue
            yield obj


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--jsonl",
        action="append",
        required=True,
        help="Path to a dataset jsonl file. Can be provided multiple times.",
    )
    ap.add_argument(
        "--show-samples",
        type=int,
        default=1,
        help="How many example task ids (or WebVoyager ids) to show per website.",
    )
    args = ap.parse_args()

    jsonl_paths = [Path(p).expanduser().resolve() for p in args.jsonl]

    by_display: Dict[str, WebsiteStats] = {}
    total_rows = 0
    formats = Counter()

    for path in jsonl_paths:
        for row in load_jsonl(path):
            total_rows += 1
            fmt = "webvoyager" if "web_name" in row else "navi_bench"
            formats[fmt] += 1

            display, guideline_key = _infer_website_from_row(row)
            stats = by_display.get(display)
            if stats is None:
                stats = WebsiteStats(
                    display=display, guideline_key=guideline_key
                )
                by_display[display] = stats

            stats.count += 1

            start_url = _infer_start_url_from_row(row)
            if start_url:
                stats.start_urls[start_url] += 1
                h = _host(start_url)
                if h:
                    stats.hosts[h] += 1

            sample_id = ""
            if "web_name" in row:
                sample_id = str(row.get("id") or "").strip()
            else:
                sample_id = str(row.get("task_id") or "").strip()
            if sample_id and len(stats.samples) < max(
                0, int(args.show_samples)
            ):
                stats.samples.append(sample_id)

    missing = []
    for display, stats in by_display.items():
        if stats.guideline_key not in WEBSITE_GUIDELINES:
            missing.append((display, stats.guideline_key, stats.count))

    # Print summary
    print(f"Rows: {total_rows}")
    print("Formats:")
    for fmt, c in formats.most_common():
        print(f"  - {fmt}: {c}")
    print()

    print(f"Websites: {len(by_display)}")
    for display, stats in sorted(
        by_display.items(), key=lambda kv: (-kv[1].count, kv[0].lower())
    ):
        top_url = (
            stats.start_urls.most_common(1)[0][0] if stats.start_urls else ""
        )
        top_host = stats.hosts.most_common(1)[0][0] if stats.hosts else ""
        sample = stats.samples[0] if stats.samples else ""
        ok = "yes" if stats.guideline_key in WEBSITE_GUIDELINES else "NO"
        print(
            f"- {display}: {stats.count}  (guidelines_key={stats.guideline_key!r}, covered={ok})"
        )
        if top_host or top_url:
            print(f"  start_host={top_host or '-'}")
            print(f"  start_url={top_url or '-'}")
        if sample:
            print(f"  sample={sample}")
    print()

    if missing:
        print("Missing WEBSITE_GUIDELINES entries (after normalization):")
        for display, key, count in sorted(
            missing, key=lambda x: (-x[2], x[0].lower())
        ):
            print(f"- {display} (normalized key={key!r}): {count}")
        raise SystemExit(2)

    print("All websites are covered by WEBSITE_GUIDELINES.")


if __name__ == "__main__":
    main()
