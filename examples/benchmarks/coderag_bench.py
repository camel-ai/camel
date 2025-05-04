# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import logging

from camel.agents import ChatAgent
from camel.benchmarks import CodeRAGBenchAutoRetriever, CodeRAGBenchmark
from camel.types import StorageType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("coderag_bench.log"),
    ],
)

logger = logging.getLogger(__name__)
logger.info("Starting CodeRAG-Bench example run...")


if __name__ == "__main__":
    assistant_sys_msg = """You are a helpful AI coding assistant.
You are given user queries, and your job is to generate appropriate code responses.
Only output the code.
If the query is ambiguous or lacks information, make reasonable assumptions."""
    agent = ChatAgent(assistant_sys_msg)
    retriever = CodeRAGBenchAutoRetriever(
        storage_type=StorageType.QDRANT,
        vector_storage_local_path="./CodeRag_Bench_Datasets/.vector_cache",
        overwrite=True,
    )

    # Example: Humaneval, retrieval + generation
    benchmark = CodeRAGBenchmark(
        data_dir="./CodeRag_Bench_Datasets",
        save_to="./CodeRag_Bench_Datasets",
        run_mode='retrieve_generate',
        task='humaneval',
        subset_size=5,
        retrieval_type="canonical",
    )
    benchmark.load()
    output_metrics = benchmark.run(
        agent,
        retriever,
        n_generation_samples=1,
        allow_code_execution=True,
        generation_eval_k=[1],
        retrieval_top_k=10,
    )
    print(output_metrics)
    """
    output_metrics:
    {'retrieval': {'ndcg': {'NDCG@1': 1.0, 'NDCG@5': 1.0, 'NDCG@10': 1.0},
                   'mrr': {'MRR@1': 1.0, 'MRR@5': 1.0, 'MRR@10': 1.0},
                   'recall': {'Recall@1': 1.0, 'Recall@5': 1.0,
                              'Recall@10': 1.0},
                   'precision': {'P@1': 1.0, 'P@5': 0.2, 'P@10': 0.1}},
    'generation': {'pass@1': 1.0}}
    """

    # Example: Humaneval, retrieval only
    benchmark = CodeRAGBenchmark(
        data_dir="./CodeRag_Bench_Datasets",
        save_to="./CodeRag_Bench_Datasets",
        run_mode='retrieve',
        task='humaneval',
        subset_size=5,
        retrieval_type="canonical",
    )
    benchmark.load()
    output_metrics = benchmark.run(
        agent,
        retriever,
        n_generation_samples=1,
        allow_code_execution=True,
        generation_eval_k=[1],
        retrieval_top_k=10,
    )
    print(output_metrics)
    '''
    output_metrics:
    {'retrieval': {'ndcg': {'NDCG@1': 1.0, 'NDCG@5': 1.0, 'NDCG@10': 1.0}, 'mrr': {'MRR@1': 1.0, 'MRR@5': 1.0, 'MRR@10': 1.0}, 'recall': {'Recall@1': 1.0, 'Recall@5': 1.0, 'Recall@10': 1.0}, 'precision': {'P@1': 1.0, 'P@5': 0.2, 'P@10': 0.1}}}
    '''

    # Example: Humaneval, generation only
    benchmark = CodeRAGBenchmark(
        data_dir="./CodeRag_Bench_Datasets",
        save_to="./CodeRag_Bench_Datasets",
        run_mode='generate',
        task='humaneval',
        subset_size=5,
        retrieval_type="canonical",
    )
    benchmark.load()
    output_metrics = benchmark.run(
        agent,
        retriever,
        n_generation_samples=1,
        allow_code_execution=True,
        retrieval_top_k=10,
        generation_eval_k=[1],
    )
    print(output_metrics)
    '''
    {'generation': {'pass@1': 1.0}}
    '''
