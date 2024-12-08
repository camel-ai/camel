from camel.agents.chat_agent import ChatAgent
from camel.benchmark.utils.benchmark_gorilla import Gorilla
from camel.messages import BaseMessage

def test_gorilla_benchmark():
    benchmark = Gorilla()
    datasets = benchmark.get_datasets()
    print("benchmark in Gorilla: ", datasets)
    # ['torchhub', 'tensorhub', 'huggingface']
    for dataset in datasets:
        print("Testing dataset: ", dataset)
        # Define system message
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="You are a helpful API writer who can write APIs based on requirements.",
        )
        agent = ChatAgent(system_message=sys_msg)
        results = benchmark.eval(dataset, agent)
        assert results is not None

test_gorilla_benchmark()