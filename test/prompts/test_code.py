from camel.prompts import CodePromptTemplateDict, TextPrompt
from camel.typing import RoleType


def test_code_prompt_template_dict():
    template_dict = CodePromptTemplateDict()

    # Test if the prompts are of the correct type
    assert isinstance(template_dict.GENERATE_LANGUAGES, TextPrompt)
    assert isinstance(template_dict.GENERATE_DOMAINS, TextPrompt)
    assert isinstance(template_dict.GENERATE_TASKS, TextPrompt)
    assert isinstance(template_dict.TASK_SPECIFY_PROMPT, TextPrompt)
    assert isinstance(template_dict.ASSISTANT_PROMPT, TextPrompt)
    assert isinstance(template_dict.USER_PROMPT, TextPrompt)

    # Test if the prompts are correctly added to the dictionary
    assert template_dict[
        'generate_languages'] == template_dict.GENERATE_LANGUAGES
    assert template_dict['generate_domains'] == template_dict.GENERATE_DOMAINS
    assert template_dict['generate_tasks'] == template_dict.GENERATE_TASKS
    assert template_dict[
        'task_specify_prompt'] == template_dict.TASK_SPECIFY_PROMPT
    assert template_dict[RoleType.ASSISTANT] == template_dict.ASSISTANT_PROMPT
    assert template_dict[RoleType.USER] == template_dict.USER_PROMPT
