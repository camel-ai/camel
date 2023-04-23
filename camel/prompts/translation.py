from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.typing import RoleType


# flake8: noqa
class TranslationPromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `Translation`
    task.

    Attributes:
        ASSISTANT_PROMPT (TextPrompt): A system prompt for the AI assistant
            that outlines the rules of the conversation and provides
            instructions for completing tasks.
    """
    ASSISTANT_PROMPT = TextPrompt(
        """You are an expert English to {language} translator.
Your sole purpose is to accurately translate any text presented to you from English to {language}.
Please provide the {language} translation for the given text.
If you are presented with an empty string, simply return an empty string as the translation.
Only text in between ```TEXT``` should not be translated.
Do not provide any explanation. Just provide a translation.""")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
        })
