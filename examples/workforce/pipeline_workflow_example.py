#!/usr/bin/env python3
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
Pipeline Workflow Example - Demonstration of CAMEL Workforce Pipeline functionality.

This example demonstrates the fork-join pattern in CAMEL Workforce Pipeline mode:
- Single source task (literature search)
- Fork to 5 parallel summarization tasks
- Join results into a comprehensive synthesis

The example shows how to handle parallel task processing where multiple agents 
work on different parts of the same data source with automatic synchronization.
"""

import asyncio
import time

from colorama import Fore, Style, init

from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce import Workforce, WorkforceMode
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage

# Initialize colorama for colored output
init(autoreset=True)

# Create model once for all agents
# model = ModelFactory.create(
#     model_platform=ModelPlatformType.DEFAULT,
#     model_type=ModelType.DEFAULT,
# )

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1,
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
    print(f"{Fore.WHITE}Result: {result[:200]}{'...' if len(result) > 200 else ''}")
    print()


async def example_1_literature_analysis_pipeline():
    """Example 1: Literature analysis with parallel summarization."""
    print_section("Example 1: Literature Analysis with Parallel Processing")
    
    # Create coordinator agent
    coordinator_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Literature Analysis Coordinator",
            content="You are a coordinator responsible for managing literature analysis tasks and ensuring quality output."
        ),
        model=model
    )
    
    # Create task agent using the same model
    task_agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Task Planning Agent",
            content="You are a task planning agent responsible for analyzing and coordinating complex tasks."
        ),
        model=model
    )
    
    # Create workforce for literature analysis
    workforce = Workforce(
        "Literature Analysis Team",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        mode=WorkforceMode.PIPELINE
    )
    
    # Add search agent with search tools (using mock data for demonstration)
    search_system_message = BaseMessage.make_assistant_message(
        role_name="Literature Researcher",
        content="You are a literature researcher. Provide 5 recent AI/ML papers with titles, authors, and brief descriptions. Format them as [Paper 1], [Paper 2], etc. Use representative examples from recent AI/ML research."
    )
    search_agent = ChatAgent(
        system_message=search_system_message,
        model=model,
        tools=[]
    )
    
    # Add multiple summary agents for parallel processing
    for i in range(5):
        summary_system_message = BaseMessage.make_assistant_message(
            role_name=f"Summary Specialist {i+1}",
            content="You are a literature summary specialist. Focus on extracting key insights, methodologies, and contributions from research papers."
        )
        summary_agent = ChatAgent(
            system_message=summary_system_message,
            model=model,
            tools=[]
        )
        workforce.add_single_agent_worker(f"Summary Specialist {i+1}", summary_agent)
    
    # Add synthesis agent
    synthesis_system_message = BaseMessage.make_assistant_message(
        role_name="Research Synthesizer",
        content="You are a research synthesizer. Combine multiple literature summaries into comprehensive analysis and identify research trends."
    )
    synthesis_agent = ChatAgent(
        system_message=synthesis_system_message,
        model=model,
        tools=[]
    )
    
    workforce.add_single_agent_worker("Literature Researcher", search_agent)
    workforce.add_single_agent_worker("Research Synthesizer", synthesis_agent)
    
    # Build literature analysis pipeline
    workforce.pipeline_add("Generate 5 representative recent AI/ML papers with titles, authors, and brief descriptions. Format as [Paper 1] to [Paper 5]") \
             .pipeline_fork([
                 "Summarize [Paper 1] core insights, methodology and contributions",
                 "Summarize [Paper 2] core insights, methodology and contributions", 
                 "Summarize [Paper 3] core insights, methodology and contributions",
                 "Summarize [Paper 4] core insights, methodology and contributions",
                 "Summarize [Paper 5] core insights, methodology and contributions"
             ]) \
             .pipeline_join("Analyze AI/ML research trends based on the 5 paper summaries") \
             .pipeline_build()
    
    print(f"{Fore.YELLOW}Literature analysis pipeline built: 1 search → 5 parallel summaries → 1 synthesis")
    print(f"{Fore.YELLOW}Mode: {workforce.mode}")
    
    # Execute the pipeline
    main_task = Task(
        content="AI/ML Literature Review and Trend Analysis",
        id="literature_analysis"
    )
    
    start_time = time.time()
    result = await workforce.process_task_async(main_task)
    end_time = time.time()
    
    print_result(result.id, result.result or "Literature analysis completed successfully")
    print(f"{Fore.BLUE}[TIME] Execution time: {end_time - start_time:.2f} seconds")
    
    return result

def print_summary():
    """Print example summary."""
    print_section("Pipeline Example Summary")
    
    print(f"{Fore.GREEN}Pipeline pattern demonstrated:")
    patterns = [
        "✓ FORK-JOIN: Single task → 5 parallel processing → 1 synthesis",
        "✓ PARALLEL SCALING: Easy adjustment of parallel worker count",
        "✓ DEPENDENCY CHAINS: Automatic synchronization and dependency resolution",
        "✓ STRUCTURED OUTPUT: Using [markers] for smart task distribution"
    ]
    
    for pattern in patterns:
        print(f"{Fore.WHITE}  {pattern}")
    
    print(f"\n{Fore.CYAN}Technical features:")
    tech_features = [
        "• Pipeline mode with pipeline_fork() and pipeline_join()",
        "• Automatic worker assignment and task routing",
        "• Multi-agent parallel coordination",
        "• Structured task dependencies"
    ]
    
    for feature in tech_features:
        print(f"{Fore.WHITE}  {feature}")

async def main():
    """Main function to run pipeline example."""
    print_section("CAMEL Workforce Pipeline Example")
    print(f"{Fore.YELLOW}Testing Pipeline mode with fork-join pattern and parallel processing.")
    
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
Literature analysis pipeline built: 1 search → 5 parallel summaries → 1 synthesis    
Mode: WorkforceMode.PIPELINE
Worker node f6cd7177-2d02-4398-bd78-3116b0807db4 (Literature Researcher) get task pipeline_task_0: Generate 5 representative recent AI/ML papers with titles, authors, and brief descriptions. Format as [Paper 1] to [Paper 5]
======
Response from Worker node f6cd7177-2d02-4398-bd78-3116b0807db4 (Literature Researcher):

[Paper 1]
"Gemini: A Family of Highly Capable Multimodal Models"
Authors: Google DeepMind (Peter Barham, Jeff Dean, et al.)
Description: Introduces the Gemini family of large language models designed for multimodal reasoning across text, images, audio, and video. Highlights performance surpassing prior state-of-the-art on multiple multimodal and language understanding benchmarks.

[Paper 2]
"LLM-Augmented Learning: Enhancing Data Quality via Iterative Refinement"
Authors: Kaixuan Zhang, Luyu Wang, Wenjuan Han, et al. (Microsoft Research)
Description: Explores the use of large language models (LLMs) for data cleaning and augmentation via iterative refinement, showing improved downstream model performance on NLP tasks with noisy data.

[Paper 3]
"MEGAVERSE: Benchmarking Foundation Models for Autonomous Agents"
Authors: Jun Shern Chan, Kevin F. Le, Yilun Du, et al. (MIT, Stanford, Google DeepMind)
Description: Presents MEGAVERSE, a new benchmark suite for evaluating how well foundation models can power general autonomous agents, across virtual environments and tasks.

[Paper 4]
"Qwen-VL: A Versatile Vision-Language Model based on Large Language Models"
Authors: Alibaba DAMO Academy (Jianfei Chen, Yuheng Xie, et al.)
Description: Introduces Qwen-VL, a powerful open-source multimodal model capable of advanced image and document understanding, outperforming previous vision-language models of similar scale.

[Paper 5]
"Eagle: Layer-wise Fine-tuning of Foundation Models"
Authors: Xinyi Xu, Jindong Wang, Wenxin Hou, et al. (Microsoft Research)
Description: Proposes a new fine-tuning approach for large foundation models, showing that targeted layer-wise updates can achieve high performance with lower computational cost, and improving knowledge transfer across tasks.
======
Task pipeline_task_0 completed successfully (quality score: 100).
Worker node 5d4ea69d-eb97-4091-8ebb-c073ca555048 (Summary Specialist 2) get task parallel_1_1: Summarize [Paper 2] core insights, methodology and contributions
Worker node cbf6bda1-c9c2-42f2-a9e3-115010772117 (Summary Specialist 4) get task parallel_3_1: Summarize [Paper 4] core insights, methodology and contributions
Worker node 5299ade7-751b-4037-9b64-cfc134a3347c (Summary Specialist 1) get task parallel_0_1: Summarize [Paper 1] core insights, methodology and contributions
Worker node e28830f2-3ee7-43ca-b2b6-30b2d287f329 (Summary Specialist 5) get task parallel_4_1: Summarize [Paper 5] core insights, methodology and contributions
Worker node d71aeebb-93bb-4c87-9990-826b5ccf97e3 (Summary Specialist 3) get task parallel_2_1: Summarize [Paper 3] core insights, methodology and contributions
======
Response from Worker node cbf6bda1-c9c2-42f2-a9e3-115010772117 (Summary Specialist 4):

Core Insights: Qwen-VL introduces a highly capable open-source vision-language model that demonstrates advanced performance in both image and document understanding tasks. It outperforms previous vision-language models of similar scale, showcasing strong generalization and multimodal reasoning abilities.

Methodology: The authors design Qwen-VL by building on large language model (LLM) architectures and augmenting them to handle multimodal inputs (images and text). The model is trained on large-scale, carefully curated vision-language datasets, utilizing both supervised and self-supervised objectives. Key methodological advances include the alignment of visual and textual representations, multimodal attention mechanisms, and strategies for robust cross-modal understanding such as unified embedding spaces and task-specific fine-tuning.

Contributions: (1) The introduction of a versatile and powerful open-source multimodal model (Qwen-VL) tailored for vision-language understanding; (2) Comprehensive evaluation showing the model outperforms previous state-of-the-art vision-language models of comparable scale on a variety of image and document understanding benchmarks; (3) Release of model weights and code, contributing valuable resources for the research community and enabling further advancements in multimodal AI.
======
Task parallel_3_1 completed successfully (quality score: 98).
======
Response from Worker node e28830f2-3ee7-43ca-b2b6-30b2d287f329 (Summary Specialist 5):

Core Insights: [Paper 5] "Eagle: Layer-wise Fine-tuning of Foundation Models" introduces a novel approach to fine-tuning large foundation models by updating selected layers rather than the whole model. The core insight is that targeted, layer-wise updates can retain or surpass the performance of full-model fine-tuning while significantly reducing computational cost and memory requirements. This strategy also improves knowledge transfer across multiple tasks, making adaptation more efficient.

Methodology: The authors design an algorithm that identifies and fine-tunes specific layers of a foundation model, based on task requirements. Through empirical studies, they compare their method against full-model and other parameter-efficient fine-tuning approaches across various NLP tasks. Metrics such as task accuracy, training time, and resource consumption are thoroughly assessed.

Contributions: 1) Proposes a systematic, layer-wise fine-tuning method for large models. 2) Demonstrates that this approach substantially reduces computational overhead. 3) Shows improved or matched performance in multi-task scenarios compared to prior methods. 4) Provides comprehensive benchmarks and analysis, establishing a new practical avenue for efficient and effective model adaptation.
======
======
Response from Worker node 5d4ea69d-eb97-4091-8ebb-c073ca555048 (Summary Specialist 2):

Paper 2, titled "LLM-Augmented Learning: Enhancing Data Quality via Iterative Refinement" by Kaixuan Zhang, Luyu Wang, Wenjuan Han, et al. (Microsoft Research), explores the use of large language models (LLMs) to improve data quality for NLP tasks, with a particular emphasis on handling noisy datasets.

Core Insights: The key insight of the paper is that LLMs can be leveraged not just for downstream inference tasks, but as intelligent agents for data cleaning and augmentation. By iteratively refining the training data using LLM-generated suggestions, the quality of the dataset improves, which in turn leads to better model performance on downstream tasks, especially in the presence of noise or imperfect data.

Methodology: The authors introduce a framework where an LLM is employed to identify errors, inconsistencies, or ambiguities in training datasets. The LLM proposes corrections or improvements in an iterative loop, with human oversight or additional automated validation ensuring changes maintain or increase data integrity. This process is repeated, resulting in progressively cleaner datasets. The refined data is then used to train standard NLP models, and performance is evaluated on benchmark tasks to assess gains from the approach.

Contributions: The main contributions of this work are: (1) Proposing a novel use-case for LLMs as data quality improvers, not just as end-task predictors; (2) Demonstrating through experiments that iterative LLM-driven data refinement can lead to measurable improvements in downstream NLP model accuracy and robustness, particularly with initially noisy data; (3) Providing a framework adaptable to various NLP scenarios where data quality is a bottleneck. The paper offers empirical results that support these claims and discusses implications for scalable automated data curation.
======
Task parallel_4_1 completed successfully (quality score: 97).
Task parallel_1_1 completed successfully (quality score: 97).
======
Response from Worker node d71aeebb-93bb-4c87-9990-826b5ccf97e3 (Summary Specialist 3):

Core Insights: 'MEGAVERSE: Benchmarking Foundation Models for Autonomous Agents' introduces MEGAVERSE—a comprehensive benchmark suite aimed at systematically evaluating how foundation models (such as large language or multimodal models) serve as the backbone for general autonomous agents. The core insight is the need for a standardized, rigorous evaluation environment to measure the capabilities and limitations of foundation models when deployed in agentic, multi-domain scenarios.

Methodology: The paper constructs a varied suite of simulated virtual environments and tasks designed to reflect real-world agent challenges, encompassing navigation, manipulation, multi-step reasoning, and adaptation. It defines standardized tasks with clear, reproducible metrics for evaluation. Foundation models are integrated as the central reasoning or decision-making module for agents, whose behaviors are then assessed across diverse environments and task types. The benchmark measures factors such as generalization, instruction following, task completion, transfer learning, and emergent behaviors. Extensive experiments are conducted with multiple state-of-the-art foundation models (including LLMs and vision-language models) to ensure comprehensive coverage.

Contributions:
1. Proposes MEGAVERSE as the first broad benchmark tailored to test the agentic capabilities of foundation models.
2. Provides an open, extensible set of tasks and virtual worlds enabling systematic, reproducible evaluation and comparison.
3. Reveals critical strengths and limitations of existing foundation models when deployed as autonomous agents, informing future research directions on improving real-world agent generality.
4. Delivers thorough experimental results, establishing initial baselines and highlighting emergent patterns and performance gaps.
======
======
Response from Worker node 5299ade7-751b-4037-9b64-cfc134a3347c (Summary Specialist 1):

Paper: "Gemini: A Family of Highly Capable Multimodal Models"

Core Insights:
- The Gemini models represent a new generation of large-scale multimodal AI systems developed by Google DeepMind, designed to process and reason across multiple input modalities including text, images, audio, and video. These models achieve strong performance, surpassing previous state-of-the-art results on various multimodal and language understanding benchmarks.

Methodology:
- Gemini comprises a family of models trained using large-scale datasets spanning diverse modalities, enabling integrated vision, language, and audio understanding. Training leverages cross-modal objectives and alignment techniques, allowing the models to interpret, synthesize, and generate outputs across different types of inputs.       
- Rigorous benchmarking is conducted against prior state-of-the-art models, using standardized multimodal datasets and tasks to demonstrate capabilities in reasoning, comprehension, and generation.

Key Contributions:
1. Introduction of a scalable family of multimodal models (Gemini) capable of unified reasoning across text, image, audio, and video domains.
2. Empirical evidence showing Gemini’s superior performance on a wide range of multimodal and language benchmarks, establishing new performance records in several categories.
3. Advancements in multimodal training and alignment techniques, demonstrating how large language model principles can be generalized beyond text to rich, multi-sensory data.
4. An extensive evaluation framework and analysis that highlights both strengths and limitations, setting a new standard for multimodal model assessment.
======
Task parallel_2_1 completed successfully (quality score: 97).
Task parallel_0_1 completed successfully (quality score: 96).
Worker node c7d22a97-4127-4248-a818-a625c0f50862 (Research Synthesizer) get task pipeline_task_6: Analyze AI/ML research trends based on the 5 paper summaries
======
Response from Worker node c7d22a97-4127-4248-a818-a625c0f50862 (Research Synthesizer):

Analysis of recent AI/ML research trends based on the five paper summaries reveals several converging themes and emerging directions:

1. Multimodal Foundation Models: Two papers (Gemini, Qwen-VL) highlight rapid advancements in large-scale multimodal models capable of processing and reasoning across text, images, audio, and video. Researchers are pursuing unified architectures and alignment techniques to extend the capabilities of foundation models beyond single modalities, resulting in superior performance on a variety of benchmarks and tasks.

2. Systematic Benchmarking and Evaluation: The introduction of benchmark suites such as MEGAVERSE signals an increased emphasis on objective, reproducible assessment of AI models, particularly in evaluating general agentic capabilities across diverse and complex tasks. There is a clear trend towards establishing broad, flexible, and extensible benchmarks for both understanding and comparing the performance of foundation models in autonomous settings.

3. Efficient Model Adaptation and Fine-tuning: Resource-efficient techniques are gaining traction, as evidenced by the Eagle paper's focus on layer-wise fine-tuning. The goal is to maximize adaptability and knowledge transfer of large models while minimizing computational and memory costs, which has important implications for scaling and deploying AI systems in practice.

4. Data Quality and Model Robustness: The LLM-Augmented Learning paper introduces an innovative use of LLMs for iterative data refinement and cleaning, highlighting a growing recognition that high-quality data remains critical, especially as models become larger. Using advanced models to improve the data they learn from creates a virtuous cycle that enhances downstream robustness and reliability.

Research Trends:
- Unification and scalability of models across modalities is a major thrust, with both commercial (Gemini) and open-source (Qwen-VL) efforts driving the field forward.   
- Comprehensive, agent-centric benchmarking (MEGAVERSE) reflects the community's recognition of the need for systematic, real-world relevant evaluation tools.
- Methodological innovations targeting the efficiency of adaptation (Eagle) and data curation (LLM-Augmented Learning) strive to make large models more practical and accessible.
- There is a move toward openness, with the release of models and code (Qwen-VL) expected to accelerate research progress.
In summary, the current landscape is characterized by rapid progress in multimodal modeling, a maturing focus on standardization and reproducibility, and practical innovations addressing efficiency and data quality. These trends point toward more capable, robust, and accessible AI systems in the near future.
======
Task pipeline_task_6 completed successfully (quality score: 97).
Task literature_analysis completed:
Result: --- Task pipeline_task_0 Result ---
[Paper 1]
"Gemini: A Family of Highly Capable Multimodal Models"
Authors: Google DeepMind (Peter Barham, Jeff Dean, et al.)
Description: Introduces the Gemini famil...

[TIME] Execution time: 56.37 seconds

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

[TIME] Execution time: 56.37 seconds

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

  • Multi-agent parallel coordination
  • Structured task dependencies


Pipeline example completed successfully!
"""