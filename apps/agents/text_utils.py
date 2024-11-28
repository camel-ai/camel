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
import re


def split_markdown_code(string: str) -> str:
    """Split a multiline block of markdown code (triple-quotes) into
    line-sized sub-blocks to make newlines stay where they belong.
    This transformation is a workaround to a known Gradio bug:
    https://github.com/gradio-app/gradio/issues/3531

    Args:
        string (str): markdown string incompatible with gr.Chatbot

    Returns:
        str: markdown string which is compatible with gr.Chatbot
    """
    substr_list = string.split("```")
    out = []
    for i_subs, subs in enumerate(substr_list):
        if i_subs % 2 == 0:  # outsize code, don't change
            out.append(subs)
        else:  # inside code
            br_done = re.sub(r"<br>", "\n", subs)

            def repl(m):
                return "```{}```".format(m.group(0))

            new_subs = re.sub(r"\n+", repl, br_done)
            out.append(new_subs)
    out_str = "```".join(out)
    out_str_cleanup = re.sub(r"``````", "", out_str)
    return out_str_cleanup
