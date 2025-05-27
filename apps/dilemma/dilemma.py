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
"""
Gradio-based web UI to select between two
options and save the answers to a database.
"""

import argparse
import json
import random
from functools import partial
from typing import Dict

import gradio as gr
from database_connection import DatabaseConnection

from apps.common.auto_zip import AutoZip
from camel.logger import get_logger

logger = get_logger(__name__)


def parse_arguments():
    """Get command line arguments."""

    parser = argparse.ArgumentParser("Dilemma tool")
    parser.add_argument(
        '--data-path',
        type=str,
        default=None,
        help='Path to ZIP file containing JSONs',
    )
    parser.add_argument(
        '--no-db',
        dest='no_db',
        action='store_true',
        help="Set in development environment",
    )
    parser.add_argument(
        '--share', type=bool, default=False, help='Expose the web UI to Gradio'
    )
    parser.add_argument(
        '--server-name',
        type=str,
        default="0.0.0.0",
        help='localhost for local, 0.0.0.0 (default) for public',
    )
    parser.add_argument(
        '--server-port',
        type=int,
        default=8080,
        help='Port to run the web page on',
    )
    parser.add_argument(
        '--inbrowser',
        type=bool,
        default=False,
        help='Open the web UI in the default browser on lunch',
    )
    parser.add_argument(
        '--concurrency-count',
        type=int,
        default=10,
        help='Number if concurrent threads at Gradio websocket queue. '
        + 'Increase to serve more requests but keep an eye on RAM usage.',
    )
    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        logger.warning("Unknown args: ", unknown)
    return args


def load_dataset(data_path: str) -> Dict[str, Dict[str, str]]:
    zip_inst = AutoZip(data_path, ext=".json")
    text_dict = zip_inst.as_dict(include_zip_name=True)
    res_dict = {}
    for path, json_str in text_dict.items():
        js = json.loads(json_str)
        if 'summary' not in js:
            continue
        if 'gpt_solution' not in js:
            continue
        if 'specified_task' not in js:
            continue
        res_dict[path] = dict(
            summary=js['summary'],
            gpt_solution=js['gpt_solution'],
            specified_task=js['specified_task'],
        )
    return res_dict


def construct_ui(
    blocks, dataset: Dict[str, Dict[str, str]], has_connection: bool = True
):
    """Build Gradio UI and populate with texts from JSONs.

    Args:
        blocks: Gradio blocks
        dataset: Parsed multi-JSON dataset.
        has_connection (bool): if the DB connection exists.

    Returns:
        None
    """

    db_conn = DatabaseConnection() if has_connection else None

    gr.Markdown("## Dilemma app")
    specified_task_ta = gr.TextArea(
        label="Specified task prompt", lines=1, interactive=False
    )
    with gr.Row():
        left_better_bn = gr.Button("Left is better")
        not_sure_bn = gr.Button("Not sure")
        right_better_bn = gr.Button("Right is better")
    with gr.Row():
        with gr.Column(scale=1):
            left_md = gr.Markdown("LOREM\nIPSUM\n")
        with gr.Column(scale=1):
            right_md = gr.Markdown("LOREM 2\nIPSUM 2\n")

    state_st = gr.State(
        dict(
            name="n",
            left=dict(who="a", text="at"),
            right=dict(who="b", text="bt"),
            specified_task="st",
        )
    )

    def load_random(state):
        items = random.sample(dataset.items(), 1)
        if len(items) > 0:
            name, rec = items[0]
        else:
            name, rec = (
                "ERROR_NAME",
                dict(summary="ERROR_TEXT", gpt_solution="ERROR_TEXT"),
            )
        specified_task = rec['specified_task']
        lst = [
            (k, v) for k, v in rec.items() if k in {'summary', 'gpt_solution'}
        ]
        random.shuffle(lst)
        state = dict(
            name=name,
            left=dict(who=lst[0][0], text=lst[0][1]),
            right=dict(who=lst[1][0], text=lst[1][1]),
            specified_task=specified_task,
        )
        return (
            state,
            state['left']['text'],
            state['right']['text'],
            specified_task,
        )

    def record(choice: str, state):
        assert choice in {'left', 'draw', 'right'}
        if choice == 'draw':
            who_is_better = 'none'
        else:
            who_is_better = state[choice]['who']
        name = state['name']
        logger.info(
            "choice=", choice, "who_is_better=", who_is_better, "name=", name
        )
        if db_conn is not None:
            db_conn.add_record(name, who_is_better)

    updated_controls = [state_st, left_md, right_md, specified_task_ta]

    left_better_bn.click(partial(record, 'left'), state_st, None).then(
        load_random, state_st, updated_controls
    )

    not_sure_bn.click(partial(record, 'draw'), state_st, None).then(
        load_random, state_st, updated_controls
    )

    right_better_bn.click(partial(record, 'right'), state_st, None).then(
        load_random, state_st, updated_controls
    )

    blocks.load(load_random, state_st, updated_controls)


def construct_blocks(data_path: str, has_connection: bool):
    """Construct Blocks app but do not launch it.

    Args:
        data_path (str): Path to the ZIP dataset with JOSNs inside.

    Returns:
        gr.Blocks: Blocks instance.
    """

    logger.info("Loading the dataset...")
    dataset = load_dataset(data_path)
    logger.info("Dataset is loaded")

    logger.info("Getting Dilemma web server online...")

    with gr.Blocks() as blocks:
        construct_ui(blocks, dataset, has_connection)

    return blocks


def main():
    """Entry point."""

    args = parse_arguments()

    blocks = construct_blocks(args.data_path, not args.no_db)

    blocks.queue(args.concurrency_count).launch(
        share=args.share,
        inbrowser=args.inbrowser,
        server_name=args.server_name,
        server_port=args.server_port,
    )

    logger.info("Exiting.")


if __name__ == "__main__":
    main()
