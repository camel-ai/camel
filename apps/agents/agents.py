"""
Gradio-based web app Agents that uses OpenAI API to generate
a chat between collaborative agents.
"""

import argparse
import gradio as gr
import os
import random
import re
from colorama import Fore
from typing import List, Dict, Any, Tuple
import openai
import tenacity

from camel.agent import RolePlaying

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))


def parse_arguments():
    """ Get command line arguments. """

    parser = argparse.ArgumentParser("Camel data explorer")
    parser.add_argument('--api-key', type=str, default=None,
                        help='OpenAI API key')
    parser.add_argument('--share', type=bool, default=False,
                        help='Expose the web UI to Gradio')
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


def load_roles(path):
    assert os.path.exists(path)
    roles = []
    with open(path, "r") as f:
        lines = f.readlines()
        for line in lines:
            match = re.search("^\d+\.\s*(.+)\n*$", line)
            if match:
                role = match.group(1)
                roles.append(role)
            else:
                print("Warning: no match")
    return roles


def construct_chatbot_history(
        plain: List[Dict[str, str]]) -> List[Tuple[str, str]]:

    history = []
    curr_qa = (None, None)
    for msg in plain:
        content = msg['message']
        if msg['role'] == "user":
            if curr_qa[0] is not None:
                history.append(curr_qa)
                curr_qa = (content, None)
            else:
                curr_qa = (content, None)
        elif msg['role'] == "assistant":
            curr_qa = (curr_qa[0], content)
            history.append(curr_qa)
            curr_qa = (None, None)
        else:
            pass
    return history


def role_playing_mayexcept(assistant: str, user: str, original_task: str,
                           num_messages: float):
    num_messages = int(num_messages)

    role_play_session = RolePlaying(assistant, user, original_task,
                                    with_task_specify=True,
                                    with_task_planner=True)
    print(
        Fore.GREEN +
        f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n")
    print(Fore.BLUE +
          f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{original_task}\n")
    print(
        Fore.CYAN +
        f"Specified task prompt:\n{role_play_session.specified_task_prompt}\n")
    print(Fore.MAGENTA +
          f"Planned task prompt:\n{role_play_session.planned_task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    assistant_msg, _ = role_play_session.init_chat()
    flat_history: List[Dict[str, str]] = []
    for _ in range(num_messages):
        assistant_msg, user_msg = role_play_session.step(assistant_msg)
        print(Fore.BLUE + f"AI User:\n\n{user_msg.content}\n\n")
        print(Fore.GREEN + f"AI Assistant:\n\n{assistant_msg.content}\n\n")
        flat_history.append(dict(role='user', message=user_msg.content))
        flat_history.append(
            dict(role='assistant', message=assistant_msg.content))

        if "<CAMEL_TASK_DONE>" in user_msg.content:
            break
    chatbot_history = construct_chatbot_history(flat_history)
    return role_play_session.specified_task_prompt, \
        role_play_session.planned_task_prompt, chatbot_history


def role_playing(*args):
    try:
        result = role_playing_mayexcept(*args)
    except (openai.error.RateLimitError, tenacity.RetryError) as ex:
        result = str(ex), "", []
    return result


def construct_demo(api_key: str) -> None:
    """ Build Gradio UI and populate with topics.

    Args:
        api_key (str): OpenAI API key.

    Returns:
        None
    """

    openai.api_key = api_key

    assistant_role_path = \
        os.path.join(REPO_ROOT, "data/ai_society/assistant_roles.txt")
    user_role_path = \
        os.path.join(REPO_ROOT, "data/ai_society/user_roles.txt")

    assistant_roles = load_roles(assistant_role_path)
    user_roles = load_roles(user_role_path)

    assistant_role = "Python Programmer"
    user_role = "Stock Trader"

    default_task = "Develop a trading bot for the stock market"

    with gr.Row():
        with gr.Column(scale=1):
            assistant_dd = gr.Dropdown(assistant_roles,
                                       label="Example assistant roles",
                                       value=assistant_role, interactive=True)
            assistant_ta = gr.TextArea(label="Assistant role (EDIT ME)",
                                       lines=1, interactive=True)
        with gr.Column(scale=1):
            user_dd = gr.Dropdown(user_roles, label="Example user roles",
                                  value=user_role, interactive=True)
            user_ta = gr.TextArea(label="User role (EDIT ME)", lines=1,
                                  interactive=True)
        with gr.Column(scale=1):
            gr.Markdown(
                "## CAMEL: Communicative Agents for \"Mind\" Extraction"
                " from Large Scale Language Model Society\n"
                "Github repo: [https://github.com/lightaime/camel]"
                "(https://github.com/lightaime/camel)")
    with gr.Row():
        with gr.Column(scale=9):
            original_task_ta = gr.TextArea(
                label=
                "Original task that the user gives to the assistant (EDIT ME)",
                value=default_task, lines=1, interactive=True)
        with gr.Column(scale=1):
            universal_task_bn = gr.Button("Insert universal task")
    with gr.Row():
        with gr.Column():
            num_messages_sl = gr.Slider(
                minimum=1, maximum=20, step=1, value=2, interactive=True,
                label="Number of message pairs to generate")
        with gr.Column():
            start_bn = gr.Button("Make agents chat [takes time]")
        with gr.Column():
            clear_bn = gr.Button("Clear chat")
    specified_task_ta = gr.TextArea(
        label="Elaborate task description given to the assistant"
        " based on the original (simplistic) task", lines=1, interactive=False)
    task_prompt_ta = gr.TextArea(label="Planned task prompt", lines=1,
                                 interactive=False)
    chatbot = gr.Chatbot()

    universal_task_bn.click(lambda: "Help me to do my job", None,
                            original_task_ta)

    start_bn.click(role_playing,
                   [assistant_ta, user_ta, original_task_ta, num_messages_sl],
                   [specified_task_ta, task_prompt_ta, chatbot])

    clear_bn.click(lambda: ("", []), None, [specified_task_ta, chatbot])

    assistant_dd.change(lambda dd: dd, assistant_dd, assistant_ta)
    user_dd.change(lambda dd: dd, user_dd, user_ta)

    assistant_ta.value = assistant_dd.value
    user_ta.value = user_dd.value


if __name__ == "__main__":
    """ Entry point. """

    args = parse_arguments()

    print("Getting Agents web server online...")

    os.chdir(REPO_ROOT)

    with gr.Blocks() as demo:
        construct_demo(args.api_key)

    demo.queue(args.concurrency_count)
    demo.launch(share=args.share, inbrowser=args.inbrowser,
                server_name="0.0.0.0", server_port=args.server_port)

    print("Exiting.")
