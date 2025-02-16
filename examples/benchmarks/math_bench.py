import logging
from pathlib import Path
from camel.agents import ChatAgent
from camel.benchmarks.math_benchmarks.math_bench import MATHBenchmark
from camel.benchmarks import Mode

# Set up the agent to be benchmarked
agent = ChatAgent()
data_dir = Path("MATHDataset")
save_to = data_dir / "MATHResults.jsonl"

# Set up the Hendrykson MATH Benchmark
benchmark = MATHBenchmark(data_dir=str(data_dir), save_to=str(save_to))
benchmark.download()

#TODO run benchmark with API Key to get the value for correct answers
result = benchmark.run(agent, on="test", subset=20, mode=Mode("pass@k", 1))
print("Total:", result["total"])
print("Correct:", result["correct"])
'''
===============================================================================
Total: 20
Correct: ?
===============================================================================
'''