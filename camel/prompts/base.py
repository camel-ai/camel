from typing import Any, Dict, Set

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


class TextPromptDict(Dict[Any, TextPrompt]):
    r"""A dictionary class that maps from key to :obj:`TextPrompt` object.
    """
    pass
