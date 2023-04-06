"""
Gradio-based web UI to explore the Camel dataset.
"""

import argparse
import random
from typing import Any, Dict, List, Tuple

import gradio as gr
from loader import load_data


def parse_arguments():
    """ Get command line arguments. """

    parser = argparse.ArgumentParser("Camel data explorer")
    parser.add_argument('--data-path', type=str, default="camel_data/",
                        help='Path to the folder with chat JSONs')
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


def construct_demo(data: Dict[str, Any]):
    """ Build Gradio UI and populate with chat data from JSONs.

    Args:
        data (Dict[str, Any]): Parsed multi-JSON dataset with chats.

    Returns:
        None
    """
    assistant_roles = data['assistant_roles']
    user_roles = data['user_roles']
    assistant_role = random.choice(assistant_roles) \
        if len(assistant_roles) > 0 else ""
    user_role = random.choice(user_roles) if len(user_roles) > 0 else ""
    with gr.Row().style():
        with gr.Column(scale=3):
            assistant_dd = gr.Dropdown(assistant_roles, label="ASSISTANT",
                                       value=assistant_role, interactive=True)
        with gr.Column(scale=3):
            user_dd = gr.Dropdown(user_roles, label="USER", value=user_role,
                                  interactive=True)
        with gr.Column(scale=3):
            gr.Markdown(
                "## CAMEL: Communicative Agents for \"Mind\" Exploration"
                " of Large Scale Language Model Society\n"
                "Github repo: [https://github.com/lightaime/camel]"
                "(https://github.com/lightaime/camel)")
    task_dd = gr.Dropdown([], label="Original task", value="",
                          interactive=True)
    specified_task_ta = gr.TextArea(label="Specified task", lines=2)
    chatbot = gr.Chatbot()

    def roles_dd_change(assistant_role: str, user_role: str) -> Dict:
        """ Update the displayed chat upon inputs change.

        Args:
            assistant_role (str): Assistant dropdown value.
            user_role (str): User dropdown value.

        Returns:
            Dict: New original roles state dictionary.
        """
        matrix = data['matrix']
        if (assistant_role, user_role) in matrix:
            record: Dict[str, Dict] = matrix[(assistant_role, user_role)]
            original_task_options = list(record.keys())
            original_task = original_task_options[0]
        else:
            original_task = "N/A"
            original_task_options = []

        choices = gr.Dropdown.update(choices=original_task_options,
                                     value=original_task, interactive=True)
        return choices

    def build_chat_history(messages: Dict[int, Dict]) -> List[Tuple]:
        """ Structures chatbot contents from the loaded data.

        Args:
            messages (Dict[int, Dict]): Messages loaded from JSON.

        Returns:
            List[Tuple]: Chat history in chatbot UI element format.
        """
        history = []
        curr_qa = (None, None)
        for k in sorted(messages.keys()):
            msg = messages[k]
            content = msg['content']
            if msg['role_type'] == "USER":
                if curr_qa[0] is not None:
                    history.append(curr_qa)
                    curr_qa = (content, None)
                else:
                    curr_qa = (content, None)
            elif msg['role_type'] == "ASSISTANT":
                curr_qa = (curr_qa[0], content)
                history.append(curr_qa)
                curr_qa = (None, None)
            else:
                pass
        return history

    def task_dd_change(assistant_role: str, user_role: str,
                       original_task: str) -> Tuple[str, List]:
        """ Load task details and chatbot history into UI elements.

        Args:
            assistant_role (str): An assistan role.
            user_role (str): An user role.
            original_task (str): The original task.

        Returns:
            Tuple[str, List]: New contents of the specified task
            and chatbot history UI elements.
        """

        matrix = data['matrix']
        if (assistant_role, user_role) in matrix:
            task_dict: Dict[str, Dict] = matrix[(assistant_role, user_role)]
            if original_task in task_dict:
                chat = task_dict[original_task]
                specified_task = chat['specified_task']
                history = build_chat_history(chat['messages'])
            else:
                specified_task = "N/A"
                history = []
        else:
            specified_task = "N/A"
            history = []
        return specified_task, history

    func_args = (roles_dd_change, [assistant_dd, user_dd], task_dd)
    assistant_dd.change(*func_args)
    user_dd.change(*func_args)

    task_dd.change(task_dd_change, [assistant_dd, user_dd, task_dd],
                   [specified_task_ta, chatbot])

    task_dd_update_dict = roles_dd_change(assistant_dd.value, user_dd.value)
    task_dd.choices = task_dd_update_dict['choices']
    task_dd.value = task_dd_update_dict['value']

    specified_task, chatbot_history = task_dd_change(assistant_dd.value,
                                                     user_dd.value,
                                                     task_dd.value)
    specified_task_ta.value = specified_task
    chatbot.value = chatbot_history


if __name__ == "__main__":
    """ Entry point. """

    args = parse_arguments()

    print("Loading the dataset...")
    data = load_data(args.data_path)
    print("Dataset is loaded")

    print("Getting Data Explorer web server online...")

    with gr.Blocks() as demo:
        construct_demo(data)

    demo.queue(args.concurrency_count)
    demo.launch(share=args.share, inbrowser=args.inbrowser,
                server_name="0.0.0.0", server_port=args.server_port)

    print("Exiting.")
