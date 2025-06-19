---
title: "Datagen"
description: "CAMEL’s data generation modules for high-quality, instruction-tuned, and reasoning-rich datasets."
icon: arrow-progress
---

This page introduces CAMEL's **data generation modules** for creating high-quality training data with explicit reasoning, diverse instructions, and advanced automated refinement.

- **Chain of Thought (CoT):** Generates explicit reasoning paths
- **Self-Instruct:** Produces instruction-following data from both humans and machines
- **Source2Synth:** Synthesizes multi-hop QA from source text or code
- **Self-Improving CoT:** Iteratively improves reasoning through agent self-critique

## Chain of Thought (CoT) Data Generation

<Note type="info" title="What is CoT?">
  Chain of Thought (CoT) data generation creates step-by-step reasoning paths for problem solving, leveraging dual agents and advanced search/verification logic.
</Note>

<AccordionGroup>
<Accordion title = "Key Features">

- Monte Carlo Tree Search (MCTS) for solution exploration
- Binary Search Error Detection for precise error localization
- Dual-Agent Verification System for quality assurance
- Solution Tree Management for tracking reasoning paths
</Accordion>
<Accordion title="Core Components">

**CoTDataGenerator Class** 

The main class that implements the CoT generation system with the following capabilities:

- **Dual-Agent Architecture**: Supports both single-agent (legacy) and dual-agent modes
- **Answer Generation**: Sophisticated answer generation with MCTS
- **Answer Verification**: Robust verification system using golden answers
- **Error Detection**: Binary search-based error detection in solutions
- **Solution Management**: Comprehensive solution tree management and export
</Accordion>
</AccordionGroup>

<Card icon="zap" title="Quick Start: CoT Data Generation" className="my-6">
  Spin up chain-of-thought data generation with dual agents, golden answers, and CoT solution generation:

  ```python
  from camel.agents import ChatAgent
  from camel.datagen import CoTDataGenerator

  # Initialize agents
  generator_agent = ChatAgent("System message for generator")
  verifier_agent = ChatAgent("System message for verifier")

  # Define golden answers
  golden_answers = {
      "question1": "answer1",
      "question2": "answer2"
  }

  # Create generator
  cot_generator = CoTDataGenerator(
      generator_agent=generator_agent,
      verifier_agent=verifier_agent,
      golden_answers=golden_answers,
      search_limit=100
  )

  # Generate solution
  solution = cot_generator.solve("question1")
  ```
</Card>

<Card icon="database" title="Data Import/Export for CoT" className="my-6">
  Easily import question-answer pairs or export generated solutions for further use:

  ```python
  # Import QA pairs from JSON
  cot_generator.import_qa_from_json("qa_pairs.json")

  # Export solutions
  cot_generator.export_solutions("solutions.json")
  ```
</Card>


<AccordionGroup>

<Accordion title = "Solution Generation Process">

    <Steps>
      <Step title="Direct Solution Attempt">
        First, the agent attempts to solve the problem directly and checks the result against the golden answer for correctness.
      </Step>
      <Step title="MCTS-Based Exploration">
        If the direct attempt fails, a Monte Carlo Tree Search (MCTS) explores alternative reasoning paths, building a solution tree from previous attempts.
      </Step>
      <Step title="Error Detection & Correction">
        Binary search is used to efficiently pinpoint and isolate errors in the solution. New solutions are then generated, reusing verified-correct parts.
      </Step>
      <Step title="Solution Verification">
        All candidate solutions are strictly verified using a dual-agent system or comparison against golden answers to ensure high quality and accuracy.
      </Step>
    </Steps>
    </Accordion>
  <Accordion title="Configuration Options">
    <ul>
      <li><code>search_limit</code>: Maximum number of search iterations (default: <b>100</b>)</li>
      <li><code>generator_agent</code>: Specialized agent for answer generation</li>
      <li><code>verifier_agent</code>: Specialized agent for answer verification</li>
      <li><code>golden_answers</code>: Pre-defined correct answers for validation</li>
    </ul>
  </Accordion>
  <Accordion title="Output Format">
    The solution tree is exported in <b>JSON format</b> containing:
    <ul>
      <li>Solutions with intermediate steps</li>
      <li>Golden answers used for verification</li>
      <li>Export timestamp</li>
      <li>Solution scores and verification results</li>
    </ul>
  </Accordion>
</AccordionGroup>

---

## Self-Instruct: Instruction Generation

<Note type="info" title="What is Self-Instruct?">
  Self-Instruct is a pipeline for generating high-quality, diverse instructions by combining human-written seed tasks and machine-generated prompts, all filtered for quality and diversity.
</Note>

<AccordionGroup>
  <Accordion title="Key Features">
    <ul>
      <li>Combines human-written and machine-generated instructions using configurable ratios</li>
      <li>Supports both classification and non-classification task types</li>
      <li>Built-in instruction filtering and validation</li>
      <li>Automatic instance generation for tasks</li>
      <li>JSON-based data input/output</li>
    </ul>
  </Accordion>
  <Accordion title="Core Components">
    <b>SelfInstructPipeline</b> – Orchestrates the end-to-end instruction generation, mixing seeds and machine prompts, filtering, and outputting results.<br/>
    <br/>
    <b>InstructionFilter</b> – Handles validation and filtering of all generated instructions:<br/>
    <ul>
      <li>Length-based, keyword, and punctuation checks</li>
      <li>Non-English text detection</li>
      <li>ROUGE similarity filtering for deduplication</li>
      <li>Extensible registry for custom filters</li>
    </ul>
  </Accordion>
</AccordionGroup>

<Card icon="zap" title="Quick Start: Self-Instruct Generation" className="my-6">
  Quickly set up an instruction generation pipeline with both human and machine prompts:

  ```python
  from camel.agents import ChatAgent
  from camel.datagen.self_instruct import SelfInstructPipeline

  # Initialize agent
  agent = ChatAgent()

  # Create pipeline with default settings
  pipeline = SelfInstructPipeline(
      agent=agent,
      seed='seed_tasks.jsonl',  # Path to human-written seed tasks
      num_machine_instructions=5,
      data_output_path='./data_output.json',
      human_to_machine_ratio=(6, 2)
  )

  # Generate instructions
  pipeline.generate()
  ```
</Card>

<Card icon="filter" title="Custom Filtering Example" className="my-6">
  Use custom filters to refine and deduplicate instructions as needed:

  ```python
  from camel.datagen.self_instruct import SelfInstructPipeline
  from camel.datagen.self_instruct.filter import InstructionFilter

  # Configure filters
  filter_config = {
      "length": {},
      "keyword": {},
      "punctuation": {},
      "non_english": {},
      "rouge_similarity": {
          "threshold": 0.7,
          "metric": "rouge-l"
      }
  }

  pipeline = SelfInstructPipeline(
      agent=agent,
      seed='seed_tasks.jsonl',
      instruction_filter=InstructionFilter(filter_config),
      num_machine_instructions=5
  )
  ```
</Card>

<AccordionGroup>
<Accordion title = "Pipeline Stages">

<Steps>
  <Step title="Seed Loading">
    Load and validate human-written instructions from JSONL file; initialize task storage.
  </Step>
  <Step title="Instruction Generation">
    Sample both human and machine tasks based on your chosen ratio, then generate new instructions with ChatAgent and apply filters.
  </Step>
  <Step title="Task Classification">
    Automatically determine if tasks are classification or not, and generate the right prompts for each type.
  </Step>
  <Step title="Instance Generation">
    Generate input-output pairs, format and parse instances, and apply quality filters.
  </Step>
  <Step title="Data Output">
    Save all generated instructions and their instances to JSON, with metadata and configuration details.
  </Step>
</Steps>
</Accordion>
  <Accordion title="Pipeline Parameters">
    <ul>
      <li><code>agent</code>: ChatAgent instance for generating instructions</li>
      <li><code>seed</code>: Path to human-written seed tasks in JSONL format</li>
      <li><code>num_machine_instructions</code>: Number of machine-generated instructions (default: 5)</li>
      <li><code>data_output_path</code>: Path for saving generated data (default: <code>./data_output.json</code>)</li>
      <li><code>human_to_machine_ratio</code>: Ratio of human to machine tasks (default: <b>(6, 2)</b>)</li>
      <li><code>instruction_filter</code>: Custom <code>InstructionFilter</code> instance (optional)</li>
      <li><code>filter_config</code>: Configuration dictionary for default filters (optional)</li>
    </ul>
  </Accordion>
  <Accordion title="Filter Configuration">
    The default filter configuration supports:
    <ul>
      <li><b>length</b>: Configure length constraints for instructions</li>
      <li><b>keyword</b>: Set up keyword-based filtering rules</li>
      <li><b>punctuation</b>: Define punctuation validation rules</li>
      <li><b>non_english</b>: Non-English text detection</li>
      <li><b>rouge_similarity</b>: Set ROUGE similarity thresholds for deduplication</li>
    </ul>
  </Accordion>
<Accordion title="Input/Output Format">
    <b>Seed Tasks (Input):</b>
    ```json
    {"instruction": "Classify the sentiment of this text as positive or negative."}
    {"instruction": "Generate a summary of the given paragraph."}
    ```
    <b>Generated Data (Output):</b>
    ```json
    {
      "machine_instructions": [
        {
          "instruction": "...",
          "is_classification": true,
          "instances": [
            {
              "input": "...",
              "output": "..."
            }
          ]
        }
      ]
    }
    ```
  </Accordion>
</AccordionGroup>

---


## Source2Synth: Multi-hop Question-Answer Generation

<Note type="info" title="What is Source2Synth?">
  <b>Source2Synth</b> generates complex multi-hop QA pairs from source text (or code) via an orchestrated pipeline of AI-driven and rule-based steps, with curation and complexity control.
</Note>

<AccordionGroup>
  <Accordion title="Core Components">
    <b>UserDataProcessor</b>: Orchestrates the full pipeline, from raw text through QA generation and curation.<br/><br/>
    <b>ExampleConstructor</b>: Builds multi-hop QA examples, extracting premise, intermediate steps, and conclusions. <br/><br/>
    <b>DataCurator</b>: Filters, deduplicates, and samples the final dataset to match quality and complexity requirements.
  </Accordion>
  <Accordion title="Key Features">
    <ul>
      <li>Batch or single text processing</li>
      <li>Switchable AI or rule-based question generation</li>
      <li>Multi-hop QA and complexity scoring</li>
      <li>Integrated curation, deduplication, and reproducible sampling</li>
      <li>Seamless MultiHopGeneratorAgent integration</li>
    </ul>
  </Accordion>
</AccordionGroup>

<Card icon="zap" title="Quick Start: Source2Synth Pipeline" className="my-6">
  Rapidly generate a multi-hop QA dataset from your own text or source files:

  ```python
  from camel.datagen.source2synth import (
      UserDataProcessor,
      ProcessorConfig
  )

  # Create configuration
  config = ProcessorConfig(
      seed=42,
      min_length=50,
      max_length=1000,
      complexity_threshold=0.5,
      dataset_size=10,
      use_ai_model=True,
  )

  # Initialize processor
  processor = UserDataProcessor(config)

  # Process a single text
  result = processor.process_text(
      "Your source text here",
      source="example_source"
  )

  # Process multiple texts
  texts = ["Text 1", "Text 2", "Text 3"]
  sources = ["source1", "source2", "source3"]
  batch_results = processor.process_batch(texts, sources)
  ```
</Card>

<AccordionGroup>
  <Accordion title="ProcessorConfig Parameters">
    <ul>
      <li><code>seed</code>: Random seed for reproducibility</li>
      <li><code>min_length</code>: Minimum text length for processing</li>
      <li><code>max_length</code>: Maximum text length for processing</li>
      <li><code>complexity_threshold</code>: Minimum complexity score (0.0–1.0)</li>
      <li><code>dataset_size</code>: Target size for the final dataset</li>
      <li><code>use_ai_model</code>: Toggle between AI model and rule-based generation</li>
      <li><code>hop_generating_agent</code>: Custom <code>MultiHopGeneratorAgent</code> (optional)</li>
    </ul>
  </Accordion>
  <Accordion title="Pipeline Stages">
    <Steps>
      <Step title="Text Preprocessing">
        Validate text length and quality; standardize for processing.
      </Step>
      <Step title="Information Extraction">
        Identify premises, extract intermediate facts, and form conclusions.
      </Step>
      <Step title="QA Generation">
        Generate multi-hop questions, validate answers, and score for complexity.
      </Step>
      <Step title="Dataset Curation">
        Filter for quality, enforce complexity thresholds, deduplicate, and sample to target size.
      </Step>
    </Steps>
  </Accordion>
</AccordionGroup>


---

## Self-Improving CoT Data Generation

<Note type="info" title="What is Self-Improving CoT?">
  This pipeline implements <b>self-taught reasoning</b>—an iterative process where an AI agent refines its own reasoning traces via self-evaluation, feedback, and reward models for continual improvement.
</Note>

<AccordionGroup>
  <Accordion title="Key Components">
    <b>SelfImprovingCoTPipeline</b>: Implements the STaR (Self-Taught Reasoning) methodology, supporting both agent-based and external reward model evaluation, iterative feedback loops, and flexible output formats.<br/><br/>
    - Customizable reasoning and evaluation agents<br/>
    - Support for reward models and custom thresholds<br/>
    - Few-shot learning and rich output options
  </Accordion>
  <Accordion title="Architecture Stages">
    <Steps>
      <Step title="Initial Reasoning Trace Generation">
        The pipeline generates an initial reasoning path for each problem using the designated agent.
      </Step>
      <Step title="Self-Evaluation">
        An evaluator agent (or reward model) critically reviews each reasoning trace for quality, clarity, and correctness.
      </Step>
      <Step title="Feedback-Based Improvement">
        The system refines and re-generates reasoning steps using the evaluation feedback.
      </Step>
      <Step title="Iterative Refinement">
        This evaluation-feedback loop is repeated for a configurable number of iterations to reach optimal performance.
      </Step>
    </Steps>
  </Accordion>
</AccordionGroup>

<Card icon="zap" title="Quick Start: Self-Improving CoT Pipeline" className="my-6">
  Launch a self-improving reasoning workflow with just a few lines:

  ```python
  from camel.agents import ChatAgent
  from camel.datagen import SelfImprovingCoTPipeline

  # Initialize agents
  reason_agent = ChatAgent(
      """Answer my question and give your 
      final answer within \\boxed{}."""
  )

  evaluate_agent = ChatAgent(
      "You are a highly critical teacher who evaluates the student's answers "
      "with a meticulous and demanding approach."
  )

  # Prepare your problems
  problems = [
      {"problem": "Your problem text here"},
      # Add more problems...
  ]

  # Create and run the pipeline
  pipeline = SelfImprovingCoTPipeline(
      reason_agent=reason_agent,
      evaluate_agent=evaluate_agent,
      problems=problems,
      max_iterations=3,
      output_path="star_output.json"
  )

  results = pipeline.generate()
  ```
</Card>

<Card icon="trophy" title="Advanced: External Reward Model Integration" className="my-6">
  Evaluate and guide reasoning traces with an external reward model, such as Nemotron:

  ```python
  from camel.models.reward import NemotronRewardModel

  # Initialize reward model
  reward_model = NemotronRewardModel(
      model_type=ModelType.NVIDIA_NEMOTRON_340B_REWARD,
      url="https://integrate.api.nvidia.com/v1",
      api_key="your_api_key"
  )

  # Create pipeline with reward model
  pipeline = SelfImprovingCoTPipeline(
      reason_agent=reason_agent,
      evaluate_agent=evaluate_agent,
      problems=problems,
      reward_model=reward_model,
      score_threshold={
          "correctness": 0.8,
          "clarity": 0.7,
          "completeness": 0.7
      }
  )
  ```
</Card>

<AccordionGroup>
  <Accordion title="Input/Output Format">
    <b>Input Format (JSON):</b>
    ```json
    {
      "problems": [
        {
          "problem": "Problem text here",
          "solution": "Optional solution text"
        }
      ]
    }
    ```
    <b>Output Format (JSON):</b>
    <ul>
      <li>Original problem</li>
      <li>Final reasoning trace</li>
      <li>Improvement history with iterations</li>
      <li>Evaluation scores and feedback per iteration</li>
    </ul>
  </Accordion>
  <Accordion title="Configuration Options">
    <ul>
      <li><code>max_iterations</code>: Maximum number of improvement iterations (default: <b>3</b>)</li>
      <li><code>score_threshold</code>: Minimum quality thresholds for evaluation dimensions (default: <b>0.7</b>)</li>
      <li><code>few_shot_examples</code>: (Optional) Examples for few-shot learning</li>
      <li><code>output_path</code>: (Optional) Path for saving generated results</li>
    </ul>
  </Accordion>
</AccordionGroup>
