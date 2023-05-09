"""
Gradio-based web UI to explore the Camel dataset.
"""

import argparse
import random
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
from database_connection import DatabaseConnection


def parse_arguments():
    """ Get command line arguments. """

    parser = argparse.ArgumentParser("Dilemma tool")
    parser.add_argument(
        '--data-path', type=str, default=None,
        help='Path to the folder with ZIP datasets containing JSONs')
    parser.add_argument('--share', type=bool, default=False,
                        help='Expose the web UI to Gradio')
    parser.add_argument(
        '--server-name', type=str, default="0.0.0.0",
        help='localhost for local, 0.0.0.0 (default) for public')
    parser.add_argument('--server-port', type=int, default=8080,
                        help='Port ot run the web page on')
    parser.add_argument('--inbrowser', type=bool, default=False,
                        help='Open the web UI in the default browser on lunch')
    parser.add_argument(
        '--concurrency-count', type=int, default=10,
        help='Number if concurrent threads at Gradio websocket queue. ' +
        'Increase to serve more requests but keep an eye on RAM usage.')
    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        print("Unknown args: ", unknown)
    return args


def construct_ui(blocks, dataset: Any):
    """ Build Gradio UI and populate with texts from TXTs.

    Args:
        blocks: Gradio blocks
        datasets (TODO): Parsed multi-TXT dataset.

    Returns:
        None
    """

    db_conn = DatabaseConnection()

    gr.Markdown("## Dilemma app")
    with gr.Row():
        with gr.Column(scale=1):
            left_md = gr.Markdown("LOREM\n" "IPSUM\n")
        with gr.Column(scale=1):
            right_md = gr.Markdown("LOREM 2\n" "IPSUM 2\n")
    with gr.Row():
        left_better_bn = gr.Button("Left is better")
        not_sure_bn = gr.Button("Not sure")
        right_better_bn = gr.Button("Right is better")

    def load_random():
        return (f"txt {random.randint(1, 100)}",
                f"txt {random.randint(1, 100)}")

    def record(choice: str, left: str, right: str):
        assert choice in {'left', 'draw', 'right'}
        print(choice, left, right)
        db_conn.add_record(choice, left, right)

    left_better_bn.click(partial(record, 'left'), [left_md, right_md], None) \
        .then(load_random, None, [left_md, right_md])

    not_sure_bn.click(partial(record, 'draw'), [left_md, right_md], None) \
        .then(load_random, None, [left_md, right_md])

    right_better_bn.click(partial(record, 'right'), [left_md, right_md], None) \
        .then(load_random, None, [left_md, right_md])

    blocks.load(load_random, None, [left_md, right_md])


def construct_blocks(data_path: str):
    """ Construct Blocs app but do not launch it.

    Args:
        data_path (str): Path to the ZIP dataset with TXTs inside.

    Returns:
        gr.Blocks: Blocks instance.
    """

    print("Loading the dataset...")
    # dataset = load_dataset(data_path)
    dataset = None
    print("Dataset is loaded")

    print("Getting Dilemma web server online...")

    with gr.Blocks() as blocks:
        construct_ui(blocks, dataset)

    return blocks


def main():
    """ Entry point. """

    args = parse_arguments()

    blocks = construct_blocks(args.data_path)

    blocks.queue(args.concurrency_count) \
          .launch(share=args.share, inbrowser=args.inbrowser,
                  server_name=args.server_name, server_port=args.server_port)

    print("Exiting.")


if __name__ == "__main__":
    main()
