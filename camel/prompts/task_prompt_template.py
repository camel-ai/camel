from typing import Any, Dict

from camel.prompts import (
    AISocietyPromptTemplateDict,
    CodePromptTemplateDict,
    EvaluationPromptTemplateDict,
    MisalignmentPromptTemplateDict,
    TextPromptDict,
    TranslationPromptTemplateDict,
)
from camel.typing import TaskType


class TaskPromptTemplateDict(Dict[Any, TextPromptDict]):
    r"""A dictionary (:obj:`Dict[Any, TextPromptDict]`) of task prompt
    templates keyed by task type. This dictionary is used to map from
    a task type to its corresponding prompt template dictionary.

    Args:
        *args: Positional arguments passed to the :obj:`dict` constructor.
        **kwargs: Keyword arguments passed to the :obj:`dict` constructor.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            TaskType.AI_SOCIETY: AISocietyPromptTemplateDict(),
            TaskType.CODE: CodePromptTemplateDict(),
            TaskType.MISALIGNMENT: MisalignmentPromptTemplateDict(),
            TaskType.TRANSLATION: TranslationPromptTemplateDict(),
            TaskType.EVALUATION: EvaluationPromptTemplateDict(),
        })
