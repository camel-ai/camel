from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.typing import RoleType


# flake8: noqa
class EvaluationPromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `Evaluation`
    task.

    Attributes:
        GENERATE_QUESTIONS (TextPrompt): A prompt to generate a set of questions
        to be used for evaluating emergence of knowledge based on a particular 
        field of knowledge.
    """

    GENERATE_QUESTIONS = TextPrompt(
        """Generate {num_questions} {category} diverse questions.
Here are some example questions:
{examples}

Now generate {num_questions} questions of your own. Be creative""")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            "generate_questions": self.GENERATE_QUESTIONS,
        })
