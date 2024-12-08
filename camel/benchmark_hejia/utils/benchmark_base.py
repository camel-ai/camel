# 定义一个基类用于所有benchmark
class BenchmarkBase:
    def __init__(self):
        self.datasets = self.get_datasets()

    def get_datasets(self):
        """获取评估所使用的数据集，子类可以重写此方法定义特定数据集"""
        raise NotImplementedError("Subclasses should implement this method to return the list of datasets")

    def get_tools(self, dataset):
        """获取要使用的工具，子类可以重写此方法定义特定工具集"""
        raise NotImplementedError("Subclasses should implement this method to return the list of tools")
    
    def eval(self, dataset, agent):
        """评估传入的代理，使用不同的数据集进行评估"""
        raise NotImplementedError("Subclasses should implement this method to eval datasets")

