from typing import Any, Dict, List

from colorama import Fore

from camel.messages import ChatMessage
from camel.utils import print_text_animated


class Human:
    r"""A class representing a human user.

    Args:
        name (str): The name of the human user.
            (default: :obj:`"Kill Switch Engineer"`).
        menu_color (Any): The color of the menu options displayed to the user.
            (default: :obj:`Fore.MAGENTA`)

    Attributes:
        name (str): The name of the human user.
        menu_color (Any): The color of the menu options displayed to the user.
        input_button (str): The text displayed for the input button.
        kill_button (str): The text displayed for the kill button.
        options_dict (Dict[str, str]): A dictionary containing the options
            displayed to the user.
    """

    def __init__(self, name: str = "Kill Switch Engineer",
                 menu_color: Any = Fore.MAGENTA) -> None:
        self.name = name
        self.menu_color = menu_color
        self.input_button = f"Input by {self.name}."
        self.kill_button = "Stop!!!"
        self.options_dict: Dict[str, str] = dict()

    def display_options(self, messages: List[ChatMessage]) -> None:
        r"""Displays the options to the user.

        Args:
            messages (List[ChatMessage]): A list of `ChatMessage` objects.

        Returns:
            None
        """
        options = [message.content for message in messages]
        options.append(self.input_button)
        options.append(self.kill_button)
        print_text_animated(
            self.menu_color + "\n> Proposals from "
            f"{messages[0].role_name} ({messages[0].role_type}). "
            "Please choose an option:\n")
        for index, option in enumerate(options):
            print_text_animated(
                self.menu_color +
                f"\x1b[3mOption {index + 1}:\n{option}\x1b[0m\n")
            self.options_dict[str(index + 1)] = option

    def get_input(self) -> str:
        r"""Gets the input from the user.

        Returns:
            str: The user's input.
        """
        while True:
            human_input = input(
                self.menu_color +
                f"Please enter your choice ([1-{len(self.options_dict)}]): ")
            print("\n")
            if human_input in self.options_dict:
                break
            print_text_animated(self.menu_color +
                                "\n> Invalid choice. Please try again.\n")

        return human_input

    def parse_input(self, human_input: str,
                    meta_chat_message: ChatMessage) -> ChatMessage:
        r"""Parses the user's input and returns a `ChatMessage` object.

        Args:
            human_input (str): The user's input.
            meta_chat_message (ChatMessage): A `ChatMessage` object.

        Returns:
            ChatMessage: A `ChatMessage` object.
        """
        if self.options_dict[human_input] == self.input_button:
            meta_chat_message.content = input(self.menu_color +
                                              "Please enter your message: ")
            return meta_chat_message
        elif self.options_dict[human_input] == self.kill_button:
            exit(self.menu_color + f"Killed by {self.name}.")
        else:
            meta_chat_message.content = self.options_dict[human_input]
            return meta_chat_message

    def step(self, messages: List[ChatMessage]) -> ChatMessage:
        r"""Performs one step of the conversation by displaying options to the
        user, getting their input, and parsing their choice.

        Args:
            messages (List[ChatMessage]): A list of ChatMessage objects.

        Returns:
            ChatMessage: A `ChatMessage` object representing the user's choice.
        """
        meta_chat_message = ChatMessage(
            role_name=messages[0].role_name,
            role_type=messages[0].role_type,
            meta_dict=messages[0].meta_dict,
            role=messages[0].role,
            content="",
        )
        self.display_options(messages)
        human_input = self.get_input()
        return self.parse_input(human_input, meta_chat_message)
