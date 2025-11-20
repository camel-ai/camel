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

"""
Pipeline Workflow Example - Demonstration of CAMEL Workforce Pipeline
functionality.

This example demonstrates the fork-join pattern in CAMEL Workforce
Pipeline mode:
- Single source task (literature search)
- Fork to 5 parallel summarization tasks
- Join results into a comprehensive synthesis

The example shows how to handle parallel task processing where multiple agents
work on different parts of the same data source with automatic synchronization.
"""

import asyncio
import time

from colorama import Fore, Style, init

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce, WorkforceMode
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType

# Initialize colorama for colored output
init(autoreset=True)

# Create model once for all agents
# model = ModelFactory.create(
#     model_platform=ModelPlatformType.DEFAULT,
#     model_type=ModelType.DEFAULT,
# )

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=ChatGPTConfig().as_dict(),
)


def print_section(title: str):
    """Print a colored section header."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{title}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")


def print_result(task_id: str, result: str):
    """Print task result with formatting."""
    print(f"{Fore.GREEN}Task {task_id} completed:")
    truncated = result[:200]
    suffix = "..." if len(result) > 200 else ""
    print(f"{Fore.WHITE}Result: {truncated}{suffix}")
    print()


async def example_1_literature_analysis_pipeline():
    """Example 1: Literature analysis with parallel summarization."""
    print_section("Example 1: Literature Analysis with Parallel Processing")

    # Create coordinator agent
    coordinator_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Literature Analysis Coordinator",
            content=(
                "You are a coordinator responsible for managing literature "
                "analysis tasks and ensuring quality output."
            ),
        ),
        model=model,
    )

    # Create task agent using the same model
    task_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Task Planning Agent",
            content=(
                "You are a task planning agent responsible for analyzing and "
                "coordinating complex tasks."
            ),
        ),
        model=model,
    )

    # Create workforce for literature analysis
    workforce = Workforce(
        "Literature Analysis Team",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        mode=WorkforceMode.PIPELINE,
    )

    # Add search agent with search tools (using mock data for demonstration)
    search_system_message = BaseMessage.make_assistant_message(
        role_name="Literature Researcher",
        content=(
            "You are a literature researcher. Provide 5 recent AI/ML papers "
            "with titles, authors, and brief descriptions. Format them as "
            "[Paper 1], [Paper 2], etc. Use representative examples from "
            "recent AI/ML research."
        ),
    )
    search_agent = ChatAgent(
        system_message=search_system_message, model=model, tools=[]
    )

    # Add multiple summary agents for parallel processing
    for i in range(5):
        summary_system_message = BaseMessage.make_assistant_message(
            role_name=f"Summary Specialist {i+1}",
            content=(
                "You are a literature summary specialist. Focus on extracting "
                "key insights, methodologies, and contributions from research "
                "papers."
            ),
        )
        summary_agent = ChatAgent(
            system_message=summary_system_message, model=model, tools=[]
        )
        workforce.add_single_agent_worker(
            f"Summary Specialist {i+1}", summary_agent
        )

    # Add synthesis agent
    synthesis_system_message = BaseMessage.make_assistant_message(
        role_name="Research Synthesizer",
        content=(
            "You are a research synthesizer. Combine multiple literature "
            "summaries into comprehensive analysis and identify research "
            "trends."
        ),
    )
    synthesis_agent = ChatAgent(
        system_message=synthesis_system_message, model=model, tools=[]
    )

    workforce.add_single_agent_worker("Literature Researcher", search_agent)
    workforce.add_single_agent_worker("Research Synthesizer", synthesis_agent)

    # Build literature analysis pipeline
    workforce.pipeline_add(
        (
            "Generate 5 representative recent AI/ML papers with titles, "
            "authors, and brief descriptions. Format as [Paper 1] to [Paper 5]"
        )
    ).pipeline_fork(
        [
            "Summarize [Paper 1] core insights, methodology and contributions",
            "Summarize [Paper 2] core insights, methodology and contributions",
            "Summarize [Paper 3] core insights, methodology and contributions",
            "Summarize [Paper 4] core insights, methodology and contributions",
            "Summarize [Paper 5] core insights, methodology and contributions",
        ]
    ).pipeline_join(
        "Analyze AI/ML research trends based on the 5 paper summaries"
    ).pipeline_build()

    print(
        f"{Fore.YELLOW}Literature analysis pipeline built: "
        "1 search → 5 parallel summaries → 1 synthesis"
    )
    print(f"{Fore.YELLOW}Mode: {workforce.mode}")

    # Execute the pipeline
    main_task = Task(
        content="AI/ML Literature Review and Trend Analysis",
        id="literature_analysis",
    )

    start_time = time.time()
    result = await workforce.process_task_async(main_task)
    end_time = time.time()

    print_result(
        result.id,
        result.result or "Literature analysis completed successfully",
    )
    duration = end_time - start_time
    print(f"{Fore.BLUE}[TIME] Execution time: {duration:.2f} seconds")

    return result


def print_summary():
    """Print example summary."""
    print_section("Pipeline Example Summary")

    print(f"{Fore.GREEN}Pipeline pattern demonstrated:")
    patterns = [
        ("✓ FORK-JOIN: Single task → 5 parallel processing " "→ 1 synthesis"),
        "✓ PARALLEL SCALING: Easy adjustment of parallel worker count",
        (
            "✓ DEPENDENCY CHAINS: Automatic synchronization and "
            "dependency resolution"
        ),
        (
            "✓ STRUCTURED OUTPUT: Using [markers] for smart task "
            "distribution"
        ),
    ]

    for pattern in patterns:
        print(f"{Fore.WHITE}  {pattern}")

    print(f"\n{Fore.CYAN}Technical features:")
    tech_features = [
        "• Pipeline mode with pipeline_fork() and pipeline_join()",
        "• Automatic worker assignment and task routing",
        "• Multi-agent parallel coordination",
        "• Structured task dependencies",
    ]

    for feature in tech_features:
        print(f"{Fore.WHITE}  {feature}")


async def main():
    """Main function to run pipeline example."""
    print_section("CAMEL Workforce Pipeline Example")
    print(
        f"{Fore.YELLOW}Testing Pipeline mode with fork-join pattern and "
        "parallel processing."
    )

    result = None

    try:
        print(f"\n{Fore.BLUE}Running literature analysis pipeline example...")

        result = await example_1_literature_analysis_pipeline()

        print_summary()

        print(f"\n{Fore.GREEN}Pipeline example completed successfully!")

    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}")
        import traceback

        traceback.print_exc()
        raise

    return result


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

"""
============================================================
CAMEL Workforce Pipeline Example
============================================================
Testing Pipeline mode with fork-join pattern and parallel processing.

Running literature analysis pipeline example...

============================================================
Example 1: Literature Analysis with Parallel Processing
============================================================
Literature analysis pipeline built:
1 search → 5 parallel summaries → 1 synthesis
Mode: WorkforceMode.PIPELINE
Worker node a17f1759-8729-4986-9842-8de8646ff1f0 (Literature Researcher)
get task pipeline_task_0: Generate 5 representative recent AI/ML papers with
titles, authors, and brief descriptions. Format as [Paper 1] to [Paper 5]
======
Response from Worker node a17f1759-8729-4986-9842-8de8646ff1f0 (Literature
Researcher):

[Paper 1]
Title: "Scaling Laws for Generative Language Models Revisited"
Authors: Ethan Dyer, Xuezhi Wang, Jeffrey Wu, et al.
Description: This paper provides an updated empirical analysis of scaling laws
for large transformer-based language models, exploring how model performance
improves with increased data and parameters, and offering new insights for
efficient model training.

[Paper 2]
Title: "Aligning Language Models to Follow Instructions"
Authors: Long Ouyang, Jeffrey Wu, Xu Jiang, et al.
Description: The authors propose novel methods for instruction tuning large
language models using reinforcement learning from human feedback (RLHF),
improving alignment and helpfulness in conversational AI systems.

[Paper 3]
Title: "EfficientViT: Memory Efficient Vision Transformers with Cascaded Group
Attention"
Authors: Ziyu Guo, Zhiqiang Shen, Zhijian Liu, et al.
Description: EfficientViT introduces a new vision transformer architecture
employing cascaded group attention, significantly reducing memory usage and
computational cost while maintaining competitive performance on image
classification benchmarks.

[Paper 4]
Title: "GraphGPT: Enhancing Graph Neural Networks with Generative
Pre-training"
Authors: Yuanhao Xiong, Junchi Yan, Xiaokang Yang, et al.
Description: GraphGPT integrates generative pre-training strategies into graph
neural networks, enabling better performance on graph-level tasks and
transfer learning scenarios commonly found in molecular property prediction
and social network analysis.

[Paper 5]
Title: "Self-Rewarding Language Models"
Authors: Daniel Fried, John Thickstun, Tatsunori Hashimoto, et al.
Description: This work introduces a self-supervised learning strategy where
language models assign their own rewards during training, effectively
improving instruction following and generalization without extensive
human-annotated data.
======
Task pipeline_task_0 completed successfully (quality score: 100).
Worker node 8a8e68ae-1cd9-480f-9dd2-c5d59d04ce0b (Summary Specialist 2) get
task parallel_1_1: Summarize [Paper 2] core insights, methodology and
contributions
Worker node 25cd87e6-253f-46de-be00-1e5c4cb0c6a7 (Summary Specialist 5) get
task parallel_4_1: Summarize [Paper 5] core insights, methodology and
contributions
Worker node c3c5898e-690e-4c8a-b94c-4e9fe706058b (Summary Specialist 4) get
task parallel_3_1: Summarize [Paper 4] core insights, methodology and
contributions
Worker node ba2d3ca5-14e2-49ac-a0d0-36a937c58fdc (Summary Specialist 3) get
task parallel_2_1: Summarize [Paper 3] core insights, methodology and
contributions
Worker node 85b0aaba-1df5-47fa-8997-5f1a0e30e127 (Summary Specialist 1) get
task parallel_0_1: Summarize [Paper 1] core insights, methodology and
contributions
======
Response from Worker node 8a8e68ae-1cd9-480f-9dd2-c5d59d04ce0b (Summary
Specialist 2):

Core Insights: "Aligning Language Models to Follow Instructions" demonstrates
that large language models can be substantially improved to follow natural
language instructions by incorporating reinforcement learning from human
feedback (RLHF). The paper reveals that instruction tuning with human
preference data significantly enhances the alignment, helpfulness, and safety
of conversational AI systems.

Methodology: The authors propose a two-stage approach. First, they fine-tune
pre-trained language models on datasets of instruction-following
demonstrations created by human annotators. Second, they employ RLHF: they
collect human preferences over model outputs, train a reward model to predict
these preferences, and optimize the language model using reinforcement
learning (often Proximal Policy Optimization) to maximize expected
human-derived rewards.

Contributions: (1) Introduced a scalable method for aligning large language
models with human intention and values, (2) conducted thorough empirical
studies demonstrating improvements in model helpfulness and safety via RLHF,
(3) released training protocols and insights that advance practical
instruction-following conversational agents.
======
Task parallel_1_1 completed successfully (quality score: 98).
======
Response from Worker node 25cd87e6-253f-46de-be00-1e5c4cb0c6a7 (Summary
Specialist 5):

Core Insights: "Self-Rewarding Language Models" introduces a novel
self-supervised learning approach whereby language models (LMs) generate
their own reward signals during training, rather than relying heavily on
human-annotated data or external reward models. The key insight is that
enabling LMs to internally assess and reward their generated responses can
lead to improved instruction following and better generalization to new
tasks.

Methodology: The authors develop a framework where the LM evaluates its own
outputs and assigns self-generated rewards, which are then used to optimize
model behavior through reinforcement learning. This involves designing
mechanisms for the language model to estimate reward signals based on
internal metrics or performance proxies, without requiring direct human
feedback or large-scale manual labeling.

Contributions:
1. Proposes a self-rewarding training paradigm for language models, reducing
   reliance on costly human feedback.
2. Demonstrates empirically that self-rewarding can improve instruction-
   following capabilities and generalization to unseen instructions.
3. Shows that self-rewarding strategies yield competitive or improved
   performance compared to methods relying on human-annotated rewards,
   supporting more scalable and autonomous model development.
======
======
Response from Worker node c3c5898e-690e-4c8a-b94c-4e9fe706058b (Summary
Specialist 4):

Core Insights: "GraphGPT: Enhancing Graph Neural Networks with Generative
Pre-training" demonstrates that leveraging generative pre-training
strategies—previously successful in language domains—can significantly
improve the performance and transferability of graph neural networks (GNNs).
The paper finds that pre-trained GNNs excel in graph-level tasks, notably in
fields like molecular property prediction and social network analysis, by
better capturing underlying graph structures and patterns.

Methodology: The authors adapt generative pre-training approaches for
application to graph data, constructing a large-scale graph corpus for
pre-training. The model is first trained to perform generative tasks on
unlabeled graphs, such as graph completion or node feature prediction. After
this pre-training phase, the GNN is fine-tuned on downstream, task-specific,
and often smaller datasets. Extensive experiments compare GraphGPT to
standard GNNs and other transfer learning methods on multiple benchmarks.

Contributions:
1. Proposes a novel framework—GraphGPT—that embeds generative pre-training
   into GNNs.
2. Demonstrates significant improvements in transfer learning and
   generalization across diverse graph-based tasks compared to conventional
   supervised training.
3. Provides empirical results showing state-of-the-art performance in key
   applications such as molecular property prediction, highlighting the power
   and flexibility of generative graph pre-training.
======
======
Response from Worker node ba2d3ca5-14e2-49ac-a0d0-36a937c58fdc (Summary
Specialist 3):

Core Insights: "EfficientViT: Memory Efficient Vision Transformers with
Cascaded Group Attention" presents an innovative architecture for vision
transformers that drastically reduces memory consumption and computational
requirements, while preserving high accuracy on image classification tasks.
The key insight is the introduction of "cascaded group attention", which
hierarchically structures attention computation to lessen redundancy and
enhance efficiency.

Methodology: The authors design a vision transformer where the standard
global self-attention is replaced with cascaded group attention mechanisms.
This approach divides the attention computation into multi-stage groups,
allowing the model to focus attention efficiently within local and
progressively broader regions before aggregating global context. The
architecture is evaluated on standard image classification datasets, and its
performance is compared against conventional vision transformer baselines in
terms of accuracy, memory usage, and speed.

Contributions:
1. Proposing the cascaded group attention mechanism, enabling significant
   memory and computation reduction in vision transformers.
2. Delivering a transformer model (EfficientViT) that consistently matches or
   outperforms existing models while using less memory and computational
   resources.
3. Providing comprehensive empirical analysis demonstrating competitive
   benchmark performance alongside resource savings, making vision
   transformers more practical for resource-constrained environments.
======
Task parallel_4_1 completed successfully (quality score: 97).
Task parallel_3_1 completed successfully (quality score: 95).
======
Response from Worker node 85b0aaba-1df5-47fa-8997-5f1a0e30e127 (Summary
Specialist 1):

Paper 1, titled "Scaling Laws for Generative Language Models Revisited" by
Ethan Dyer, Xuezhi Wang, Jeffrey Wu, et al., revisits and updates empirical
scaling laws for large transformer-based language models.

Core Insights: The paper identifies how model performance continues to
improve predictably with greater model parameters and data sizes. It provides
refined understanding of the functional relationships between model scale,
data scale, and achieved model loss, confirming and updating previously
observed power-law patterns. The findings highlight diminishing returns at
extreme scales and underscore the importance of balancing data and parameter
count for efficient training.

Methodology: The authors conduct extensive empirical experiments by training
transformer-based generative language models at various scales, systematically
varying both the amount of data and the number of model parameters. They then
measure performance metrics (such as loss and downstream task performance) and
fit empirical models to quantify and analyze the scaling relationships. The
study also includes comparisons across different datasets and training
regimens to test the robustness of the observed scaling laws.

Contributions: This work provides updated, large-scale empirical evidence for
scaling laws in generative language models, offering practical guidelines on
model size and data requirements for efficient training. The analysis informs
strategies for resource allocation and helps guide future training of even
larger models. Additionally, the refined scaling law equations and adjusted
empirical constants contribute to the research community's ability to
anticipate and plan the development of new, larger language models.
======
Task parallel_2_1 completed successfully (quality score: 95).
Task parallel_0_1 completed successfully (quality score: 98).
Worker node f60b0634-4e23-4f4f-8240-c8c63b4c98aa (Research Synthesizer) get
task pipeline_task_6: Analyze AI/ML research trends based on the 5 paper
summaries
======
Response from Worker node f60b0634-4e23-4f4f-8240-c8c63b4c98aa (Research
Synthesizer):

Analyzing the summaries of the five AI/ML research papers reveals several
major trends and directions currently shaping the field:

1. Model Scaling and Efficiency:
   Papers 1 and 3 focus on the scaling of models (both language and vision)
   and efficient architecture design. Paper 1 refines empirical scaling laws
   in large language models, highlighting predictable performance
   improvements with increased model/data size and providing practical
   guidelines for resource allocation. Paper 3 introduces memory-efficient
   vision transformers with cascaded group attention, demonstrating a strong
   trend toward creating architectures that offer both high performance and
   lower computational requirements for broader accessibility and deployment.

2. Advancing Model Alignment and Autonomy:
   Paper 2 emphasizes aligning language models to better follow human
   instructions using RLHF, while Paper 5 proposes a shift towards autonomy,
   enabling language models to generate and optimize their own rewards
   (self-rewarding LMs). This represents a key trajectory in AI safety,
   alignment, and scalability—first leveraging human feedback for grounded
   alignment, and then exploring self-guided reward mechanisms to reduce
   dependency on costly human annotation and enable more scalable training.

3. Transfer Learning and Pre-training Across Modalities:
   Paper 4 extends generative pre-training strategies from the NLP domain to
   graph neural networks (GNNs), showing significant improvements in
   generalizability and performance on graph-structured data. This highlights
   a maturing trend of adapting successful pre-training/transfer learning
   paradigms across diverse data modalities beyond text or images, such as
   graphs, for specialized tasks and improved efficiency.

4. Diminishing Reliance on Human Supervision:
   Both Paper 2 (with RLHF) and Paper 5 (self-rewarding LMs) tackle the cost
   and scalability limits of human-in-the-loop systems, the latter pushing
   further toward models that can autonomously shape their learning
   objectives. This shift has implications for economic scalability, as well
   as potential risks around model alignment and oversight.

5. Empirical Rigor and Benchmarks:
   All papers emphasize large-scale empirical evaluation, thorough
   benchmarking against existing baselines, and practical implications (e.g.,
   resource tradeoffs, real-world tasks). The field is moving toward more
   grounded, reproducible research that informs not only theoretical
   development but decisions around model deployment and development
   lifecycles.

In summary, contemporary AI/ML research is converging on scalable model
development, architectural efficiency, improved alignment (both human-guided
and self-supervised), and bridging successful learning frameworks between
modalities. There is an ongoing move toward reducing training costs—both
computational and human—while maintaining or advancing model performance,
safety, and generalizability.
======
Task pipeline_task_6 completed successfully (quality score: 97).
Task literature_analysis completed:
Result: --- Task pipeline_task_0 Result ---
[Paper 1]
Title: "Scaling Laws for Generative Language Models Revisited"
Authors: Ethan Dyer, Xuezhi Wang, Jeffrey Wu, et al.
Description: This paper provides an up...

[TIME] Execution time: 66.42 seconds

============================================================
Pipeline Example Summary
============================================================
Pipeline pattern demonstrated:
  ✓ FORK-JOIN: Single task → 5 parallel processing → 1 synthesis
  ✓ PARALLEL SCALING: Easy adjustment of parallel worker count
  ✓ DEPENDENCY CHAINS: Automatic synchronization and dependency resolution
  ✓ STRUCTURED OUTPUT: Using [markers] for smart task distribution

Technical features:
  • Pipeline mode with pipeline_fork() and pipeline_join()
  • Automatic worker assignment and task routing
  • Multi-agent parallel coordination
  • Structured task dependencies

Pipeline example completed successfully!
"""
