from camel.agent import ChatAgent
from camel.message import AssistantSystemMessage, UserChatMessage
from camel.typing import ModeType


def main(role_type: str = "user", num_roles: int = 50):
    with open(f"prompts/ai_society/generate_{role_type}.txt", "r") as f:
        prompt = f.read().replace("<NUM_ROLES>", str(num_roles))
    print(prompt)
    assistant_sys_msg = AssistantSystemMessage(
        role_name="Assistant",
        content="You are a helpful assistant.",
    )
    agent = ChatAgent(assistant_sys_msg, model=ModeType.GPT_3_5_TURBO)
    agent.reset()

    user_msg = UserChatMessage(role_name="User", content=prompt)
    assistant_msg, _, _ = agent.step(user_msg)
    print(assistant_msg[0].content)


if __name__ == "__main__":
    main()
