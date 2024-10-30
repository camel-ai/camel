from camel.benchmark.utils.benchmark_base import BenchmarkBase
from camel.toolkits import FunctionTool
from camel.benchmark.datasets.nexusraven.eval_nexusraven import eval_nexus_dataset, nvd_tools, vt_tools, otx_tools, places_tools, climate_tools, vt_multi_tools, nvdmulti_tools
class NexusRaven(BenchmarkBase):
    def get_datasets(self):
        return [
            "NVDLibrary",
            "VirusTotal",
            "OTX",
            "Places API",
            "Climate API",
            "VirusTotal-Parallel Calls",
            "VirusTotal-Nested Calls",
            "NVDLibrary-Nested Calls"
        ]
    
    def get_tools(self, dataset):
        tools_dict = {
            "NVDLibrary": nvd_tools,
            "VirusTotal": vt_tools,
            "OTX": otx_tools,
            "Places API": places_tools,
            "Climate API": climate_tools,
            "VirusTotal-Parallel Calls": vt_multi_tools,
            "VirusTotal-Nested Calls": vt_multi_tools,
            "NVDLibrary-Nested Calls": nvdmulti_tools
        }
        if dataset in tools_dict:
            return [FunctionTool(tool) for tool in tools_dict[dataset]]
        else:
            raise ValueError("Invalid dataset name")
    
    def eval(self, dataset, agent):
        return eval_nexus_dataset(agent, dataset)



