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
Pipeline Workflow Example - Comprehensive demonstration of CAMEL Workforce Pipeline functionality.

This example demonstrates all the Pipeline features of CAMEL Workforce:
1. Sequential task chains
2. Parallel task execution
3. Task synchronization and joining
4. Different pipeline building approaches
5. Auto-dependency inference
6. Manual dependency specification
7. Complex workflow patterns

The example simulates a market analysis workflow with data collection,
parallel analysis, and report generation.
"""

import asyncio
import time
from typing import Dict, Any

from colorama import Fore, Style, init

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce import (
    PipelineTaskBuilder, 
    Workforce, 
    WorkforceMode,
    SingleAgentWorker
)
from camel.tasks import Task
from camel.toolkits import SearchToolkit, ThinkingToolkit
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage

# Initialize colorama for colored output
init(autoreset=True)

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

async def example_1_simple_sequential_pipeline():
    """Example 1: Simple sequential pipeline using chain methods."""
    print_section("Example 1: Simple Sequential Pipeline")
    
    # Create workforce with simple workers
    workforce = Workforce("Sequential Analysis Team")
    
    # Add some basic workers
    data_collector = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Data Collector",
            content="You are a data collector. Collect and organize market data efficiently."
        )
    )
    
    data_processor = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Data Processor", 
            content="You are a data processor. Clean and process raw data for analysis."
        )
    )
    
    report_generator = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Report Generator",
            content="You are a report generator. Create comprehensive reports from processed data."
        )
    )
    
    workforce.add_single_agent_worker("Data Collector", data_collector)
    workforce.add_single_agent_worker("Data Processor", data_processor)
    workforce.add_single_agent_worker("Report Generator", report_generator)
    
    # Build pipeline using chain methods
    workforce.add_pipeline_task("Collect current market data for technology stocks").then_pipeline("Clean and validate the collected market data").then_pipeline("Generate a summary report of technology stock trends").finalize_pipeline()
    
    print(f"{Fore.YELLOW}Pipeline built with 3 sequential tasks")
    print(f"{Fore.YELLOW}Mode: {workforce.mode}")
    
    # Execute the pipeline
    main_task = Task(
        content="Technology Stock Market Analysis Pipeline",
        id="sequential_analysis"
    )
    
    start_time = time.time()
    result = await workforce.process_task_async(main_task)
    end_time = time.time()
    
    print_result(result.id, result.result or "Pipeline completed successfully")
    print(f"{Fore.BLUE}[TIME] Execution time: {end_time - start_time:.2f} seconds")
    
    return result

async def example_2_parallel_and_sync():
    """Example 2: Parallel tasks with synchronization."""
    print_section("Example 2: Parallel Tasks with Synchronization")
    
    # Create workforce with specialized workers
    workforce = Workforce("Parallel Analysis Team")
    
    # Add specialized workers for different analysis types
    workers = [
        ("Data Collector", "You collect and organize financial market data."),
        ("Technical Analyst", "You perform technical analysis on stock charts and indicators."),
        ("Fundamental Analyst", "You analyze company fundamentals and financial statements."),
        ("Sentiment Analyst", "You analyze market sentiment and news impact."),
        ("Report Synthesizer", "You synthesize multiple analyses into comprehensive reports.")
    ]
    
    for role, description in workers:
        agent = ChatAgent(
            BaseMessage.make_assistant_message(role_name=role, content=description),
            tools=[*ThinkingToolkit().get_tools()]
        )
        workforce.add_single_agent_worker(role, agent)
    
    # Build pipeline with parallel analysis
    workforce.add_pipeline_task("Collect comprehensive market data for AAPL, GOOGL, and MSFT").fork_pipeline([
        "Perform technical analysis on collected stock data using indicators",
        "Conduct fundamental analysis of company financial health",
        "Analyze market sentiment and recent news impact"
    ]).join_pipeline("Synthesize all analyses into a comprehensive investment report").finalize_pipeline()
    
    print(f"{Fore.YELLOW}Pipeline built with 1 initial task, 3 parallel tasks, and 1 sync task")
    print(f"{Fore.YELLOW}Mode: {workforce.mode}")
    
    # Execute the pipeline
    main_task = Task(
        content="Comprehensive Stock Analysis Pipeline",
        id="parallel_analysis"
    )
    
    start_time = time.time()
    result = await workforce.process_task_async(main_task)
    end_time = time.time()
    
    print_result(result.id, result.result or "Parallel pipeline completed successfully")
    print(f"{Fore.BLUE}[TIME] Execution time: {end_time - start_time:.2f} seconds")
    
    return result

async def example_3_direct_pipeline_builder():
    """Example 3: Using PipelineTaskBuilder directly."""
    print_section("Example 3: Direct PipelineTaskBuilder Usage")
    
    # Create workforce
    workforce = Workforce("Direct Builder Team")
    
    # Add workers
    for i, role in enumerate(["Researcher", "Analyst", "Writer", "Reviewer"]):
        agent = ChatAgent(
            BaseMessage.make_assistant_message(
                role_name=role,
                content=f"You are a {role.lower()} specializing in market research."
            )
        )
        workforce.add_single_agent_worker(f"{role} {i+1}", agent)
    
    # Use PipelineTaskBuilder directly for more control
    builder = PipelineTaskBuilder()
    
    # Build a complex pipeline with explicit dependencies
    research_id = builder.add_task(
        "Research emerging technology trends and market opportunities",
        "research_task"
    )
    
    analysis_ids = builder.add_parallel_tasks(
        [
            "Analyze market size and growth potential",
            "Assess competitive landscape and key players",
            "Evaluate technology adoption trends"
        ],
        dependencies=[research_id],
        task_id_prefix="analysis"
    )
    
    synthesis_id = builder.add_sync_point(
        "Synthesize research and analysis into key insights",
        wait_for=analysis_ids,
        task_id="synthesis"
    )
    
    builder.add_task(
        "Write a comprehensive market opportunity report",
        "final_report",
        dependencies=[synthesis_id]
    )
    
    # Build and set tasks
    tasks = builder.build()
    workforce.set_pipeline_tasks(tasks)
    
    print(f"{Fore.YELLOW}Pipeline built with PipelineTaskBuilder")
    print(f"{Fore.YELLOW}Tasks: {len(tasks)}")
    print(f"{Fore.YELLOW}Mode: {workforce.mode}")
    
    # Show task information
    task_info = builder.get_task_info()
    print(f"{Fore.CYAN}Pipeline structure:")
    for task in task_info["tasks"]:
        deps = ", ".join(task["dependencies"]) if task["dependencies"] else "None"
        print(f"  {Fore.WHITE}{task['id']}: {task['content'][:50]}... (deps: {deps})")
    
    # Execute the pipeline
    main_task = Task(
        content="Technology Market Opportunity Analysis",
        id="direct_builder_analysis"
    )
    
    start_time = time.time()
    result = await workforce.process_task_async(main_task)
    end_time = time.time()
    
    print_result(result.id, result.result or "Direct builder pipeline completed successfully")
    print(f"{Fore.BLUE}[TIME] Execution time: {end_time - start_time:.2f} seconds")
    
    return result

async def example_4_complex_workflow():
    """Example 4: Complex workflow with multiple branches and joins."""
    print_section("Example 4: Complex Multi-Branch Workflow")
    
    # Create a larger workforce for complex analysis
    workforce = Workforce("Complex Analysis Workforce", mode=WorkforceMode.PIPELINE)
    
    # Add various specialized workers
    worker_configs = [
        ("Market Researcher", "You research market trends and collect data."),
        ("Risk Analyst", "You analyze financial and market risks."),
        ("Growth Analyst", "You analyze growth potential and opportunities."),
        ("Tech Analyst", "You analyze technology trends and innovations."),
        ("Competitive Analyst", "You analyze competitive landscapes."),
        ("Financial Modeler", "You create financial models and projections."),
        ("Strategy Consultant", "You develop strategic recommendations."),
        ("Report Writer", "You write comprehensive business reports.")
    ]
    
    for role, description in worker_configs:
        agent = ChatAgent(
            BaseMessage.make_assistant_message(role_name=role, content=description)
        )
        workforce.add_single_agent_worker(role, agent)
    
    # Build complex pipeline
    workforce.add_pipeline_task("Gather comprehensive market and industry data").fork_pipeline([
        "Analyze market risks and potential challenges",
        "Analyze growth opportunities and market potential",
        "Analyze technology trends and innovations"
    ]).join_pipeline("Synthesize initial market analysis findings").add_parallel_pipeline_tasks([
        "Conduct competitive landscape analysis",
        "Create financial projections and models"
    ]).add_sync_pipeline_task("Integrate competitive and financial analysis").then_pipeline("Develop strategic recommendations and action plan").then_pipeline("Write comprehensive strategic analysis report").finalize_pipeline()
    
    print(f"{Fore.YELLOW}Complex pipeline built with multiple parallel branches")
    print(f"{Fore.YELLOW}Mode: {workforce.mode}")
    
    # Execute the complex pipeline
    main_task = Task(
        content="Comprehensive Strategic Market Analysis",
        id="complex_workflow"
    )
    
    start_time = time.time()
    result = await workforce.process_task_async(main_task)
    end_time = time.time()
    
    print_result(result.id, result.result or "Complex workflow completed successfully")
    print(f"{Fore.BLUE}[TIME] Execution time: {end_time - start_time:.2f} seconds")
    
    return result

async def example_5_mode_comparison():
    """Example 5: Compare AUTO_DECOMPOSE vs PIPELINE modes."""
    print_section("Example 5: Mode Comparison")
    
    # Test task
    test_task = Task(
        content="Analyze the cryptocurrency market trends and provide investment recommendations",
        id="crypto_analysis"
    )
    
    # Create two identical workforces
    auto_workforce = Workforce("Auto Decompose Team", mode=WorkforceMode.AUTO_DECOMPOSE)
    pipeline_workforce = Workforce("Pipeline Team", mode=WorkforceMode.PIPELINE)
    
    # Add same workers to both
    for workforce_instance in [auto_workforce, pipeline_workforce]:
        for role in ["Crypto Analyst", "Market Researcher", "Investment Advisor"]:
            agent = ChatAgent(
                BaseMessage.make_assistant_message(
                    role_name=role,
                    content=f"You are a {role.lower()} specializing in cryptocurrency markets."
                )
            )
            workforce_instance.add_single_agent_worker(role, agent)
    
    # Set up pipeline for pipeline workforce
    pipeline_workforce.add_pipeline_task("Research current cryptocurrency market conditions").add_pipeline_task("Analyze major cryptocurrency trends and patterns").add_pipeline_task("Generate investment recommendations based on analysis").finalize_pipeline()
    
    print(f"{Fore.YELLOW}Testing AUTO_DECOMPOSE mode...")
    start_time = time.time()
    auto_result = await auto_workforce.process_task_async(test_task)
    auto_time = time.time() - start_time
    
    print(f"{Fore.YELLOW}Testing PIPELINE mode...")
    start_time = time.time()
    pipeline_result = await pipeline_workforce.process_task_async(test_task)
    pipeline_time = time.time() - start_time
    
    # Compare results
    print(f"\n{Fore.CYAN}Comparison Results:")
    print(f"{Fore.WHITE}AUTO_DECOMPOSE mode:")
    print(f"  Time: {auto_time:.2f}s")
    print(f"  Result length: {len(auto_result.result or '')}")
    print(f"  Status: {auto_result.state}")
    
    print(f"\n{Fore.WHITE}PIPELINE mode:")
    print(f"  Time: {pipeline_time:.2f}s") 
    print(f"  Result length: {len(pipeline_result.result or '')}")
    print(f"  Status: {pipeline_result.state}")
    
    return auto_result, pipeline_result

async def example_6_error_handling():
    """Example 6: Pipeline with error handling and recovery."""
    print_section("Example 6: Error Handling and Recovery")
    
    workforce = Workforce("Error Handling Team")
    
    # Add workers
    agent = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Resilient Analyst",
            content="You are an analyst who handles errors gracefully and provides alternative solutions."
        )
    )
    workforce.add_single_agent_worker("Resilient Analyst", agent)
    
    try:
        # Build pipeline with potential error scenarios
        workforce.add_pipeline_task("Attempt to access restricted financial data").then_pipeline("Process data even if some sources fail").then_pipeline("Generate report with available information and note limitations").finalize_pipeline()
        
        main_task = Task(
            content="Resilient Data Analysis Pipeline",
            id="error_handling_test"
        )
        
        result = await workforce.process_task_async(main_task)
        print_result(result.id, result.result or "Error handling pipeline completed")
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Pipeline failed with error: {e}")
        print(f"{Fore.YELLOW}This demonstrates error handling in pipeline execution")
    
    return result

def print_summary():
    """Print example summary."""
    print_section("Pipeline Workflow Examples Summary")
    
    examples = [
        "1. Simple Sequential Pipeline - Basic chain of dependent tasks",
        "2. Parallel Tasks with Sync - Fork/join pattern for parallel processing", 
        "3. Direct PipelineTaskBuilder - Advanced control with explicit dependencies",
        "4. Complex Multi-Branch - Multiple parallel branches with synchronization",
        "5. Mode Comparison - AUTO_DECOMPOSE vs PIPELINE performance",
        "6. Error Handling - Graceful failure handling in pipelines"
    ]
    
    print(f"{Fore.CYAN}Examples demonstrated:")
    for example in examples:
        print(f"{Fore.WHITE}  [CHECK] {example}")
    
    print(f"\n{Fore.GREEN}Key Pipeline Features:")
    features = [
        "[CHAIN] Chain methods: .add_pipeline_task().then_pipeline().fork_pipeline()",
        "[PARALLEL] Parallel execution: .fork_pipeline() and .add_parallel_pipeline_tasks()",
        "[SYNC] Synchronization: .join_pipeline() and .add_sync_pipeline_task()",
        "[AUTO] Auto-dependency: Automatic inference of task dependencies",
        "[MANUAL] Manual control: Explicit dependency specification when needed",
        "[BUILDER] Builder access: Direct PipelineTaskBuilder usage for advanced scenarios",
        "[MODE] Mode switching: Automatic PIPELINE mode activation",
        "[ERROR] Error handling: Graceful failure recovery and reporting"
    ]
    
    for feature in features:
        print(f"{Fore.WHITE}  {feature}")

async def main():
    """Main function to run all pipeline examples."""
    print_section("CAMEL Workforce Pipeline Examples")
    print(f"{Fore.YELLOW}This script demonstrates comprehensive Pipeline functionality in CAMEL Workforce.")
    print(f"{Fore.YELLOW}Each example shows different patterns and capabilities.")
    
    results = {}
    
    try:
        # Run all examples
        print(f"\n{Fore.BLUE}Running all pipeline examples...")
        
        results['sequential'] = await example_1_simple_sequential_pipeline()
        results['parallel'] = await example_2_parallel_and_sync()
        results['direct_builder'] = await example_3_direct_pipeline_builder()
        results['complex'] = await example_4_complex_workflow()
        results['comparison'] = await example_5_mode_comparison()
        results['error_handling'] = await example_6_error_handling()
        
        print_summary()
        
        print(f"\n{Fore.GREEN}[SUCCESS] All pipeline examples completed successfully!")
        print(f"{Fore.CYAN}Total examples run: {len(results)}")
        
    except Exception as e:
        print(f"\n{Fore.RED}[ERROR] Error running examples: {e}")
        raise
    
    return results

if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())