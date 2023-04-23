from camel.generators import (
    AISocietyTaskPromptGenerator,
    RoleNameGenerator,
    SystemMessageGenerator,
)
from camel.typing import RoleType, TaskType


def test_system_message_generator():
    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
    sys_msg_generator.from_dict(dict(assistant_role="doctor"),
                                role_tuple=("doctor", RoleType.ASSISTANT))
    sys_msg_generator.from_dict(dict(user_role="doctor"),
                                role_tuple=("doctor", RoleType.USER))

    sys_msg_generator.from_dicts(
        [dict(assistant_role="doctor", user_role="doctor")] * 2,
        role_tuples=[("chatbot", RoleType.ASSISTANT),
                     ("doctor", RoleType.USER)],
    )

    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
    sys_msg_generator.from_dicts(
        [
            dict(assistant_role="chatbot", user_role="doctor",
                 task="Analyze a patient's medical report")
        ] * 2,
        role_tuples=[("chatbot", RoleType.ASSISTANT),
                     ("doctor", RoleType.USER)],
    )


def test_role_name_generator():
    role_name_generator = RoleNameGenerator().from_role_files()
    role_tuple = next(role_name_generator)
    assert isinstance(role_tuple, tuple)


def test_task_prompt_generator():
    role_name_generator = RoleNameGenerator().from_role_files()
    task_prompt, role_names = next(
        AISocietyTaskPromptGenerator().from_role_generator(
            role_name_generator))
    assert isinstance(task_prompt, str)
    assert isinstance(role_names, tuple)
    for role_name in role_names:
        assert isinstance(role_name, str)

    task_prompt, role_names = next(
        AISocietyTaskPromptGenerator().from_role_files())
    assert isinstance(task_prompt, str)
    assert isinstance(role_names, tuple)
    for role_name in role_names:
        assert isinstance(role_name, str)
