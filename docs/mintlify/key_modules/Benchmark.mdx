---
title: "BenchMarks"
description: "Learn about CAMEL's Benchmark module."
---

## Overview

The **Benchmark** module in CAMEL provides a framework for evaluating AI agents and language models across various tasks and domains. It includes implementations of multiple benchmarks and provides a interface for running evaluations, measuring performance, and generating detailed reports.

The module supports benchmarks for:

- **API calling and tool use** (APIBank, APIBench, Nexus)
- **General AI assistance** (GAIA)
- **Browser-based comprehension** (BrowseComp)
- **Retrieval-Augmented Generation** (RAGBench)

## Architecture

### Base Class: `BaseBenchmark`

All benchmarks inherit from the `BaseBenchmark` abstract class, which provides a common interface for downloading data, loading datasets, running evaluations, and accessing results.

#### BaseBenchmark Methods

| Method       | Description                  | Parameters                                                                                                                                       |
| ------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `__init__()` | Initialize the benchmark     | `name`: Benchmark name<br>`data_dir`: Data directory path<br>`save_to`: Results save path<br>`processes`: Number of parallel processes           |
| `download()` | Download benchmark data      | None                                                                                                                                             |
| `load()`     | Load benchmark data          | `force_download`: Force re-download                                                                                                              |
| `run()`      | Run the benchmark evaluation | `agent`: ChatAgent to evaluate<br>`on`: Data split ("train", "valid", "test")<br>`randomize`: Shuffle data<br>`subset`: Limit number of examples |
| `train`      | Get training data            | None                                                                                                                                             |
| `valid`      | Get validation data          | None                                                                                                                                             |
| `test`       | Get test data                | None                                                                                                                                             |
| `results`    | Get evaluation results       | None                                                                                                                                             |

## Available Benchmarks

### 1. GAIA Benchmark

**GAIA (General AI Assistants)** is a benchmark for evaluating general-purpose AI assistants on real-world tasks requiring multiple steps, tool use, and reasoning.

### 2. APIBank Benchmark

**APIBank** evaluates the ability of LLMs to make correct API calls and generate appropriate responses in multi-turn conversations.

### 3. APIBench Benchmark

**APIBench (Gorilla)** tests the ability to generate correct API calls for various machine learning frameworks (HuggingFace, TensorFlow Hub, Torch Hub).

### 4. Nexus Benchmark

**Nexus** evaluates function calling capabilities across multiple domains including security APIs, location services, and climate data.

#### Available Tasks

| Task                         | Description                   |
| ---------------------------- | ----------------------------- |
| `"NVDLibrary"`               | CVE and CPE API calls         |
| `"VirusTotal"`               | Malware and security analysis |
| `"OTX"`                      | Open Threat Exchange API      |
| `"PlacesAPI"`                | Location and mapping services |
| `"ClimateAPI"`               | Weather and climate data      |
| `"VirusTotal-ParallelCalls"` | Multiple parallel API calls   |
| `"VirusTotal-NestedCalls"`   | Nested API calls              |
| `"NVDLibrary-NestedCalls"`   | Nested CVE/CPE calls          |

### 5. BrowseComp Benchmark

**BrowseComp** evaluates browser-based comprehension by testing agents on questions that require understanding web content.

### 6. RAGBench Benchmark

**RAGBench** evaluates Retrieval-Augmented Generation systems using context relevancy and faithfulness metrics.

#### Available Subsets

| Subset       | Description                                        |
| ------------ | -------------------------------------------------- |
| `"hotpotqa"` | Multi-hop question answering                       |
| `"covidqa"`  | COVID-19 related questions                         |
| `"finqa"`    | Financial question answering                       |
| `"cuad"`     | Contract understanding                             |
| `"msmarco"`  | Microsoft Machine Reading Comprehension            |
| `"pubmedqa"` | Biomedical questions                               |
| `"expertqa"` | Expert-level questions                             |
| `"techqa"`   | Technical questions                                |
| Others       | `"emanual"`, `"delucionqa"`, `"hagrid"`, `"tatqa"` |

## Common Usage Pattern

All benchmarks follow a similar pattern:

```python
from camel.benchmarks import <BenchmarkName>
from camel.agents import ChatAgent

# 1. Initialize
benchmark = <BenchmarkName>(
    data_dir="./data",
    save_to="./results.json",
    processes=4
)

# 2. Load data
benchmark.load(force_download=False)

# 3. Create agent
agent = ChatAgent(...)

# 4. Run evaluation
results = benchmark.run(
    agent=agent,
    # benchmark-specific parameters
    randomize=False,
    subset=None  # or number of examples
)

# 5. Access results
print(results)  # Summary metrics
print(benchmark.results)  # Detailed per-example results
```

## Implementing Custom Benchmarks

To create a custom benchmark, inherit from `BaseBenchmark` and implement:

1. `download()`: Download benchmark data
2. `load()`: Load data into `self._data` dictionary
3. `run()`: Execute benchmark and populate `self._results`
4. Optional: Override `train`, `valid`, `test` properties

## References

- **GAIA**: https://huggingface.co/datasets/gaia-benchmark/GAIA
- **APIBank**: https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank
- **APIBench (Gorilla)**: https://huggingface.co/datasets/gorilla-llm/APIBench
- **Nexus**: https://huggingface.co/collections/Nexusflow/nexusraven-v2
- **BrowseComp**: https://openai.com/index/browsecomp/
- **RAGBench**: https://arxiv.org/abs/2407.11005

## Other Resources

- Explore the [Agents](./agents.md) module for creating custom agents
