import unittest

import gradio as gr

from apps.agents.agents import construct_blocks


class TestAgents(unittest.TestCase):
    def test_construct_blocks(self):
        blocks = construct_blocks(None)
        self.assertIsInstance(blocks, gr.Blocks)


if __name__ == '__main__':
    unittest.main()
