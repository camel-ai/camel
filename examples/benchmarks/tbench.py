from camel.benchmarks.tbench import TBench


benchmark = TBench(name="tbench", data_dir="tbench_data", save_to="tbench_results")
benchmark.download()
benchmark.run()

