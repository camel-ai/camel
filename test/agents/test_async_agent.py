import asyncio
from camel.agents.embodied_agent import EmbodiedAgent
from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.responses.agent_responses import ChatAgentResponse


def test_Async_Agent():
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
        )
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Hello!",
        )
    chatagent_1 = ChatAgent(assistant_sys_msg)
    chatagent_2 = ChatAgent(assistant_sys_msg)
    embodiedagent = EmbodiedAgent(assistant_sys_msg)

    loop = asyncio.get_event_loop()

    tasks = [
            loop.create_task(chatagent_1.astep(user_msg)),
            loop.create_task(chatagent_2.astep(user_msg)),
            loop.create_task(embodiedagent.astep(user_msg))
        ]
    wait_coro = asyncio.wait(tasks)
    loop.run_until_complete(wait_coro)

    for task in tasks:
        assert isinstance(task.result(), ChatAgentResponse)
  
    loop.close()
