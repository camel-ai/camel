from camel.agents import ChatAgent
from camel.messages import AssistantSystemMessage, UserChatMessage
from camel.prompts import PromptTemplateGenerator
from camel.typing import TaskType


def generate_meta_data(meta_data: str, num: int = 50):
    prompt_template = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.CODE, f"generate_{meta_data}")
    prompt = prompt_template.format(**{f"num_{meta_data}": num})
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
