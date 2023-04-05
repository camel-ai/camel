from camel.generator import (
    AISocietyTaskPromptGenerator,
    RoleNameGenerator,
    SystemMessageGenerator,
)
from camel.typing import RoleType, TaskType


def test_system_message_generator():
    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
    sys_msg_generator.from_dict({"<ASSISTANT_ROLE>": "doctor"},
                                role_tuple=("doctor", RoleType.ASSISTANT))
    sys_msg_generator.from_dict({"<USER_ROLE>": "doctor"},
                                role_tuple=("doctor", RoleType.USER))

    sys_msg_generator.from_dicts(
        [{
            "<ASSISTANT_ROLE>": "chatbot",
            "<USER_ROLE>": "doctor"
        }] * 2,
        role_tuples=[("chatbot", RoleType.ASSISTANT),
                     ("doctor", RoleType.USER)],
    )

    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
    sys_msg_generator.from_dicts(
        [{
            "<ASSISTANT_ROLE>": "chatbot",
            "<USER_ROLE>": "doctor",
            "<TASK>": "Analyze a patient's medical report"
        }] * 2,
        role_tuples=[("chatbot", RoleType.ASSISTANT),
                     ("doctor", RoleType.USER)],
    )


def test_role_name_generator():
    role_name_generator = RoleNameGenerator().from_role_files()
    role_tuple = next(role_name_generator)
    assert isinstance(role_tuple, tuple)


def test_task_prompt_generator():
    role_name_generator = RoleNameGenerator().from_role_files()
    task_tuple = next(AISocietyTaskPromptGenerator().from_role_generator(
        role_name_generator))
    assert isinstance(task_tuple, str)

    task_tuple = next(AISocietyTaskPromptGenerator().from_role_files())
    assert isinstance(task_tuple, str)
