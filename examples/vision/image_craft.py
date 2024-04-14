# %%
from camel.types import ModelType
import os
from camel.agents.chat_agent import ChatAgent
from camel.configs import FunctionCallingConfig
from camel.generators import PromptTemplateGenerator, SystemMessageGenerator
from camel.messages.base import BaseMessage
from camel.types.enums import RoleType
from camel.functions import T2I_FUNCS
from camel.types import ModelType, RoleType, TaskType


def craft_image(caption):
    role_name = "Artist"

    sys_template = PromptTemplateGenerator().get_prompt_from_key(TaskType.IMAGE_CRAFT, RoleType.ASSISTANT)

    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_template)
    user_msg = BaseMessage.make_user_message(
        role_name=role_name,
        content="Caption: " + caption,

    )

    print("=" * 20 + " USR MSG " + "=" * 20)
    print(user_msg.content)
    print("=" * 49)

    function_list = [*T2I_FUNCS]
    assistant_model_config = FunctionCallingConfig.from_openai_function_list(
        function_list=function_list,
        kwargs=dict(temperature=0.0),
    )

    dalle_agent = ChatAgent(
        system_message=sys_msg,
        model_type=ModelType.GPT_4_TURBO,
        model_config=assistant_model_config,
        function_list=[*T2I_FUNCS],
    )

    response = dalle_agent.step(user_msg)

    print("=" * 20 + " RESULT " + "=" * 20)
    print(response.msg.content)
    print("=" * 48)
