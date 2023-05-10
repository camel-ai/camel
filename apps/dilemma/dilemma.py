"""
Gradio-based web UI to explore the Camel dataset.
"""

import argparse
import random
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
from database_connection import DatabaseConnection
from tqdm import tqdm

from apps.common.auto_zip import AutoZip


def parse_arguments():
    """ Get command line arguments. """

    parser = argparse.ArgumentParser("Dilemma tool")
    parser.add_argument('--left-path', type=str, default=None,
                        help='Path to ZIP file containing TXTs (left)')
    parser.add_argument('--right-path', type=str, default=None,
                        help='Path to ZIP file containing TXTs (right)')
    parser.add_argument('--no-db', dest='no_db', action='store_true',
                        help="Set in development environment")
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


def load_dataset(left_path: str, right_path: str) -> Dict[str, Dict[str, str]]:
    datasets = dict()
    for zip_path, name in ((left_path, 'left'), (right_path, 'right')):
        zip_inst = AutoZip(zip_path, ext=".txt")
        text_dict = zip_inst.as_dict(include_zip_name=True)
        datasets[name] = text_dict
    return datasets


def construct_ui(blocks, datasets: Dict[str, Dict[str, str]],
                 has_connection: bool = True):
    """ Build Gradio UI and populate with texts from TXTs.

    Args:
        blocks: Gradio blocks
        datasets: Parsed multi-TXT dataset.
        has_connection (bool): if the DB connection exists.

    Returns:
        None
    """

    db_conn = DatabaseConnection() if has_connection else None

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

    state_st = gr.State(
        dict(left=dict(name="a", text="at"), right=dict(name="b", text="bt")))

    def load_random(state):
        for side in ('left', 'right'):
            items = random.sample(datasets[side].items(), 1)
            if len(items) > 0:
                name, text = items[0]
            else:
                name, text = "ERROR_NAME", "ERROR_TEXT"
            state[side] = dict(name=name, text=text)
        return state, state['left']['text'], state['right']['text']

    def record(choice: str, state):
        assert choice in {'left', 'draw', 'right'}
        left_name = state['left']['name']
        right_name = state['right']['name']
        print(choice, left_name, right_name)
        if db_conn is not None:
            db_conn.add_record(choice, left_name, right_name)

    left_better_bn.click(partial(record, 'left'), state_st, None) \
        .then(load_random, state_st, [state_st, left_md, right_md])

    not_sure_bn.click(partial(record, 'draw'), state_st, None) \
        .then(load_random, state_st, [state_st, left_md, right_md])

    right_better_bn.click(partial(record, 'right'), state_st, None) \
        .then(load_random, state_st, [state_st, left_md, right_md])

    blocks.load(load_random, state_st, [state_st, left_md, right_md])


def construct_blocks(left_path: str, right_path: str, has_connection: bool):
    """ Construct Blocs app but do not launch it.

    Args:
        left_path (str): Path to the ZIP dataset with TXTs inside (left).
        right_path (str): Path to the ZIP dataset with TXTs inside (right).

    Returns:
        gr.Blocks: Blocks instance.
    """

    print("Loading the dataset...")
    dataset = load_dataset(left_path, right_path)
    print("Dataset is loaded")

    print("Getting Dilemma web server online...")

    with gr.Blocks() as blocks:
        construct_ui(blocks, dataset, has_connection)

    return blocks


def main():
    """ Entry point. """

    args = parse_arguments()

    blocks = construct_blocks(args.left_path, args.right_path, not args.no_db)

    blocks.queue(args.concurrency_count) \
          .launch(share=args.share, inbrowser=args.inbrowser,
                  server_name=args.server_name, server_port=args.server_port)

    print("Exiting.")


if __name__ == "__main__":
    main()
