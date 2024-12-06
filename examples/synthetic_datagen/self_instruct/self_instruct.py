from camel.agents import ChatAgent
from camel.synthetic_datagen.self_instruct import SelfInstructPipeline

agent = ChatAgent()

pipeline = SelfInstructPipeline(
    agent=agent,
    seed='seed_tasks.jsonl',
    num_machine_instructions=5,
    data_output_path='./data_output.json',
    human_to_machine_ratio=(6, 2),
)

pipeline.generate()

