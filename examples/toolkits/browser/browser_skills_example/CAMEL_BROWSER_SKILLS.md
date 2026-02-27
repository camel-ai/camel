# Browser Skills Framework Documentation

## Overview

CAMEL Browser Skills is a framework that automatically extracts, encapsulates, and reuses interaction patterns from successfully completed browser task executions.
The core concept is: **progressively transforming Agent's exploratory execution (Agent Loop) into deterministic workflow execution (Workflow)**, thereby significantly improving task success rates and reducing inference costs.

### Core Value

- **Improved Success Rate**: Reuse validated interaction patterns to avoid redundant exploration
- **Reduced Cost**: Minimize token consumption by elevating reasoning granularity from atomic operations to skill level
- **Continuous learning**: As tasks are executed, the skill library continuously enriches, and system capabilities keep improving

---

## Quick Start Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SIMPLE WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. EXTRACT: Log → Skills Folder                            │               │
│     ┌──────────────┐     cli/subtask_extractor.py  ┌──────────────────┐    │
│     │ session_logs │  ─────────────────────────►   │ skills_store/<web│    │
│     │ (raw logs)   │                               │ site>/*/SKILL.md │    │
│     └──────────────┘                               │ + actions.json   │    │
│                                                     └──────────────────┘    │
│                                                             │               │
│  2. USE: Load Skill → Execute                               │               │
│                                                             ▼               │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │  core/skill_agent.py (SkillsAgent)                              │    │
│     │    └── core/skill_loader.py → core/action_replayer.py           │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Framework Structure

```
browser_skills_example/
├── skills_store/                      # Generated skills (by website; default for WebVoyager)
│   ├── google_flights/
│   │   └── 001-.../ (SKILL.md + actions.json)
│   └── wolfram_alpha/
│       └── 001-.../ (SKILL.md + actions.json)
├── browser_skills/                    # Optional: bundled skill library (by website)
│   └── <website>/*/ (SKILL.md + actions.json)
│
├── core/                              # Core logic (importable modules)
│   ├── skill_agent.py                 # Main Agent (SkillsAgent)
│   ├── subtask_extractor.py           # Mine subtasks from logs
│   ├── skill_store.py                 # Persist extracted skills (SKILL.md + actions.json)
│   ├── skill_loader.py                # Load skills
│   └── action_replayer.py             # Replay actions (with Recovery Agent)
│
├── cli/                               # CLI thin wrappers
│   ├── run_webvoyager_tasks.py        # Batch testing (WebVoyager)
│   ├── run_single_case.py             # Run one task
│   ├── run_navi_bench_tasks.py        # Batch testing (Navi-Bench)
│   └── subtask_extractor.py           # Mine skills from a session folder
│
└── ../utils/utils.py                  # Shared helper functions (imported as `utils`)
```

---

## Core Components

### 1. Main Agent

**File**: `core/skill_agent.py`

The Main Agent is the core of task execution, responsible for:
- Receiving user tasks and planning execution strategies
- Deciding when to invoke existing Skills vs. executing atomic operations
- Coordinating Skill composition and parameter passing

### 2. Subtask Extractor (Task Agent)

**File**: `core/subtask_extractor.py` (CLI: `cli/subtask_extractor.py`)

The Task Agent analyzes successfully executed task logs and splits them into reusable subtasks:

1. **Extract consecutive action groups**: Identify consecutive atomic operations from `action_timeline.json`
2. **Semantic analysis**: Use LLM to analyze semantic boundaries of action sequences
3. **Subtask generation**: Generate for each subtask:
   - Natural language description
   - Configurable parameters (variables)
   - Execution preconditions

### 3. Recovery Agent

**File**: `core/action_replayer.py` (CLI: `cli/action_replayer.py`)

When element location fails during Skill replay, the Recovery Agent intervenes:

1. **Receive context**: Current page snapshot, target element's aria-label, failed action type
2. **Intelligent matching**: Analyze page structure, find semantically equivalent alternative elements
3. **Return decision**:
   - Return new element reference (e.g., `e149`)
   - Return `SKIP` (action no longer needed)
   - Return `NONE` (cannot find suitable element)

```python
# Recovery Agent workflow
result_ref = await replayer.agent_recovery(
    failed_action="click",
    target_label="Where from?",
    current_snapshot=page_snapshot,
    error_message="Element not found"
)
```

---

## Skill Format

### Directory Structure

Each skill contains a folder with two files:

```
enter-departure-location/
├── SKILL.md        # Skill definition
└── actions.json    # Action sequence
```

### SKILL.md Format

```yaml
---
name: enter-departure-location
id: 9
description: "Enter and confirm the departure city"
start_index: 5
end_index: 11
url_start: "https://www.google.com/travel/flights"
url_end: "https://www.google.com/travel/flights"
variables:
  departure_city:
    type: string
    default_value: "Edinburgh"
    description: "Name of the departure city"
    action_index: 9
    arg_position: 1
source:
  log_file: "../../session_logs/session_xxx/complete_browser_log.log"
  task_description: "Original task description..."
---

# Enter Departure Location

Detailed skill description...

## Variables

- **departure_city**: Name of the departure city
```

### actions.json Format

```json
[
  {
    "action_step": 5,
    "action": "click",
    "element_label": "Where from?",
    "args": ["e149"]
  },
  {
    "action_step": 9,
    "action": "type",
    "element_label": "Where else?",
    "args": ["e552", "Edinburgh"]
  },
  {
    "action_step": 11,
    "action": "enter",
    "args": []
  }
]
```

---

## Execution Log Format: action_timeline.json

Each task execution generates an `action_timeline.json` that records the complete execution trajectory. This file is the data source for skill extraction.

### File Location

```
session_logs/
└── session_YYYYMMDD_HHMMSS/
    └── action_timeline.json
```

### Two Action Types

Each entry in the timeline has an `action_type` field that distinguishes two execution methods:

#### 1. `subtask_replay` - Skill Replay

Indicates operations executed through existing Skills:

```json
{
  "action_step": 8,
  "timestamp": "2025-12-28T19:43:17.146966",
  "action_type": "subtask_replay",
  "subtask_id": "02_enter_departure_location",
  "subtask_name": "Enter Departure Location",
  "element_label": "Where from?",
  "variables_used": {
    "departure_city": "Chicago"
  }
}
```

#### 2. `individual_action` - Agent Autonomous Execution

Indicates atomic operations autonomously decided and executed by the Agent:

```json
{
  "action_step": 22,
  "timestamp": "2025-12-28T19:43:28.269268",
  "action_type": "individual_action",
  "action": "click",
  "element_label": "Change ticket type. Round trip",
  "args": ["e998"]
}
```

### Key Rule for Skill Extraction

**Only consecutive `individual_action` entries are analyzed as potential new skills.**

Reasons:
- `subtask_replay` is reuse of existing skills, no need to re-extract
- Consecutive `individual_action` entries indicate scenarios not covered by the skill library
- These new interaction patterns are exactly what needs to be learned and encapsulated

### Example: Mixed Execution Timeline

```json
{
  "task_description": "Search for one-way flights from Beijing to Shanghai",
  "timeline": [
    // Using existing skill: Open search page
    {"action_type": "subtask_replay", "subtask_name": "Open Google Flights", ...},

    // Using existing skill: Enter departure
    {"action_type": "subtask_replay", "subtask_name": "Enter Departure", ...},

    // Agent autonomous operation: Set one-way (not covered by skill library)
    {"action_type": "individual_action", "action": "click", ...},
    {"action_type": "individual_action", "action": "click", ...},

    // Using existing skill: Submit search
    {"action_type": "subtask_replay", "subtask_name": "Submit Search", ...}
  ]
}
```

In this example, the two consecutive `individual_action` entries in the middle will be analyzed by the Task Agent to determine if they can be extracted as a new "Set One-Way Ticket" skill.

---

## Complete Workflow

### Phase 1: Task Execution and Log Recording

```
┌─────────────────────────────────────────────────────────────┐
│  User Task: "Search for one-way flights from Beijing to     │
│  Shanghai on January 20"                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Main Agent executes task                                   │
│  - Check if available Skills exist                          │
│  - Compose Skills or execute atomic operations              │
│  - Record complete execution log to session_logs/           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Generate action_timeline.json                              │
│  - Contains all atomic operations                           │
│  - Contains skill invocation records                        │
│  - Contains page snapshots                                  │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Subtask Analysis and Skill Extraction

```
┌─────────────────────────────────────────────────────────────┐
│  Prerequisite: Task completed successfully                  │
│  (Only successful tasks can be used for reliable skill      │
│  extraction)                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Task Agent analyzes execution log                          │
│  - Identify consecutive atomic operation groups             │
│  - Segment subtasks based on semantic boundaries            │
│  - Identify parameterizable variables                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  skill_store.py saves Skills folders                        │
│  - Assign unique IDs                                        │
│  - Write */SKILL.md + actions.json                          │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3: Skill Reuse

```
┌─────────────────────────────────────────────────────────────┐
│  New Task: "Search for one-way flights from Guangzhou to    │
│  Shenzhen on February 15"                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Main Agent plans execution                                 │
│  1. Invoke skill_8: Initialize search page                  │
│  2. Invoke skill_9: Enter departure (departure_city=        │
│     "Guangzhou")                                            │
│  3. Invoke skill_18: Enter destination (destination_city=   │
│     "Shenzhen")                                             │
│  4. Invoke skill_13: Set one-way ticket                     │
│  5. Invoke skill_19: Set date (departure_date="Feb 15")     │
│  6. Invoke skill_15: Submit search                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ActionReplayer replays each Skill                          │
│  - Locate elements based on aria-label                      │
│  - Replace variable values                                  │
│  - Execute action sequence                                  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│  Element located         │     │  Element location failed    │
│  successfully            │     │  → Invoke Recovery Agent    │
│  → Execute operation     │     │  → Attempt to find          │
│  → Continue to next step │     │    alternative element      │
└─────────────────────────┘     └─────────────────────────────┘
```

---

## Execution Constraints: URL Preconditions

### Why Execution Constraints?

Each skill's execution has preconditions:
- **Dependencies exist between skills**: e.g., "Enter destination" must come after "Enter departure"
- **Starting point must be correct**: Skill B's starting point may be Skill A's ending point

### Constraint Implementation

We use **URL** as a simplified execution constraint:

```yaml
# Constraint definition in SKILL.md
url_start: "https://www.google.com/travel/flights"
url_end: "https://www.google.com/travel/flights?..."
```

- `url_start`: Page URL before skill execution
- `url_end`: Page URL after skill execution

### Constraint Check Flow

```python
# Pseudocode
def can_execute_skill(skill, current_url):
    if skill.url_start and current_url != skill.url_start:
        return False, "URL precondition not met"
    return True, None
```

---

## Element Locating Mechanism

### Semantic Attribute-Based Locating

We use two stable attributes for element identification:

1. **aria-label**: Element's accessibility label
2. **element role**: Element's role type

```python
# Element matching logic
def find_element_by_label(snapshot, target_label, target_role=None):
    for element in snapshot.elements:
        if element.aria_label == target_label:
            if target_role is None or element.role == target_role:
                return element.ref
    return None
```

### Potential Instability

**Warning**: aria-label based locating may be unstable due to:

1. **Dynamic content**: Page content changes causing label changes
2. **Internationalization**: Different language versions have different labels
3. **A/B testing**: Websites may dynamically adjust UI text
4. **DOM structure changes**: Website updates may change element structure

### Failure Recovery Mechanism

When element locating fails, the Recovery Agent will:
1. Analyze current page snapshot
2. Infer correct element based on context and task objective
3. Return alternative element or skip the step

---

## Usage

### 0. Prerequisites: Start Chrome with CDP

Before running, start Chrome with Chrome DevTools Protocol (CDP) enabled:

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223

# Linux
google-chrome --remote-debugging-port=9223

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9223
```

### 1. Install Dependencies

Same with CAMEL framework.

### 2. Run Task (Using Existing Skills)

```python
from core.skill_agent import SkillsAgent
import asyncio


async def main():
    # Create agent with skills directory
    agent = SkillsAgent(
        skills_dir="./skills_store",  # Skills root (auto-scoped by website)
        website="Google Flights",
    )

    # Initialize agent (connects to browser via CDP)
    success = await agent.initialize()
    if not success:
        print("Failed to initialize. Make sure Chrome is running with CDP enabled.")
        return

    # Run the task
    result = await agent.run(
        "Search for one-way flights from Tokyo to Osaka on Feb 20"
    )
    print(result)

    # Print statistics and save logs
    agent.print_statistics()
    agent.save_communication_log()


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Analyze New Tasks and Extract Subtasks

```bash
# 1. First ensure task executes successfully and generates logs
# 2. Run extraction script (pass session folder path as argument)
python -m examples.toolkits.browser.browser_skills_example.cli.subtask_extractor ./session_logs/session_xxx

# Optional: specify custom subtask_configs directory
python -m examples.toolkits.browser.browser_skills_example.cli.subtask_extractor ./session_logs/session_xxx ./subtask_configs
```

### 4. Verify Skill Loading

```bash
python skill_loader.py
```

---

## Key Design Principles

### 1. Only Extract Skills from Successful Tasks

**Important**: Only successfully completed tasks can be used for skill extraction.

Reasons:
- Failed executions may contain incorrect interaction patterns
- Cannot distinguish which operations are effective vs. invalid attempts
- Incorrect skills will cause more failures in subsequent tasks

### 2. Semantic Completeness of Subtasks

Each subtask should:
- Complete an **independent semantic goal** (e.g., "Enter departure location")
- Have clear **start and end points**
- Be **parameterizable** to adapt to different scenarios

### 3. Progressive Skill Accumulation

The system design supports continuous learning:
- Early tasks: More atomic operations
- Later tasks: More skill reuse
- New scenarios: Automatically learn new skills

---

## Extended Issues and Challenges

### Challenge 1: Skill Validation and Credit Assignment Problem

**Problem Description**:

The current implementation assumes: if a complete task succeeds, all subtasks along the trajectory are correct. However, in complex environments, agents may attempt multiple failed approaches before ultimately succeeding. We cannot assume every subtask along the successful trajectory is valid or generalizable—some may be exploratory detours or corrective actions.

**Theoretical Perspective**:

This is fundamentally an instance of the **Credit Assignment Problem** in reinforcement learning: when reward (task completion) occurs with temporal delay, which prior operations should receive credit?

**Possible Solutions**:

- **State reversion detection**: Identify mutually canceling operation pairs (e.g., opening then immediately closing a popup)
- **Counterfactual analysis**: Simulate whether the task still succeeds after removing an operation

### Challenge 2: Generalization Boundaries and Symbol Grounding Problem

**Problem Description**:

Skills accept parameters (such as input text, element labels), but the valid range of parameters may not be obvious. More importantly, incorrect inputs may not trigger explicit errors—procedural encapsulation of operations reduces the agent's ability to detect internal failures.

For example: In Google Flights, overly specific airport information silently returns no results, making it difficult for the agent to perceive that a problem occurred.

**Theoretical Perspective**:

This is an instance of the **Symbol Grounding Problem**: the agent operates on symbols (e.g., typing "SFO") without understanding the constraints those symbols must satisfy in the actual environment.

**Possible Solutions**:

Skill structures should include **Expectation Clauses**:

```
Action: Type("SFO")
Expectation: Input field retains "SFO" OR dropdown menu appears
```

If the expectation is not met, the skill throws an exception internally rather than silently continuing.

### Challenge 3: Skill Dependency Resolution and Context Modeling

**Problem Description**:

When decomposing task trajectories into subtasks, each skill may require a specific initial state. Invoking a skill from an incorrect starting state substantially increases failure probability. The current implementation uses a simplified URL heuristic, but this is insufficient for complex environments.

Web state depends on factors beyond URL: authentication status, form completion state, dynamically loaded content, etc.

**Possible Solutions**:

Restructure skill selection as a **Context-Aware Ranking Problem**:

- **User/Context** → Current Web state (not just URL, but also DOM embeddings, key text, previous action result)
- **Candidates** → All skills in the skill library
- **Click/Conversion** → Execution success rate / Task progress

This approach enables:
- Learning dependencies from historical execution data
- Constraining feasible skill sets after each skill invocation
- Continuous improvement as data accumulates

---

## Appendix: Configuration Parameters

### SkillsAgent Parameters (skill_agent.py)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skills_dir` | str | None | Skill directory (defaults to ./browser_skills) |
| `cdp_port` | int | 9223 | Chrome DevTools Protocol port |
| `use_agent_recovery` | bool | True | Whether to enable Recovery Agent |

### SKILL.md Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill name (lowercase + hyphens) |
| `id` | Yes | Unique numeric ID |
| `description` | Yes | Skill description |
| `start_index` | No | Start index in original log |
| `end_index` | No | End index in original log |
| `url_start` | No | URL precondition before execution |
| `url_end` | No | URL after execution |
| `variables` | No | Configurable parameters |
| `source` | No | Source information (log file, original task) |

---

## Summary

The Browser Skills framework implements progressive transformation from **Agent Loop (exploratory execution)** to **Workflow (deterministic execution)**:

1. **Exploration Phase**: Agent executes new tasks, recording complete interaction trajectories
2. **Extraction Phase**: Extract reusable atomic skills from successful tasks
3. **Execution Phase**: Subsequent tasks are completed through skill composition, greatly improving efficiency

Core Advantages:
- **High Reusability**: Skills can be shared across different tasks
- **Interpretability**: Each skill has clear semantics and boundaries
- **Continuous learning**: Skill library continuously enriches with use

Limitations:
- Element locating relies on aria-label, may be unstable
- URL constraints are a simplified approach, may be insufficient for complex scenarios
- Task must succeed to extract skills
