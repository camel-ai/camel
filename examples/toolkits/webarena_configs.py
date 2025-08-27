"""
python examples/toolkits/webarena_configs.py \
    --webarena-path home/ishneet/Documents/camel/webarena \
    --output-dir home/ishneet/Documents/camel/config_files \
    --shopping-admin http://localhost:7780/admin
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and collect WebArena Shopping Admin config JSONs",
    )
    parser.add_argument(
        "--webarena-path",
        type=Path,
        required=True,
        help="Path to local webarena repo (containing scripts/generate_test_data.py)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to place filtered Shopping Admin JSON files",
    )
    parser.add_argument(
        "--shopping-admin",
        type=str,
        default=os.getenv("SHOPPING_ADMIN", ""),
        help="Shopping admin base URL, e.g. http://<domain>:7780/admin",
    )
    # Optional convenience: other WebArena site hosts
    parser.add_argument("--shopping", type=str, default=os.getenv("SHOPPING", ""))
    parser.add_argument("--reddit", type=str, default=os.getenv("REDDIT", ""))
    parser.add_argument("--gitlab", type=str, default=os.getenv("GITLAB", ""))
    parser.add_argument("--map", type=str, default=os.getenv("MAP", ""))
    parser.add_argument("--wikipedia", type=str, default=os.getenv("WIKIPEDIA", ""))
    parser.add_argument("--homepage", type=str, default=os.getenv("HOMEPAGE", ""))
    return parser.parse_args()


def ensure_webarena_paths(webarena_path: Path) -> Tuple[Path, Path]:
    # Expand user (~) and resolve to absolute path
    webarena_path = Path(os.path.expanduser(str(webarena_path))).resolve()
    gen_script = webarena_path / "scripts" / "generate_test_data.py"
    config_dir = webarena_path / "config_files"
    if not gen_script.exists():
        raise FileNotFoundError(
            f"Generator not found: {gen_script}. Expected a clone of the "
            f"WebArena repo with scripts/generate_test_data.py present."
        )
    config_dir.mkdir(parents=True, exist_ok=True)
    return gen_script, config_dir


def run_webarena_generator(gen_script: Path, env: Dict[str, str]) -> None:
    cmd = [sys.executable, str(gen_script)]
    proc = subprocess.run(cmd, cwd=str(gen_script.parent.parent), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"WebArena generator failed (exit {proc.returncode}).\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def is_shopping_admin_case(cfg: Dict, raw_text: str, admin_host: str) -> bool:
    text_l = raw_text.lower()
    if "shopping_admin" in text_l or "shop_admin" in text_l or "cms" in text_l:
        return True
    if "/admin" in text_l:
        return True
    if admin_host and admin_host.lower() in text_l:
        return True
    for key in [
        "url",
        "start_url",
        "homepage",
        "init_url",
        "initial_url",
        "domain",
        "target_url",
        "admin_url",
    ]:
        value = cfg.get(key)
        if isinstance(value, str):
            v = value.lower()
            if "/admin" in v or (admin_host and admin_host.lower() in v):
                return True
    return False


def filter_and_copy_configs(src_dir: Path, dst_dir: Path, admin_url: str) -> int:
    dst_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in src_dir.glob("*.json"):
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
            cfg = json.loads(raw)
        except Exception:
            continue
        if is_shopping_admin_case(cfg, raw, admin_url):
            shutil.copy2(str(p), str(dst_dir / p.name))
            count += 1
    return count


def build_env(args: argparse.Namespace) -> Dict[str, str]:
    env = os.environ.copy()
    # Pass through known WebArena envs if provided
    if args.shopping_admin:
        env["SHOPPING_ADMIN"] = args.shopping_admin
    if args.shopping:
        env["SHOPPING"] = args.shopping
    if args.reddit:
        env["REDDIT"] = args.reddit
    if args.gitlab:
        env["GITLAB"] = args.gitlab
    if args.map:
        env["MAP"] = args.map
    if args.wikipedia:
        env["WIKIPEDIA"] = args.wikipedia
    if args.homepage:
        env["HOMEPAGE"] = args.homepage
    return env


def main() -> None:
    args = parse_args()
    # Expand output dir as well
    args.output_dir = Path(os.path.expanduser(str(args.output_dir))).resolve()
    gen_script, webarena_config_dir = ensure_webarena_paths(args.webarena_path)

    if not args.shopping_admin:
        raise SystemExit(
            "--shopping-admin is required (e.g., http://<host>:7780/admin)."
        )

    env = build_env(args)
    print("Running WebArena generator ...")
    run_webarena_generator(gen_script, env)

    print("Filtering Shopping Admin cases ...")
    selected = filter_and_copy_configs(webarena_config_dir, args.output_dir, args.shopping_admin)

    print(f"Done. Copied {selected} Shopping Admin JSON files to: {args.output_dir}")
    if selected == 0:
        print("Warning: no Shopping Admin cases detected. Ensure your admin URL and sites are configured.")
    print("Set WEBARENA_CONFIG_DIR to this folder for the example run.")


if __name__ == "__main__":
    main()


