from camel.benchmark.utils.benchmark_base import BenchmarkBase
from camel.benchmark.datasets.gorilla.eval.eval_scripts.get_llm_responses import get_llm_response
from camel.benchmark.datasets.gorilla.eval.eval_scripts.ast_eval_th import eval_ast

class Gorilla(BenchmarkBase):
    def get_datasets(self):
        return [
                'torchhub', 
                'tensorhub', 
                'huggingface']
    
    def get_tools(self, dataset):
        print("Gorilla datasets do not have API based tools. It's based on AST evaluation.")
    
    def eval(self, dataset, agent):
        get_llm_response(dataset, agent)
        return eval_ast(dataset)



