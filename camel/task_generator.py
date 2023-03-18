from camel_typing import (AssistantChatMessage, AssistantSystemMessage,
                          ModeType, RoleType, UserChatMessage,
                          UserSystemMessage)
from chat_agent import ChatAgent
from configs import SystemMessageGenerator, TaskPromptGenerator



def main() -> None:
    task_prompt_generator = TaskPromptGenerator().generate_role_prompt()
    sys_msg_generator = SystemMessageGenerator()

    assistant_sys_msg = sys_msg_generator.from_role(RoleType.DEFAULT)
    assistant_agent = ChatAgent(assistant_sys_msg, ModeType.GPT_3_5_TURBO)
    
    for task_prompt in task_prompt_generator:
        print(task_prompt)
        assistant_sys_msg.content = task_prompt
        user_msgs, _, _ = assistant_agent.step(assistant_sys_msg)
        user_msg = user_msgs[0]
        print(f"User:\n{user_msg.content}\n")





if __name__ == "__main__":
    main()
    exit()
