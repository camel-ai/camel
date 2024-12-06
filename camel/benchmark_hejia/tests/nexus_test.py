from camel.agents.chat_agent import ChatAgent
from camel.benchmark.utils.benchmark_nexusraven import NexusRaven

def test_nexus_benchmark():
    benchmark = NexusRaven()
    datasets = benchmark.get_datasets()
    print("benchmark in Nexus: ", datasets)
    
    for dataset in datasets:
        print("Testing dataset: ", dataset)
        agent = ChatAgent(tools=benchmark.get_tools(dataset))
        results = benchmark.eval(dataset, agent)
        assert results is not None

test_nexus_benchmark()