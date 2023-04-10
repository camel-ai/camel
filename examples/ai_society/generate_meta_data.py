import os

from camel.agents import ChatAgent
from camel.messages import AssistantSystemMessage, UserChatMessage
from camel.prompts import PROMPTS_DIR


def main(role_type: str = "user", num_roles: int = 50):
    prompt_path = os.path.join(PROMPTS_DIR,
                               f"ai_society/generate_{role_type}.txt")
    with open(prompt_path, "r") as f:
        prompt = f.read().replace("<NUM_ROLES>", str(num_roles))
    print(prompt)
    assistant_sys_msg = AssistantSystemMessage(
        role_name="Assistant",
        content="You are a helpful assistant.",
    )
    agent = ChatAgent(assistant_sys_msg)
    agent.reset()

    user_msg = UserChatMessage(
        role_name="User",
        content=prompt,
    )
    assistant_msg, _, _ = agent.step(user_msg)
    print(assistant_msg[0].content)


if __name__ == "__main__":
    main("user", 50)
    main("assistant", 50)
