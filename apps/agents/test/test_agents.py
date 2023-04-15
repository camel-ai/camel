import unittest

import gradio as gr

from apps.agents.agents import construct_ui


class TestInterface(unittest.TestCase):
    def test_ui(self):
        with gr.Blocks() as blocks:
            construct_ui(blocks, None)


if __name__ == '__main__':
    unittest.main()
