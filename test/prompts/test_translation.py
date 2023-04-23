from camel.prompts import TextPrompt, TranslationPromptTemplateDict
from camel.typing import RoleType


def test_translation_prompt_template_dict():
    template_dict = TranslationPromptTemplateDict()

    # Test if the prompts are of the correct type
    assert isinstance(template_dict.ASSISTANT_PROMPT, TextPrompt)

    # Test if the prompts are correctly added to the dictionary
    assert template_dict[RoleType.ASSISTANT] == template_dict.ASSISTANT_PROMPT
