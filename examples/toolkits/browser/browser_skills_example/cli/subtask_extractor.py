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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mine reusable subtasks/skills from a session directory."""

from __future__ import annotations

import argparse

from examples.toolkits.browser.browser_skills_example.core.subtask_extractor import (
    analyze_with_agent,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "session_dir",
        help="Path to session folder containing action_timeline.json",
    )
    ap.add_argument(
        "skills_dir",
        nargs="?",
        default="",
        help="Optional skills directory. If omitted, will not write skills.",
    )
    args = ap.parse_args()

    session_dir = args.session_dir
    skills_dir = args.skills_dir.strip() or None
    analyze_with_agent(session_dir, skills_dir)


if __name__ == "__main__":
    main()
