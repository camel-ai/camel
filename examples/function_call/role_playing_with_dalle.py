# %%
from camel.types import ModelType
import os
from camel.agents.chat_agent import ChatAgent
from camel.configs import FunctionCallingConfig
from camel.generators import SystemMessageGenerator
from camel.messages.base import BaseMessage
from camel.types.enums import RoleType
from camel.functions import T2I_FUNCS

os.environ["OPENAI_API_KEY"] = ""

# %%
def main():
    # Create an embodied agent
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}", RoleType.DEFAULT))
    
    user_msg = BaseMessage.make_user_message(
        role_name=role_name,
        content="Can you draw a picture of a camel ?",
    )
    
    function_list=[*T2I_FUNCS]
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
    print(response.msg.content)

# %%
main()


