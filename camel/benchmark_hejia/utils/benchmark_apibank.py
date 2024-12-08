from camel.benchmark.utils.benchmark_base import BenchmarkBase
from camel.benchmark.datasets.apibank.evaluator import eval_apibank
class APIBank(BenchmarkBase):
    def get_datasets(self):
        return [
                'level1', 
                'level2', 
                'level3']
    
    def get_tools(self, dataset):
        print("APIBank datasets do not have API based tools. It's based on AST evaluation.")
    
    def eval(self, dataset, api_test_enabled, agent):
        return eval_apibank(dataset, api_test_enabled, agent)




