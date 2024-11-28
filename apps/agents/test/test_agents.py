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
import gradio as gr
import pytest

from apps.agents.agents import (
    State,
    cleanup_on_launch,
    construct_blocks,
    parse_arguments,
    role_playing_chat_cont,
    role_playing_chat_init,
    role_playing_start,
    stop_session,
)


def test_construct_blocks():
    blocks = construct_blocks(None)
    assert isinstance(blocks, gr.Blocks)


def test_utils():
    args = parse_arguments()
    assert args is not None


@pytest.mark.model_backend
def test_session():
    for society_name in ("AI Society", "Code"):
        state = State.empty()

        state, _, _ = cleanup_on_launch(state)

        if society_name == "AI Society":
            assistant = "professor"
            user = "PhD student"
            original_task = "Recommend AI conferences to publish a paper"
        else:
            assistant = "JavaScript"
            user = "Sociology"
            original_task = "Develop a poll app"

        max_messages = 10
        with_task_specifier = False
        word_limit = 50
        language = "English"
        state, specified_task_prompt, planned_task_upd, chat, progress_upd = (
            role_playing_start(
                state,
                society_name,
                assistant,
                user,
                original_task,
                max_messages,
                with_task_specifier,
                word_limit,
                language,
            )
        )

        assert state.session is not None

        state, chat, progress_update = role_playing_chat_init(state)

        assert state.session is not None

        for _ in range(5):
            state, chat, progress_update, start_bn_update = (
                role_playing_chat_cont(state)
            )

        state, _, _ = stop_session(state)

        assert state.session is None
