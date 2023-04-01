from camel.generator import (AISocietyTaskPromptGenerator, RoleNameGenerator,
                             SystemMessageGenerator)
from camel.typing import RoleType


def test_system_message_generator():
    sys_msg_generator = SystemMessageGenerator(with_task=False)
    sys_msg_generator.from_role(role_name="doctor",
                                role_type=RoleType.ASSISTANT)
    sys_msg_generator.from_role(role_name="doctor", role_type=RoleType.USER)

    sys_msg_generator.from_roles(
        roles=[("doctor", RoleType.USER), ("chatbot", RoleType.ASSISTANT)])

    generator = sys_msg_generator.from_role_files()
    sys_msg_1 = next(generator)
    sys_msg_2 = next(generator)
    assert sys_msg_1 != sys_msg_2

    sys_msg_generator = SystemMessageGenerator(with_task=True)
    sys_msg_generator.from_roles(
        roles=[("doctor", RoleType.USER), ("chatbot", RoleType.ASSISTANT)],
        task_prompt="Analyze a patient's medical report")


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
