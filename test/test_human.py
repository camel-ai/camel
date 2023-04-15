from camel.human import Human
from camel.messages import AssistantChatMessage


def test_display_options():
    human = Human()
    msgs = [
        AssistantChatMessage(role_name="assistant", content="Hello"),
        AssistantChatMessage(role_name="assistant", content="World"),
    ]
    human.display_options(msgs)


def test_get_input(monkeypatch):
    human = Human()
    msgs = [
        AssistantChatMessage(role_name="assistant", content="Hello"),
        AssistantChatMessage(role_name="assistant", content="World"),
    ]
    human.display_options(msgs)
    monkeypatch.setattr('builtins.input', lambda _: str(1))
    assert human.get_input() == str(1)


def test_step(monkeypatch):
    human = Human()
    msgs = [
        AssistantChatMessage(role_name="assistant", content="Hello"),
        AssistantChatMessage(role_name="assistant", content="World"),
    ]

    monkeypatch.setattr('builtins.input', lambda _: str(1))
    msg = human.step(msgs)
    assert msg.content == "Hello"
