from camel.prompts import AISocietyPromptTemplateDict, TaskPromptTemplateDict
from camel.typing import TaskType


def test_task_prompt_template_dict_init():
    task_prompt_template_dict = TaskPromptTemplateDict()
    assert isinstance(task_prompt_template_dict, dict)
    assert TaskType.AI_SOCIETY in task_prompt_template_dict
    assert task_prompt_template_dict[
        TaskType.AI_SOCIETY] == AISocietyPromptTemplateDict()
