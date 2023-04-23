from camel.prompts import MisalignmentPromptTemplateDict, TextPrompt
from camel.typing import RoleType


def test_misalignment_prompt_template_dict():
    template_dict = MisalignmentPromptTemplateDict()

    # Test if the prompts are of the correct type
    assert isinstance(template_dict.DAN_PROMPT, TextPrompt)
    assert isinstance(template_dict.GENERATE_TASKS, TextPrompt)
    assert isinstance(template_dict.TASK_SPECIFY_PROMPT, TextPrompt)
    assert isinstance(template_dict.ASSISTANT_PROMPT, TextPrompt)
    assert isinstance(template_dict.USER_PROMPT, TextPrompt)

    # Test if the prompts are correctly added to the dictionary
    assert template_dict['dan_prompt'] == template_dict.DAN_PROMPT
    assert template_dict['generate_tasks'] == template_dict.GENERATE_TASKS
    assert template_dict[
        'task_specify_prompt'] == template_dict.TASK_SPECIFY_PROMPT
    assert template_dict[RoleType.ASSISTANT] == template_dict.ASSISTANT_PROMPT
    assert template_dict[RoleType.USER] == template_dict.USER_PROMPT
