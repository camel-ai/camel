from camel.agents.chat_agent import ChatAgent
from camel.benchmark.utils.benchmark_apibank import APIBank
from camel.messages import BaseMessage

def test_apibank_benchmark():
    benchmark = APIBank()
    datasets = benchmark.get_datasets()
    print("benchmark in APIbank: ", datasets)
    for dataset in datasets:
        print("Testing dataset: ", dataset)
        # Define system message
        agent = ChatAgent()
        print("Agent: ", agent)
        results1 = benchmark.eval(dataset, api_test_enabled=False, agent=agent)
        results2 = benchmark.eval(dataset, api_test_enabled=False, agent=agent)

        assert results1 and results2 is not None


test_apibank_benchmark()