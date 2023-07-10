from pathlib import Path
from colorama import Fore

from camel.agents import WebsiteAgent
from camel.messages import BaseMessage
from camel.configs import ChatGPTConfig
from camel.utils.functions import database
from camel.typing import ModelType, RoleType
from camel.prompts import WebsitePromptTemplateDict
from camel.utils.functions import print_text_animated


project_path = "examples/website/markdown_editor"
template_dict = WebsitePromptTemplateDict(project_path=project_path)
system_prompt = template_dict.ASSISTANT_PROMPT
task_prompt = template_dict.USER_PROMPT
print(Fore.YELLOW + f"Task prompt:\n{task_prompt}\n")

user_msg = BaseMessage(role_name="Computer Programmer", role_type=RoleType.USER,
            meta_dict=dict(), content=task_prompt)

model_config = ChatGPTConfig(temperature=0.1)
assistant = WebsiteAgent(system_prompt, model=ModelType.GPT_4, model_config=model_config)
assistant_response = assistant.step(user_msg)


code_save_path = Path(project_path).absolute() / "workspace"
read_write_content = database(path=code_save_path)
print_text_animated(Fore.GREEN + f"Code Generation:\n\n{assistant_response.msg.content}\n")
assistant.to_files(assistant_response, read_write_content)
