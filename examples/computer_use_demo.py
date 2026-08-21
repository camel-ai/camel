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
r"""Minimal example: ComputerUseToolkit in local mode.

This demo creates a ComputerUseToolkit operating on the host display
(no Docker required) and exercises each tool category to confirm they
return expected status strings.

Requirements:
    - xdotool (``sudo apt install xdotool`` on Debian/Ubuntu)
    - ImageMagick (``sudo apt install imagemagick``)
"""

from camel.toolkits.computer_use_toolkit import ComputerUseToolkit


def main() -> None:
    toolkit = ComputerUseToolkit(
        display_width=1280,
        display_height=720,
        use_docker=False,
    )

    # ── Screen info ──────────────────────────────────────────
    print("Screen size:", toolkit.get_screen_size())
    print("Cursor position:", toolkit.get_cursor_position())

    # ── Mouse ────────────────────────────────────────────────
    print(toolkit.mouse_move(500, 300))
    print(toolkit.left_click())
    print(toolkit.scroll(3))
    print(toolkit.get_cursor_position())

    # ── Keyboard ─────────────────────────────────────────────
    print(toolkit.key_combination(["ctrl", "c"]))
    print(toolkit.type_text("Hello from CAMEL!"))

    # ── Screenshot ───────────────────────────────────────────
    img_b64 = toolkit.screenshot()
    print(f"Screenshot captured: {len(img_b64)} base64 chars")

    print("All tools exercised successfully.")


if __name__ == "__main__":
    main()
