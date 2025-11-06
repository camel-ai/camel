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
from __future__ import annotations

import io
import json
import random
import re
from typing import (
    Any,
    BinaryIO,
    Dict,
    List,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from PIL import Image, ImageDraw, ImageFont

# Constants
TOP_NO_LABEL_ZONE = 20

WEB_AGENT_SYSTEM_PROMPT = """
You are a helpful web agent that can assist users in browsing the web.
Given a high-level task, you can leverage predefined browser tools to help
users achieve their goals.
        """

PLANNING_AGENT_SYSTEM_PROMPT = """
You are a helpful planning agent that can assist users in planning complex
tasks which need multi-step browser interaction.
        """

OBSERVE_PROMPT_TEMPLATE = """
Please act as a web agent to help me complete the following high-level task:
<task>{task_prompt}</task>
Now, I have made screenshot (only the current viewport, not the full webpage)
based on the current browser state, and marked interactive elements in the
webpage.
Please carefully examine the requirements of the task, and current state of
the browser, and provide the next appropriate action to take.

{detailed_plan_prompt}

Here are the current available browser functions you can use:
{AVAILABLE_ACTIONS_PROMPT}

Here are the latest {history_window} trajectory (at most) you have taken:
<history>
{history}
</history>

Your output should be in json format, including the following fields:
- `observation`: The detailed image description about the current viewport. Do
not over-confident about the correctness of the history actions. You should
always check the current viewport to make sure the correctness of the next
action.
- `reasoning`: The reasoning about the next action you want to take, and the
possible obstacles you may encounter, and how to solve them. Do not forget to
check the history actions to avoid the same mistakes.
- `action_code`: The action code you want to take. It is only one step action
code, without any other texts (such as annotation)

Here is two example of the output:
```json
{{
    "observation": [IMAGE_DESCRIPTION],
    "reasoning": [YOUR_REASONING],
    "action_code": "fill_input_id([ID], [TEXT])"
}}

{{
    "observation":  "The current page is a CAPTCHA verification page on Amazon. It asks the user to ..",
    "reasoning": "To proceed with the task of searching for products, I need to complete..",
    "action_code": "fill_input_id(3, 'AUXPMR')"
}}

Here are some tips for you:
- Never forget the overall question: **{task_prompt}**
- Maybe after a certain operation (e.g. click_id), the page content has not
changed. You can check whether the action step is successful by looking at the
`success` of the action step in the history. If successful, it means that the
page content is indeed the same after the click. You need to try other methods.
- If using one way to solve the problem is not successful, try other ways.
Make sure your provided ID is correct!
- Some cases are very complex and need to be achieve by an iterative process.
You can use the `back()` function to go back to the previous page to try other
methods.
- There are many links on the page, which may be useful for solving the
problem. You can use the `click_id()` function to click on the link to see if
it is useful.
- Always keep in mind that your action must be based on the ID shown in the
current image or viewport, not the ID shown in the history.
- Do not use `stop()` lightly. Always remind yourself that the image only
shows a part of the full page. If you cannot find the answer, try to use
functions like `scroll_up()` and `scroll_down()` to check the full content of
the webpage before doing anything else, because the answer or next key step
may be hidden in the content below.
- If the webpage needs human verification, you must avoid processing it.
Please use `back()` to go back to the previous page, and try other ways.
- If you have tried everything and still cannot resolve the issue, please stop
the simulation, and report issues you have encountered.
- Check the history actions carefully, detect whether you have repeatedly made
the same actions or not.
- When dealing with wikipedia revision history related tasks, you need to
think about the solution flexibly. First, adjust the browsing history
displayed on a single page to the maximum, and then make use of the
find_text_on_page function. This is extremely useful which can quickly locate
the text you want to find and skip massive amount of useless information.
- Flexibly use interactive elements like slide down selection bar to filter
out the information you need. Sometimes they are extremely useful.
```
"""  # noqa: E501

GET_FINAL_ANSWER_PROMPT_TEMPLATE = """
We are solving a complex web task which needs multi-step browser interaction. After the multi-step observation, reasoning and acting with web browser, we think that the task is currently solved.
Here are all trajectory we have taken:
<history>{history}</history>
Please find the final answer, or give valuable insights and founds (e.g. if previous actions contain downloading files, your output should include the path of the downloaded file) about the overall task: <task>{task_prompt}</task>
        """  # noqa: E501

TASK_PLANNING_PROMPT_TEMPLATE = """
<task>{task_prompt}</task>
According to the problem above, if we use browser interaction, what is the general process of the interaction after visiting the webpage `{start_url}`? 

Please note that it can be viewed as Partially Observable MDP. Do not over-confident about your plan.
Please first restate the task in detail, and then provide a detailed plan to solve the task.
"""  # noqa: E501

TASK_REPLANNING_PROMPT_TEMPLATE = """
We are using browser interaction to solve a complex task which needs multi-step actions.
Here are the overall task:
<overall_task>{task_prompt}</overall_task>

In order to solve the task, we made a detailed plan previously. Here is the detailed plan:
<detailed plan>{detailed_plan}</detailed plan>

According to the task above, we have made a series of observations, reasonings, and actions. Here are the latest {history_window} trajectory (at most) we have taken:
<history>{history}</history>

However, the task is not completed yet. As the task is partially observable, we may need to replan the task based on the current state of the browser if necessary.
Now please carefully examine the current task planning schema, and our history actions, and then judge whether the task needs to be fundamentally replanned. If so, please provide a detailed replanned schema (including the restated overall task).

Your output should be in json format, including the following fields:
- `if_need_replan`: bool, A boolean value indicating whether the task needs to be fundamentally replanned.
- `replanned_schema`: str, The replanned schema for the task, which should not be changed too much compared with the original one. If the task does not need to be replanned, the value should be an empty string. 
"""  # noqa: E501

AVAILABLE_ACTIONS_PROMPT = """
1. `fill_input_id(identifier: Union[str, int], text: str)`: Fill an input
field (e.g. search box) with the given text and press Enter.
2. `click_id(identifier: Union[str, int])`: Click an element with the given ID.
3. `hover_id(identifier: Union[str, int])`: Hover over an element with the
given ID.
4. `download_file_id(identifier: Union[str, int])`: Download a file with the
given ID. It returns the path to the downloaded file. If the file is
successfully downloaded, you can stop the simulation and report the path to
the downloaded file for further processing.
5. `scroll_to_bottom()`: Scroll to the bottom of the page.
6. `scroll_to_top()`: Scroll to the top of the page.
7. `scroll_up()`: Scroll up the page. It is suitable when you want to see the
elements above the current viewport.
8. `scroll_down()`: Scroll down the page. It is suitable when you want to see
the elements below the current viewport. If the webpage does not change, It
means that the webpage has scrolled to the bottom.
9. `back()`: Navigate back to the previous page. This is useful when you want
to go back to the previous page, as current page is not useful.
10. `stop()`: Stop the action process, because the task is completed or failed
(impossible to find the answer). In this situation, you should provide your
answer in your output.
11. `get_url()`: Get the current URL of the current page.
12. `find_text_on_page(search_text: str)`: Find the next given text on the
current whole page, and scroll the page to the targeted text. It is equivalent
to pressing Ctrl + F and searching for the text, and is powerful when you want
to fast-check whether the current page contains some specific text.
13. `visit_page(url: str)`: Go to the specific url page.
14. `click_blank_area()`: Click a blank area of the page to unfocus the
current element. It is useful when you have clicked an element but it cannot
unfocus itself (e.g. Menu bar) to automatically render the updated webpage.
15. `ask_question_about_video(question: str)`: Ask a question about the
current webpage which contains video, e.g. youtube websites.
"""

ACTION_WITH_FEEDBACK_LIST = [
    'ask_question_about_video',
    'download_file_id',
    'find_text_on_page',
]


# TypedDicts
class DOMRectangle(TypedDict):
    x: Union[int, float]
    y: Union[int, float]
    width: Union[int, float]
    height: Union[int, float]
    top: Union[int, float]
    right: Union[int, float]
    bottom: Union[int, float]
    left: Union[int, float]


class VisualViewport(TypedDict):
    height: Union[int, float]
    width: Union[int, float]
    offsetLeft: Union[int, float]
    offsetTop: Union[int, float]
    pageLeft: Union[int, float]
    pageTop: Union[int, float]
    scale: Union[int, float]
    clientWidth: Union[int, float]
    clientHeight: Union[int, float]
    scrollWidth: Union[int, float]
    scrollHeight: Union[int, float]


class InteractiveRegion(TypedDict):
    tag_name: str
    role: str
    aria_name: str
    v_scrollable: bool
    rects: List[DOMRectangle]


# Helper Functions
def _get_str(d: Any, k: str) -> str:
    r"""Safely retrieve a string value from a dictionary."""
    if k not in d:
        raise KeyError(f"Missing required key: '{k}'")
    val = d[k]
    if isinstance(val, str):
        return val
    raise TypeError(
        f"Expected a string for key '{k}', but got {type(val).__name__}"
    )


def _get_number(d: Any, k: str) -> Union[int, float]:
    r"""Safely retrieve a number (int or float) from a dictionary"""
    val = d[k]
    if isinstance(val, (int, float)):
        return val
    raise TypeError(
        f"Expected a number (int/float) for key "
        f"'{k}', but got {type(val).__name__}"
    )


def _get_bool(d: Any, k: str) -> bool:
    r"""Safely retrieve a boolean value from a dictionary."""
    val = d[k]
    if isinstance(val, bool):
        return val
    raise TypeError(
        f"Expected a boolean for key '{k}', but got {type(val).__name__}"
    )


def _parse_json_output(
    text: str, logger: Any
) -> Dict[str, Any]:  # Added logger argument
    r"""Extract JSON output from a string."""

    markdown_pattern = r'```(?:json)?\\s*(.*?)\\s*```'
    markdown_match = re.search(markdown_pattern, text, re.DOTALL)
    if markdown_match:
        text = markdown_match.group(1).strip()

    triple_quotes_pattern = r'"""(?:json)?\\s*(.*?)\\s*"""'
    triple_quotes_match = re.search(triple_quotes_pattern, text, re.DOTALL)
    if triple_quotes_match:
        text = triple_quotes_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            # Attempt to fix common JSON issues like unquoted keys or using
            # single quotes
            # This is a simplified fix, more robust parsing might be needed
            # for complex cases
            fixed_text = re.sub(
                r"(\w+)(?=\s*:)", r'"\1"', text
            )  # Add quotes to keys
            fixed_text = fixed_text.replace("'", '"')  # Replace single quotes
            # with double
            # Handle boolean values not in lowercase
            fixed_text = re.sub(
                r':\s*True', ': true', fixed_text, flags=re.IGNORECASE
            )
            fixed_text = re.sub(
                r':\s*False', ': false', fixed_text, flags=re.IGNORECASE
            )
            # Remove trailing commas
            fixed_text = re.sub(r",\s*([\}\]])", r"\1", fixed_text)

            return json.loads(fixed_text)
        except json.JSONDecodeError:
            # Fallback to regex extraction if strict JSON parsing fails
            result = {}
            try:
                # Extract boolean-like values
                bool_pattern = r'"?(\w+)"?\s*:\s*(true|false)'
                for match in re.finditer(bool_pattern, text, re.IGNORECASE):
                    key, value = match.groups()
                    result[key.strip('"')] = value.lower() == "true"

                # Extract string values
                str_pattern = r'"?(\w+)"?\s*:\s*"([^"]*)"'
                for match in re.finditer(str_pattern, text):
                    key, value = match.groups()
                    result[key.strip('"')] = value

                # Extract numeric values
                num_pattern = r'"?(\w+)"?\s*:\s*(-?\d+(?:\.\d+)?)'
                for match in re.finditer(num_pattern, text):
                    key, value = match.groups()
                    try:
                        result[key.strip('"')] = int(value)
                    except ValueError:
                        result[key.strip('"')] = float(value)

                # Extract empty string values
                empty_str_pattern = r'"?(\w+)"?\s*:\s*""'
                for match in re.finditer(empty_str_pattern, text):
                    key = match.group(1)
                    result[key.strip('"')] = ""

                if result:
                    return result

                logger.warning(
                    f"Failed to parse JSON output after multiple attempts: "
                    f"{text}"
                )
                return {}
            except Exception as e:
                logger.warning(
                    f"Error during regex extraction from JSON-like string: {e}"
                )
                return {}


def _reload_image(image: Image.Image) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return Image.open(buffer)


def dom_rectangle_from_dict(rect: Dict[str, Any]) -> DOMRectangle:
    r"""Create a DOMRectangle object from a dictionary."""
    return DOMRectangle(
        x=_get_number(rect, "x"),
        y=_get_number(rect, "y"),
        width=_get_number(rect, "width"),
        height=_get_number(rect, "height"),
        top=_get_number(rect, "top"),
        right=_get_number(rect, "right"),
        bottom=_get_number(rect, "bottom"),
        left=_get_number(rect, "left"),
    )


def interactive_region_from_dict(region: Dict[str, Any]) -> InteractiveRegion:
    r"""Create an :class:`InteractiveRegion` object from a dictionary."""
    typed_rects: List[DOMRectangle] = []
    for rect_data in region[
        "rects"
    ]:  # Renamed rect to rect_data to avoid conflict
        typed_rects.append(dom_rectangle_from_dict(rect_data))

    return InteractiveRegion(
        tag_name=_get_str(region, "tag_name"),
        role=_get_str(region, "role"),
        aria_name=_get_str(region, "aria-name"),
        v_scrollable=_get_bool(region, "v-scrollable"),
        rects=typed_rects,
    )


def visual_viewport_from_dict(viewport: Dict[str, Any]) -> VisualViewport:
    r"""Create a :class:`VisualViewport` object from a dictionary."""
    return VisualViewport(
        height=_get_number(viewport, "height"),
        width=_get_number(viewport, "width"),
        offsetLeft=_get_number(viewport, "offsetLeft"),
        offsetTop=_get_number(viewport, "offsetTop"),
        pageLeft=_get_number(viewport, "pageLeft"),
        pageTop=_get_number(viewport, "pageTop"),
        scale=_get_number(viewport, "scale"),
        clientWidth=_get_number(viewport, "clientWidth"),
        clientHeight=_get_number(viewport, "clientHeight"),
        scrollWidth=_get_number(viewport, "scrollWidth"),
        scrollHeight=_get_number(viewport, "scrollHeight"),
    )


def add_set_of_mark(
    screenshot: Union[bytes, Image.Image, io.BufferedIOBase],
    ROIs: Dict[str, InteractiveRegion],
) -> Tuple[Image.Image, List[str], List[str], List[str]]:
    if isinstance(screenshot, Image.Image):
        return _add_set_of_mark(screenshot, ROIs)

    if isinstance(screenshot, bytes):
        screenshot = io.BytesIO(screenshot)

    image = Image.open(cast(BinaryIO, screenshot))
    comp, visible_rects, rects_above, rects_below = _add_set_of_mark(
        image, ROIs
    )
    image.close()
    return comp, visible_rects, rects_above, rects_below


def _add_set_of_mark(
    screenshot: Image.Image, ROIs: Dict[str, InteractiveRegion]
) -> Tuple[Image.Image, List[str], List[str], List[str]]:
    r"""Add a set of marks to the screenshot.

    Args:
        screenshot (Image.Image): The screenshot to add marks to.
        ROIs (Dict[str, InteractiveRegion]): The regions to add marks to.

    Returns:
        Tuple[Image.Image, List[str], List[str], List[str]]: A tuple
            containing the screenshot with marked ROIs, ROIs fully within the
            images, ROIs located above the visible area, and ROIs located below
            the visible area.
    """
    visible_rects: List[str] = list()
    rects_above: List[str] = list()  # Scroll up to see
    rects_below: List[str] = list()  # Scroll down to see

    fnt = ImageFont.load_default(14)
    base = screenshot.convert("L").convert("RGBA")
    overlay = Image.new("RGBA", base.size)

    draw = ImageDraw.Draw(overlay)
    for r_key in ROIs:  # Renamed r to r_key
        for rect_item in ROIs[r_key]["rects"]:  # Renamed rect to rect_item
            # Empty rectangles
            if (
                not rect_item
                or rect_item["width"] == 0
                or rect_item["height"] == 0
            ):
                continue

            # TODO: add scroll left and right?
            horizontal_center = (rect_item["right"] + rect_item["left"]) / 2.0
            vertical_center = (rect_item["top"] + rect_item["bottom"]) / 2.0
            is_within_horizon = 0 <= horizontal_center < base.size[0]
            is_above_viewport = vertical_center < 0
            is_below_viewport = vertical_center >= base.size[1]

            if is_within_horizon:
                if is_above_viewport:
                    rects_above.append(r_key)
                elif is_below_viewport:
                    rects_below.append(r_key)
                else:  # Fully visible
                    visible_rects.append(r_key)
                    _draw_roi(draw, int(r_key), fnt, rect_item)

    comp = Image.alpha_composite(base, overlay)
    overlay.close()
    return comp, visible_rects, rects_above, rects_below


def _draw_roi(
    draw: ImageDraw.ImageDraw,
    idx: int,
    font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
    # Made Union explicit
    rect: DOMRectangle,
) -> None:
    r"""Draw a ROI on the image.

    Args:
        draw (ImageDraw.ImageDraw): The draw object.
        idx (int): The index of the ROI.
        font (ImageFont.FreeTypeFont | ImageFont.ImageFont): The font.
        rect (DOMRectangle): The DOM rectangle.
    """
    color = _get_random_color(idx)
    text_color = _get_text_color(color)

    roi = ((rect["left"], rect["top"]), (rect["right"], rect["bottom"]))

    label_location = (rect["right"], rect["top"])
    label_anchor = "rb"

    if label_location[1] <= TOP_NO_LABEL_ZONE:
        label_location = (rect["right"], rect["bottom"])
        label_anchor = "rt"

    draw.rectangle(
        roi, outline=color, fill=(color[0], color[1], color[2], 48), width=2
    )

    bbox = draw.textbbox(
        label_location,
        str(idx),
        font=font,
        anchor=label_anchor,
        align="center",
    )
    bbox = (bbox[0] - 3, bbox[1] - 3, bbox[2] + 3, bbox[3] + 3)
    draw.rectangle(bbox, fill=color)

    draw.text(
        label_location,
        str(idx),
        fill=text_color,
        font=font,
        anchor=label_anchor,
        align="center",
    )


def _get_text_color(
    bg_color: Tuple[int, int, int, int],
) -> Tuple[int, int, int, int]:
    r"""Determine the ideal text color (black or white) for contrast.

    Args:
        bg_color: The background color (R, G, B, A).

    Returns:
        A tuple representing black or white color for text.
    """
    luminance = bg_color[0] * 0.3 + bg_color[1] * 0.59 + bg_color[2] * 0.11
    return (0, 0, 0, 255) if luminance > 120 else (255, 255, 255, 255)


def _get_random_color(identifier: int) -> Tuple[int, int, int, int]:
    r"""Generate a consistent random RGBA color based on the identifier.

    Args:
        identifier: The ID used as a seed to ensure color consistency.

    Returns:
        A tuple representing (R, G, B, A) values.
    """
    rnd = random.Random(int(identifier))
    r_val = rnd.randint(0, 255)  # Renamed r to r_val
    g_val = rnd.randint(125, 255)  # Renamed g to g_val
    b_val = rnd.randint(0, 50)  # Renamed b to b_val
    color = [r_val, g_val, b_val]
    # TODO: check why shuffle is needed?
    rnd.shuffle(color)
    color.append(255)
    return cast(Tuple[int, int, int, int], tuple(color))
