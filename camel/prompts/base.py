from typing import Any, Dict, Set

from camel.typing import RoleType
from camel.utils import get_prompt_template_key_words


class TextPrompt(str):
    r"""A class that represents a text prompt. The TextPrompt class extends
    the built-in str class to provide a property for retrieving the set of
    key words in the prompt.

    Attributes:
        key_words (set): A set of strings representing the key words in the
            prompt.
    """

    @property
    def key_words(self) -> Set[str]:
        r"""Returns a set of strings representing the key words in the prompt.
        """
        return get_prompt_template_key_words(self)

    def format(self, *args: Any, **kwargs: Any) -> 'TextPrompt':
        r"""Overrides the built-in :obj:`str.format` method to allow for
        default values in the format string. This is used to allow formatting
        the partial string.

        Args:
            *args (Any): Variable length argument list.
            **kwargs (Any): Arbitrary keyword arguments.

        Returns:
            TextPrompt: A new TextPrompt object with the format string replaced
                with the formatted string.
        """
        default_kwargs = {key: '{' + f'{key}' + '}' for key in self.key_words}
        default_kwargs.update(kwargs)
        return TextPrompt(super().format(*args, **default_kwargs))


# flake8: noqa :E501
class TextPromptDict(Dict[Any, TextPrompt]):
    r"""A dictionary class that maps from key to :obj:`TextPrompt` object.
    """
    EMBODIMENT_PROMPT = TextPrompt(
        """You are the physical embodiment of the {role} who is working on solving a task: {task}.
You can do things in the physical world including browsing the Internet, reading documents, drawing images, creating videos, executing code and so on.
Your job is to perform the physical actions necessary to interact with the physical world.
You will receive thoughts from the {role} and you will need to perform the actions described in the thoughts.
You can write a series of simple commands in Python to act.
You can perform a set of actions by calling the available Python functions.
You should perform actions based on the descriptions of the functions.

Here is your action space:
{action_space}

You should only perform actions in the action space.
You can perform multiple actions.
You can perform actions in any order.
First, explain the actions you will perform and your reasons, then write Python code to implement your actions.
If you decide to perform actions, you must write Python code to implement the actions.
You may print intermediate results if necessary.""")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({RoleType.EMBODIMENT: self.EMBODIMENT_PROMPT})
