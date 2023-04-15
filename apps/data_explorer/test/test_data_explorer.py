import os
import unittest
import urllib.request

import gradio as gr

from apps.data_explorer.data_explorer import construct_blocks, parse_arguments
from apps.data_explorer.loader import REPO_ROOT


class TestDataExplorer(unittest.TestCase):
    def test_app(self):
        test_data_url = ("https://storage.googleapis.com/"
                         "camel-bucket/datasets/test/DATA.zip")
        data_dir = os.path.join(REPO_ROOT, "datasets_test")
        test_file_path = os.path.join(data_dir,
                                      os.path.split(test_data_url)[1])
        os.makedirs(data_dir, exist_ok=True)
        urllib.request.urlretrieve(test_data_url, test_file_path)

        blocks = construct_blocks(data_dir, None)

        self.assertIsInstance(blocks, gr.Blocks)

    def test_utils(self):
        args = parse_arguments()
        self.assertIsNotNone(args)


if __name__ == '__main__':
    unittest.main()
