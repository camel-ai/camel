# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import inspect
from typing import Any, Callable, Dict, Set, TypeVar, Union

from camel.typing import RoleType
from camel.utils import get_prompt_template_key_words

T = TypeVar('T')


def return_text_prompt(
        func: Callable) -> Callable[..., Union['TextPrompt', tuple]]:
    r"""Decorator that converts the return value of a function to a
    :obj:`TextPrompt` instance if it's a string.

    Args:
        func (Callable): The function to decorate.

    Returns:
        Callable[..., Union[TextPrompt, tuple]]: Decorated function that
            returns a :obj:`TextPrompt` instance if the return value is a
            string.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Union['TextPrompt', tuple]:
        r"""Wrapper function that performs the conversion to :obj:`TextPrompt`
            instance.

        Args:
            *args (Any): Variable length argument list.
            **kwargs (Any): Arbitrary keyword arguments.

        Returns:
            Union[TextPrompt, tuple]: The converted return value.
        """
        result = func(*args, **kwargs)
        if isinstance(result, str) and not isinstance(result, TextPrompt):
            return TextPrompt(result)
        elif isinstance(result, tuple):
            new_result = tuple(
                TextPrompt(item) if isinstance(item, str)
                and not isinstance(item, TextPrompt) else item
                for item in result)
            return new_result
        return result

    # # Preserve the original function's attributes
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__

    return wrapper


def wrap_text_prompt_functions(cls: T) -> T:
    r"""Decorator that wraps functions of a class inherited from :obj:`str`
    with the :obj:`return_text_prompt` decorator.

    Args:
        cls (type): The class to decorate.

    Returns:
        type: Decorated class with wrapped functions.
    """
    excluded_attrs = {'__init__', '__new__', '__str__', '__repr__'}
    for attr_name in dir(cls):
        attr_value = getattr(cls, attr_name)
        if callable(attr_value) and attr_name not in excluded_attrs:
            if inspect.isroutine(attr_value):
                setattr(cls, attr_name, return_text_prompt(attr_value))
    return cls


@wrap_text_prompt_functions
class TextPrompt(str):
    r"""A class that represents a text prompt. The :obj:`TextPrompt` class
    extends the built-in :obj:`str` class to provide a property for retrieving
    the set of key words in the prompt.

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
            TextPrompt: A new :obj:`TextPrompt` object with the format string
                replaced with the formatted string.
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
