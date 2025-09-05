import os
from datetime import datetime
from pathlib import Path

from terminal_bench.harness import Harness

from .base import BaseBenchmark


class TBench(BaseBenchmark):
    def __init__(self, name, data_dir, save_to, processes=1):
        self.name = name
        self.data_dir = data_dir
        self.save_to = save_to
        self.processes = processes
        super().__init__(name, data_dir, save_to, processes)
        os.makedirs(self.save_to, exist_ok=True)
        self.harness = None

    def download(self) -> "BaseBenchmark":
        harness = Harness(
            output_path=Path(self.save_to),
            run_id=datetime.now().strftime("%Y-%m-%d__%H-%M-%S"),
            dataset_name="terminal-bench-core".strip(),
            dataset_version="0.1.1",
            task_ids=["nginx-request-logging"],
            agent_import_path="camel.benchmarks.tbench_camel_agent:TerminalBenchAgent",
        )
        self.harness = harness
        return self

    def load(self, force_download: bool = False) -> "BaseBenchmark":
        pass

    def run(self):
        results = self.harness.run()
        print(results)
