from camel.agents import ChatAgent
from camel.messages import AssistantSystemMessage, UserChatMessage
from camel.prompts import PromptTemplateGenerator
from camel.typing import TaskType


def main(key: str = "generate_users", num_roles: int = 50):
    prompt_template = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.AI_SOCIETY, key)
    prompt = prompt_template.format(num_roles=num_roles)
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
    main("generate_users", 50)
    main("generate_assistants", 50)
