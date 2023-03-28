"""
Gradio-based web app Agents that uses OpenAI API to generate
a chat between collaborative agents.
"""

import argparse
import gradio as gr
import os
import random
import re
import time
from colorama import Fore
from typing import List, Dict, Any, Tuple, Union, Optional
import openai
import openai.error
import tenacity
from dataclasses import dataclass

from camel.agent import RolePlaying
from camel.message import ChatMessage, AssistantChatMessage, UserChatMessage

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

ChatBotHistory = List[Tuple[Optional[str], Optional[str]]]


@dataclass
class State:
    session: Optional[RolePlaying]
    chat: ChatBotHistory
    saved_assistant_msg: AssistantChatMessage


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
        '--concurrency-count', type=int, default=1,
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


def role_playing_start(
        state, assistant: str, user: str,
        original_task: str) -> Union[Dict, Tuple[State, str, str]]:
    if state.session is not None:
        return {}  # may fail
    try:
        session = RolePlaying(assistant, user, original_task,
                              with_task_specify=True, with_task_planner=True)
        print(Fore.GREEN +
              f"AI Assistant sys message:\n{session.assistant_sys_msg}\n")
        print(Fore.BLUE + f"AI User sys message:\n{session.user_sys_msg}\n")

        print(Fore.YELLOW + f"Original task prompt:\n{original_task}\n")
        print(Fore.CYAN +
              f"Specified task prompt:\n{session.specified_task_prompt}\n")
        print(Fore.MAGENTA +
              f"Planned task prompt:\n{session.planned_task_prompt}\n")
        print(Fore.RED + f"Final task prompt:\n{session.task_prompt}\n")
        state.session = session
    except (openai.error.RateLimitError, tenacity.RetryError) as ex:
        result = (state, str(ex), "")
    else:
        specified_task_prompt = session.specified_task_prompt \
            if session.specified_task_prompt is not None else ""
        planned_task_prompt = session.planned_task_prompt \
            if session.planned_task_prompt is not None else ""
        result = (state, specified_task_prompt, planned_task_prompt)
    return result


def role_playing_chat_init(state) -> \
        Union[Dict, Tuple[State, ChatBotHistory]]:

    session = state.session
    if session is None:
        return {}  # may fail
    try:
        assistant_msg, _ = session.init_chat()
        assistant_msg: AssistantChatMessage
    except (openai.error.RateLimitError, tenacity.RetryError) as ex:
        state.session = None
        return state, state.chat

    print(Fore.GREEN + f"AI Assistant:\n\n{assistant_msg.content}\n\n")
    state.saved_assistant_msg = assistant_msg

    return state, state.chat


# WORKAROUND: do not add type hinst for session and chatbot_histoty
def role_playing_chat_cont(state, num_messages: float) -> \
        Tuple[State, ChatBotHistory]:

    session = state.session
    if session is None:
        return state, state.chat

    num_messages = int(num_messages)

    if state.saved_assistant_msg is None:
        state.session = None
        return state, state.chat

    try:
        assistant_msg, user_msg = session.step(state.saved_assistant_msg)
    except (openai.error.RateLimitError, tenacity.RetryError) as ex:
        state.session = None
        return state, state.chat

    u_msg = user_msg[0]
    a_msg = assistant_msg[0]

    state.saved_assistant_msg = a_msg

    print(Fore.BLUE + f"AI User:\n\n{u_msg.content}\n\n")
    print(Fore.GREEN + f"AI Assistant:\n\n{a_msg.content}\n\n")
    state.chat.append([None, u_msg.content])
    state.chat.append([a_msg.content, None])

    if len(state.chat) > num_messages:
        state.session = None

    if "CAMEL_TASK_DONE" in a_msg.content or \
            "CAMEL_TASK_DONE" in u_msg.content:
        state.session = None

    return state, state.chat


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
    session_state = gr.State(State(None, [], None))

    universal_task_bn.click(lambda: "Help me to do my job", None,
                            original_task_ta)

    # def start_chat(state):  # 'State'
    #     if state.int_val is not None:
    #         return {}
    #     state.int_val = 0
    #     state.chat = []
    #     print("start_chat", state)
    #     return state

    # def next_msg(state):  # 'State'
    #     print("next_msg", state)
    #     if state.int_val is None:
    #         return {
    #             chatbot: state.chat
    #         }  # must return something otherwise gradio does not work
    #     state.chat.append((None, f"mess {state.int_val} {time.time()}")\
    #         if state.int_val % 2 == 0 else (f"mess {state.int_val} {time.time()}", None))
    #     state.int_val = state.int_val + 1 if state.int_val < 6 else None
    #     time.sleep(0.5)
    #     return {session_state: state, chatbot: state.chat}

    # start_bn.click(start_chat, session_state, session_state, queue=False)

    # .then(lambda state: str(state), session_state, task_prompt_ta, queue=False)
    # .then(next_msg, session_state, [session_state, chatbot], queue=False)
    # .then(next_msg, session_state, [session_state, chatbot], queue=False) \
    # .then(next_msg, session_state, [session_state, chatbot], queue=False) \
    # .then(next_msg, session_state, [session_state, chatbot], queue=False) \
    # .then(next_msg, session_state, [session_state, chatbot], queue=False)

    # demo.load(next_msg, session_state, [session_state, chatbot], every=0.5)

    start_bn.click(role_playing_start,
                   [session_state, assistant_ta, user_ta, original_task_ta],
                   [session_state, specified_task_ta, task_prompt_ta],
                   queue=False) \
            .then(role_playing_chat_init, session_state, [session_state, chatbot]) \
            .then(role_playing_chat_cont, [session_state, num_messages_sl], [session_state, chatbot]) \
            .then(role_playing_chat_cont, [session_state, num_messages_sl], [session_state, chatbot]) \
            .then(role_playing_chat_cont, [session_state, num_messages_sl], [session_state, chatbot])

    # demo.load(role_playing_chat, [session_state, num_messages_sl],
    #           [session_state, chatbot], every=0.5)

    # clear_bn.click(lambda state: {specified_task_ta: "READ " + str(state)},
    #                session_state, [specified_task_ta, chatbot])

    clear_bn.click(lambda: ("", []), None, [specified_task_ta, chatbot])

    assistant_dd.change(lambda dd: dd, assistant_dd, assistant_ta)
    user_dd.change(lambda dd: dd, user_dd, user_ta)

    demo.load(lambda dd: dd, assistant_dd, assistant_ta)
    demo.load(lambda dd: dd, user_dd, user_ta)


if __name__ == "__main__":
    """ Entry point. """

    args = parse_arguments()

    print("Getting Agents web server online...")

    os.chdir(REPO_ROOT)

    with gr.Blocks() as demo:
        construct_demo(args.api_key)

    #
    demo.queue(args.concurrency_count) \
        .launch(share=args.share, inbrowser=args.inbrowser,
                server_name="0.0.0.0", server_port=args.server_port,
                debug=True)

    print("Exiting.")
