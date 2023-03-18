from camel_typing import (AssistantChatMessage, AssistantSystemMessage,
                          ModeType, RoleType, UserChatMessage,
                          UserSystemMessage)
from chat_agent import ChatAgent
from configs import SystemMessageGenerator


def init_chat(
    assistant_agent: ChatAgent,
    user_agent: ChatAgent,
    user_sys_msg: UserSystemMessage,
    assistant_sys_msg: AssistantSystemMessage,
):
    assistant_agent.reset()
    user_agent.reset()

    # Send the system messages again to the agents using chat messages
    assistant_msg = AssistantChatMessage(
        "Computer Programer",
        content=(f"{user_sys_msg.content}. "
                 "Now start to give me introductions one by one. "
                 "Only reply with Instruction and Input."))
    assistant_msg.role = "user"

    user_msg = UserChatMessage(user_sys_msg.role_name,
                               content=f"{assistant_sys_msg.content}")
    msgs, _, _ = assistant_agent.step(user_msg)

    return assistant_msg, msgs


def main() -> None:
    task_prompt = "Developing custom game mods or plugins for Minecraft"
    sys_msg_generator = SystemMessageGenerator(with_task=True)
    assistant_sys_msg, user_sys_msg = sys_msg_generator.from_roles(
        roles=[("Computer Programmer", RoleType.ASSISTANT),
               ("Gamer", RoleType.USER)], task_prompt=task_prompt)
    assistant_agent = ChatAgent(assistant_sys_msg, ModeType.GPT_3_5_TURBO)
    user_agent = ChatAgent(user_sys_msg, ModeType.GPT_3_5_TURBO)

    assistant_msg, _ = init_chat(assistant_agent, user_agent, user_sys_msg,
                                 assistant_sys_msg)

    while True:
        user_msgs, user_terminated, _ = user_agent.step(assistant_msg)
        if user_terminated:
            break
        user_msg = user_msgs[0]
        print(f"User:\n{user_msg.content}\n")
        user_msg.role = "user"

        assistant_msgs, assistant_terminated, _ = assistant_agent.step(
            user_msg)
        if assistant_terminated:
            break
        assistant_msg = assistant_msgs[0]
        print(f"Assistant:\n{assistant_msg.content}\n")
        assistant_msg.role = "user"


if __name__ == "__main__":
    main()
