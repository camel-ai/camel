from camel.agents.chat_agent import ChatAgent
from camel.benchmarks import GAIABenchmark
from camel.configs.openai_config import ChatGPTConfig
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.runtime.docker_runtime import DockerRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types.enums import ModelPlatformType, ModelType


benchmark = GAIABenchmark(
    data_dir="datasets_test", processes=1, save_to="results.jsonl"
)

print(f"Number of validation examples: {len(benchmark.valid)}")
print(f"Number of test examples: {len(benchmark.test)}")

toolkit = CodeExecutionToolkit(verbose=True)
runtime = DockerRuntime("xukunliu/camel").add(
    toolkit.get_tools(),
    "camel.toolkits.CodeExecutionToolkit",
    dict(verbose=True),
    redirect_stdout=False,
)

task_prompt = """
        You are a general AI assistant. I will ask you a question. Report your 
        thoughts, and finish your answer with the following template: 
        FINAL ANSWER: [YOUR FINAL ANSWER].
        YOUR FINAL ANSWER should be a number OR as few words as possible OR a 
        comma separated list of numbers and/or strings.
        If you are asked for a number, don't use comma to write your number 
        neither use units such as $ or percent sign unless specified otherwise.
        If you are asked for a string, don't use articles, neither 
        abbreviations (e.g. for cities), and write the digits in plain text 
        unless specified otherwise.
        If you are asked for a comma separated list, apply the above rules 
        depending of whether the element to be put in the list is a number or 
        a string.
        """.strip()

sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content=task_prompt,
)

tools = runtime.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

agent = ChatAgent(
    sys_msg,
    model,
    tools=tools,
)

with runtime as r:
    r.wait()
    benchmark.run(agent, "valid", level="all", subset=3)

"""
Number of validation examples: 165
Number of test examples: 300
"""
