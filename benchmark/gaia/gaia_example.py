from benchmark.gaia import GAIABenchmark
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import GeminiConfig
from camel.messages import BaseMessage

task_prompt = (
        """
        You are a general AI assistant. I will ask you a question. Report your 
        thoughts, and finish your answer with the following template: 
        FINAL ANSWER: [YOUR FINAL ANSWER].
        YOUR FINAL ANSWER should be a number OR as few words as possible OR a 
        comma separated list of numbers and/or strings.
        If you are asked for a number, don’t use comma to write your number 
        neither use units such as $ or percent sign unless specified otherwise.
        If you are asked for a string, don’t use articles, neither 
        abbreviations (e.g. for cities), and write the digits in plain text 
        unless specified otherwise.
        If you are asked for a comma separated list, apply the above rules 
        depending of whether the element to be put in the list is a number or 
        a string.
        """.strip()
        )
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content=task_prompt,
)
model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_1_5_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).__dict__,
)
gaia = GAIABenchmark()
gaia.download()
agent = ChatAgent(system_message=sys_msg,model=model)
scores = gaia.eval(agent,"validation", 1,)
print(scores)
