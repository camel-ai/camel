import os

from camel.agents import ChatAgent
from camel.messages import AssistantSystemMessage, UserChatMessage
from camel.prompts import PROMPTS_DIR


def generate_meta_data(meta_data: str, num: int = 50):
    prompt_path = os.path.join(
        PROMPTS_DIR,
        f"code/generate_{meta_data}.txt",
    )
    with open(prompt_path, "r") as f:
        prompt = f.read().replace(f"<NUM_{meta_data.upper()}>", str(num))
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
    generate_meta_data("languages", 20)
    generate_meta_data("domains", 50)
