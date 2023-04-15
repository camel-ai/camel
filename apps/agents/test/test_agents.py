import unittest

import gradio as gr

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


class TestAgents(unittest.TestCase):
    def test_construct_blocks(self):
        blocks = construct_blocks(None)
        self.assertIsInstance(blocks, gr.Blocks)

    def test_utils(self):
        args = parse_arguments()
        self.assertIsNotNone(args)

    def test_session(self):
        state = State.empty()

        state, _, _ = cleanup_on_launch(state)

        assistant = "professor"
        user = "PhD student"
        original_task = "Recommend AI conferences to publish a paper"
        max_messages = 10
        with_task_specifier = False
        word_limit = 50
        state, specified_task_prompt, planned_task_upd, chat, progress_upd = \
            role_playing_start(state, assistant, user, original_task,
                               max_messages, with_task_specifier, word_limit)

        self.assertIsNotNone(state.session)

        state, chat, progress_update = \
            role_playing_chat_init(state)

        self.assertIsNotNone(state.session)

        for _ in range(5):
            state, chat, progress_update, start_bn_update =\
                role_playing_chat_cont(state)

        state, _, _ = stop_session(state)

        self.assertIsNone(state.session)


if __name__ == '__main__':
    unittest.main()
