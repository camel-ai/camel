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
import re
import json
import shutil
from typing import Any, List, Literal, Optional, Union

from camel.agents.chat_agent import ChatAgent
from camel.memories import AgentMemory
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from jinja2 import Template
from camel.types import OpenAIBackendRole
from camel.logger import get_logger

try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent

logger = get_logger(__name__)

_PLANING_SYSTEM_PROMPT: str = """You are an expert researcher and strategic planner with a deep understanding of experimental design and reproducibility in scientific research. 
You will receive a research paper in {{paper_format}} format. 
Your task is to create a detailed and efficient plan to reproduce the experiments and methodologies described in the paper.
This plan should align precisely with the paper's methodology, experimental setup, and evaluation metrics. 

Instructions:

1. Align with the Paper: Your plan must strictly follow the methods, datasets, model configurations, hyperparameters, and experimental setups described in the paper.
2. Be Clear and Structured: Present the plan in a well-organized and easy-to-follow format, breaking it down into actionable steps.
3. Prioritize Efficiency: Optimize the plan for clarity and practical implementation while ensuring fidelity to the original experiments."""

_PLANING_USER_PROMPTS: List[str] = [
    """## Paper
{{ paper_content }}

## Task
1. We want to reproduce the method described in the attached paper. 
2. The authors did not release any official code, so we have to plan our own implementation.
3. Before writing any Python code, please outline a comprehensive plan that covers:
   - Key details from the paper's **Methodology**.
   - Important aspects of **Experiments**, including dataset requirements, experimental settings, hyperparameters, or evaluation metrics.
4. The plan should be as **detailed and informative** as possible to help us write the final code later.

## Requirements
- You don't need to provide the actual code yet; focus on a **thorough, clear strategy**.
- If something is unclear from the paper, mention it explicitly.

## Instruction
The response should give us a strong roadmap, making it easier to write the code later.

{{ input_message }}""",
    """Your goal is to create a concise, usable, and complete software system design for reproducing the paper's method. Use appropriate open-source libraries and keep the overall architecture simple.
             
Based on the plan for reproducing the paper’s main method, please design a concise, usable, and complete software system. 
Keep the architecture simple and make effective use of open-source libraries.

-----

## Format Example
[CONTENT]
{
    "Implementation approach": "We will ... ,
    "File list": [
        "main.py",  
        "dataset_loader.py", 
        "model.py",  
        "trainer.py",
        "evaluation.py" 
    ],
    "Data structures and interfaces": "\nclassDiagram\n    class Main {\n        +__init__()\n        +run_experiment()\n    }\n    class DatasetLoader {\n        +__init__(config: dict)\n        +load_data() -> Any\n    }\n    class Model {\n        +__init__(params: dict)\n        +forward(x: Tensor) -> Tensor\n    }\n    class Trainer {\n        +__init__(model: Model, data: Any)\n        +train() -> None\n    }\n    class Evaluation {\n        +__init__(model: Model, data: Any)\n        +evaluate() -> dict\n    }\n    Main --> DatasetLoader\n    Main --> Trainer\n    Main --> Evaluation\n    Trainer --> Model\n",
    "Program call flow": "\nsequenceDiagram\n    participant M as Main\n    participant DL as DatasetLoader\n    participant MD as Model\n    participant TR as Trainer\n    participant EV as Evaluation\n    M->>DL: load_data()\n    DL-->>M: return dataset\n    M->>MD: initialize model()\n    M->>TR: train(model, dataset)\n    TR->>MD: forward(x)\n    MD-->>TR: predictions\n    TR-->>M: training complete\n    M->>EV: evaluate(model, dataset)\n    EV->>MD: forward(x)\n    MD-->>EV: predictions\n    EV-->>M: metrics\n",
    "Anything UNCLEAR": "Need clarification on the exact dataset format and any specialized hyperparameters."
}
[/CONTENT]

## Nodes: "<node>: <type>  # <instruction>"
- Implementation approach: <class 'str'>  # Summarize the chosen solution strategy.
- File list: typing.List[str]  # Only need relative paths. ALWAYS write a main.py or app.py here.
- Data structures and interfaces: typing.Optional[str]  # Use mermaid classDiagram code syntax, including classes, method(__init__ etc.) and functions with type annotations, CLEARLY MARK the RELATIONSHIPS between classes, and comply with PEP8 standards. The data structures SHOULD BE VERY DETAILED and the API should be comprehensive with a complete design.
- Program call flow: typing.Optional[str] # Use sequenceDiagram code syntax, COMPLETE and VERY DETAILED, using CLASSES AND API DEFINED ABOVE accurately, covering the CRUD AND INIT of each object, SYNTAX MUST BE CORRECT.
- Anything UNCLEAR: <class 'str'>  # Mention ambiguities and ask for clarifications.

## Constraint
Format: output wrapped inside [CONTENT][/CONTENT] like the format example, nothing else.

## Action
Follow the instructions for the nodes, generate the output, and ensure it follows the format example.""",
    """Your goal is break down tasks according to PRD/technical design, generate a task list, and analyze task dependencies. 
You will break down tasks, analyze dependencies.
             
You outline a clear PRD/technical design for reproducing the paper’s method and experiments. 

Now, let's break down tasks according to PRD/technical design, generate a task list, and analyze task dependencies.
The Logic Analysis should not only consider the dependencies between files but also provide detailed descriptions to assist in writing the code needed to reproduce the paper.

-----

## Format Example
[CONTENT]
{
    "Required packages": [
        "numpy==1.21.0",
        "torch==1.9.0"  
    ],
    "Required Other language third-party packages": [
        "No third-party dependencies required"
    ],
    "Logic Analysis": [
        [
            "data_preprocessing.py",
            "DataPreprocessing class ........"
        ],
        [
            "trainer.py",
            "Trainer ....... "
        ],
        [
            "dataset_loader.py",
            "Handles loading and ........"
        ],
        [
            "model.py",
            "Defines the model ......."
        ],
        [
            "evaluation.py",
            "Evaluation class ........ "
        ],
        [
            "main.py",
            "Entry point  ......."
        ]
    ],
    "Task list": [
        "dataset_loader.py", 
        "model.py",  
        "trainer.py", 
        "evaluation.py",
        "main.py"  
    ],
    "Full API spec": "openapi: 3.0.0 ...",
    "Shared Knowledge": "Both data_preprocessing.py and trainer.py share ........",
    "Anything UNCLEAR": "Clarification needed on recommended hardware configuration for large-scale experiments."
}

[/CONTENT]

## Nodes: "<node>: <type>  # <instruction>"
- Required packages: typing.Optional[typing.List[str]]  # Provide required third-party packages in requirements.txt format.(e.g., 'numpy==1.21.0').
- Required Other language third-party packages: typing.List[str]  # List down packages required for non-Python languages. If none, specify "No third-party dependencies required".
- Logic Analysis: typing.List[typing.List[str]]  # Provide a list of files with the classes/methods/functions to be implemented, including dependency analysis and imports. Include as much detailed description as possible.
- Task list: typing.List[str]  # Break down the tasks into a list of filenames, prioritized based on dependency order. The task list must include the previously generated file list.
- Full API spec: <class 'str'>  # Describe all APIs using OpenAPI 3.0 spec that may be used by both frontend and backend. If front-end and back-end communication is not required, leave it blank.
- Shared Knowledge: <class 'str'>  # Detail any shared knowledge, like common utility functions or configuration variables.
- Anything UNCLEAR: <class 'str'>  # Mention any unresolved questions or clarifications needed from the paper or project scope.

## Constraint
Format: output wrapped inside [CONTENT][/CONTENT] like the format example, nothing else.

## Action
Follow the node instructions above, generate your output accordingly, and ensure it follows the given format example.""",
    """You write elegant, modular, and maintainable code. Adhere to Google-style guidelines.

Based on the paper, plan, design specified previously, follow the "Format Example" and generate the code. 
Extract the training details from the above paper (e.g., learning rate, batch size, epochs, etc.), follow the "Format example" and generate the code. 
DO NOT FABRICATE DETAILS — only use what the paper provides.

You must write `config.yaml`.

ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. Your output format must follow the example below exactly.

-----

# Format Example
## Code: config.yaml
```yaml
## config.yaml
training:
  learning_rate: ...
  batch_size: ...
  epochs: ...
...
```

-----

## Code: config.yaml
"""
]

_ANALYSIS_SYSTEM_PROMPT = """You are an expert researcher, strategic analyzer and software engineer with a deep understanding of experimental design and reproducibility in scientific research.
You will receive a research paper in {{paper_format}} format, an overview of the plan, a design in JSON format consisting of "Implementation approach", "File list", "Data structures and interfaces", and "Program call flow", followed by a task in JSON format that includes "Required packages", "Required other language third-party packages", "Logic Analysis", and "Task list", along with a configuration file named "config.yaml". 

Your task is to conduct a comprehensive logic analysis to accurately reproduce the experiments and methodologies described in the research paper. 
This analysis must align precisely with the paper’s methodology, experimental setup, and evaluation criteria.

1. Align with the Paper: Your analysis must strictly follow the methods, datasets, model configurations, hyperparameters, and experimental setups described in the paper.
2. Be Clear and Structured: Present your analysis in a logical, well-organized, and actionable format that is easy to follow and implement.
3. Prioritize Efficiency: Optimize the analysis for clarity and practical implementation while ensuring fidelity to the original experiments.
4. Follow design: YOU MUST FOLLOW "Data structures and interfaces". DONT CHANGE ANY DESIGN. Do not use public member functions that do not exist in your design.
5. REFER TO CONFIGURATION: Always reference settings from the config.yaml file. Do not invent or assume any values—only use configurations explicitly provided.
     
"""

_ANALYSIS_USER_PROMPT = """## Paper
        {{paper_content}}

        -----

        ## Overview of the plan
        {{context_lst0}}

        -----

        ## Design
        {{context_lst1}}

        -----

        ## Task
        {{context_lst2}}

        -----

        ## Configuration file
        ```yaml
        {{config_yaml}}
        ```
        -----

        ## Instruction
        Conduct a Logic Analysis to assist in writing the code, based on the paper, the plan, the design, the task and the previously specified configuration file (config.yaml). 
        You DON'T need to provide the actual code yet; focus on a thorough, clear analysis.

        {{draft_desc}}

        -----
        ## Logic Analysis: {{todo_file_name}}"""

_CODE_SYSTEM_PROMPT = """You are an expert researcher and software engineer with a deep understanding of experimental design and reproducibility in scientific research.
    You will receive a research paper in {{paper_format}} format, an overview of the plan, a Design in JSON format consisting of "Implementation approach", "File list", "Data structures and interfaces", and "Program call flow", followed by a Task in JSON format that includes "Required packages", "Required other language third-party packages", "Logic Analysis", and "Task list", along with a configuration file named "config.yaml". 
    Your task is to write code to reproduce the experiments and methodologies described in the paper. 

    The code you write must be elegant, modular, and maintainable, adhering to Google-style guidelines. 
    The code must strictly align with the paper's methodology, experimental setup, and evaluation metrics. 
    Write code with triple quoto."""

_CODE_USER_PROMPT = """# Context
## Paper
{{paper_content}}

-----

## Overview of the plan
{{context_lst0}}

-----

## Design
{{context_lst1}}

-----

## Task
{{context_lst2}}

-----

## Configuration file
```yaml
{{config_yaml}}
```
-----

## Code Files
{{code_files}}

-----

# Format example
## Code: {{todo_file_name}}
```python
## {{todo_file_name}}
...
```

-----

# Instruction
Based on the paper, plan, design, task and configuration file(config.yaml) specified previously, follow "Format example", write the code. 

We have {{done_file_lst}}.
Next, you must write only the "{{todo_file_name}}".
1. Only One file: do your best to implement THIS ONLY ONE FILE.
2. COMPLETE CODE: Your code will be part of the entire project, so please implement complete, reliable, reusable code snippets.
3. Set default value: If there is any setting, ALWAYS SET A DEFAULT VALUE, ALWAYS USE STRONG TYPE AND EXPLICIT VARIABLE. AVOID circular import.
4. Follow design: YOU MUST FOLLOW "Data structures and interfaces". DONT CHANGE ANY DESIGN. Do not use public member functions that do not exist in your design.
5. CAREFULLY CHECK THAT YOU DONT MISS ANY NECESSARY CLASS/FUNCTION IN THIS FILE.
6. Before using a external variable/module, make sure you import it first.
7. Write out EVERY CODE DETAIL, DON'T LEAVE TODO.
8. REFER TO CONFIGURATION: you must use configuration from "config.yaml". DO NOT FABRICATE any configuration values.

{{detailed_logic_analysis}}

## Code: {{todo_file_name}}"""


@track_agent(name="PaperToCodeAgent")
class PaperToCodeAgent(ChatAgent):
    r"""An agent that converts research papers into executable code.

    This agent processes academic research papers and generates code to reproduce
    the methods, experiments, and results described in the paper. It follows a
    structured workflow including planning, analysis, and code generation phases.

    Args:
        file_path (str): Path to the input paper file.
        paper_name (str): Name of the paper for output organization.
        paper_format (Literal['JSON', 'LaTex']): Format of the input paper.
        model (Optional[BaseModelBackend]): The model backend to use for
            generating responses. If None, a default model will be used.
        memory (Optional[AgentMemory]): Memory system for the agent. If None,
            a default memory will be used.
        message_window_size (int): The maximum number of previous messages to
            include in the context window. (default: 20)
    """

    def __init__(
        self,
        file_path: str,
        paper_name: str,
        paper_format: Literal['JSON', 'LaTex'],
        model: Optional[BaseModelBackend] = None,
        memory: Optional[AgentMemory] = None,
        message_window_size: int = 20,
    ) -> None:
        self.paper_format: str = paper_format

        template: Template = Template(_PLANING_SYSTEM_PROMPT)
        formatted_content = template.render(paper_format=self.paper_format)
        planning_system_message = BaseMessage.make_assistant_message(
            role_name="Assistant", content=formatted_content)
        self.planning_system_message = planning_system_message

        super().__init__(
            planning_system_message,
            model=model,
            memory=memory,
            message_window_size=message_window_size,
        )

        anaylyzing_template = Template(_ANALYSIS_SYSTEM_PROMPT)
        anaylyzing_formatted_content = anaylyzing_template.render(
            paper_format=self.paper_format)
        self.analyzing_system_message: BaseMessage = BaseMessage.make_assistant_message(
            role_name="Assistant", content=anaylyzing_formatted_content)

        coding_template = Template(_ANALYSIS_SYSTEM_PROMPT)
        coding_formatted_content = coding_template.render(
            paper_format=self.paper_format)
        self.coding_system_message: BaseMessage = BaseMessage.make_assistant_message(
            role_name="Assistant", content=coding_formatted_content)

        self.file_path: str = file_path
        self.paper_name: str = paper_name
        self.output_path: str = f'{self.paper_name}/output/'
        self.output_repo_path: str = f'{self.paper_name}/repo/'

    def step(
        self,
        input_message: Union[BaseMessage, str],
    ) -> None:
        r"""Process the input message and run the full paper-to-code pipeline.
        
        This method coordinates the entire workflow: paper processing, planning,
        architecture design, code structure design, and code generation.
        
        Args:
            input_message (Union[BaseMessage, str]): The input message from the user,
                can be incorporated into prompts as additional guidance.
        """
        if self.paper_format == "JSON":
            self._process()
        self.planning(input_message.content if isinstance(
            input_message, BaseMessage) else input_message)
        self._extract_config()
        self.analyzing()
        self.coding()

    def remove_spans(self, data: Any):
        r"""Remove unnecessary spans from the paper JSON data.
        
        Cleans the JSON data structure by removing fields that are not needed for
        code generation, such as citations, references, and metadata fields.
        
        Args:
            data (Any): The data structure to clean, typically a dictionary or list.
            
        Returns:
            Any: The cleaned data structure with unnecessary fields removed.
        """
        if isinstance(data, dict):
            for key in ["cite_spans", "ref_spans", "eq_spans", "authors", "bib_entries", \
                        "year", "venue", "identifiers", "_pdf_hash", "header"]:
                data.pop(key, None)
            for key, value in data.items():
                data[key] = self.remove_spans(value)
        elif isinstance(data, list):
            return [self.remove_spans(item) for item in data]
        return data

    def _process(self):
        r"""Process the paper file by cleaning up its JSON structure.
        
        Reads the paper file, removes unnecessary spans from the JSON data,
        and writes the cleaned data back to the file.
        """
        with open(f'{self.file_path}') as f:
            data = json.load(f)
        cleaned_data = self.remove_spans(data)
        with open(self.file_path, 'w') as f:
            json.dump(cleaned_data, f)

    def planning(self, input_message: str = ""):
        r"""Generate a plan for reproducing the paper's methodology and experiments.
        
        This phase creates a detailed roadmap for implementation by analyzing the
        paper content and outputting a structured plan, architecture design, and
        logic design.
        
        Args:
            input_message (str, optional): Additional input to incorporate into the planning
                prompts. (default: "")
        """
        with open(self.file_path) as f:
            paper_content: str = f.read()

        responses = []
        trajectories = []
        trajectories.append({
            'role': 'system',
            'content': self.planning_system_message.content
        })
        for user_message_template in _PLANING_USER_PROMPTS:
            context = {
                "paper_content": paper_content or "",
                "input_message": input_message or "",
            }
            template = Template(user_message_template)
            user_message = template.render(**context)
            trajectories.append({'role': 'user', 'content': user_message})

            completion = super().step(user_message)
            completion_json = json.loads(completion.model_dump_json())
            responses.append(completion_json)
            message = completion.msg
            trajectories.append({
                'role': 'assistant',
                'content': message.content
            })
            logger.info(f'planning response: {message}')

        os.makedirs(self.output_path, exist_ok=True)
        with open(f'{self.output_path}/planning_response.json', 'w') as f:
            json.dump(responses, f)
        with open(f'{self.output_path}/planning_trajectories.json', 'w') as f:
            json.dump(trajectories, f)

    def _extract_config(self) -> None:
        r"""Extract configuration information from the planning output.
        
        Processes the planning trajectories to extract YAML configuration,
        architecture design, and logic design, saving them as separate artifacts.
        """
        with open(f'{self.output_path}/planning_trajectories.json',
                  encoding='utf8') as f:
            traj = json.load(f)

        yaml_raw_content = ""
        for turn_idx, turn in enumerate(traj):
            if turn_idx == 8:
                yaml_raw_content = turn['content']

        if "</think>" in yaml_raw_content:
            yaml_raw_content = yaml_raw_content.split("</think>")[-1]

        match = re.search(r"```yaml\n(.*?)\n```", yaml_raw_content, re.DOTALL)
        if match:
            yaml_content = match.group(1)
            with open(f'{self.output_path}/planning_config.yaml', 'w',
                      encoding='utf8') as f:
                f.write(yaml_content)
        else:
            match = re.search(r"```yaml\\n(.*?)\\n```", yaml_raw_content,
                              re.DOTALL)
            if match:
                yaml_content = match.group(1)
                with open(f'{self.output_path}/planning_config.yaml', 'w',
                          encoding='utf8') as f:
                    f.write(yaml_content)
            else:
                logger.warning("No YAML content found.")

        artifact_output_dir = f"{self.output_path}/planning_artifacts"
        os.makedirs(artifact_output_dir, exist_ok=True)

        context_lst = self.extract_planning(
            f'{self.output_path}/planning_trajectories.json')

        arch_design = self._content_to_json(context_lst[1])
        logic_design = self._content_to_json(context_lst[2])

        def __format(data):
            formatted_text = ""
            for key, value in data.items():
                formatted_text += "-" * 40 + "\n"
                formatted_text += "[" + key + "]\n"
                if isinstance(value, list):
                    for item in value:
                        formatted_text += f"- {item}\n"
                else:
                    formatted_text += str(value) + "\n"
                formatted_text += "\n"
            return formatted_text

        formatted_arch_design = __format(arch_design)
        formatted_logic_design = __format(logic_design)

        with open(f"{artifact_output_dir}/1.1_overall_plan.txt", "w",
                  encoding="utf-8") as f:
            f.write(context_lst[0])

        with open(f"{artifact_output_dir}/1.2_arch_design.txt", "w",
                  encoding="utf-8") as f:
            f.write(formatted_arch_design)

        with open(f"{artifact_output_dir}/1.3_logic_design.txt", "w",
                  encoding="utf-8") as f:
            f.write(formatted_logic_design)

        shutil.copy(f"{self.output_path}/planning_config.yaml",
                    f"{artifact_output_dir}/1.4_config.yaml")

    def extract_planning(self, trajectories_json_file_path):
        r"""Extract planning content from the saved trajectories.
        
        Args:
            trajectories_json_file_path (str): Path to the JSON file containing
                the planning process trajectories.
                
        Returns:
            List[str]: A list of content extracted from assistant messages in the
                trajectories, typically containing plan, architecture, and task list.
        """
        with open(trajectories_json_file_path) as f:
            traj = json.load(f)

        context_lst = []
        for turn in traj:
            if turn['role'] == 'assistant':
                content = turn['content']
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                context_lst.append(content)

        context_lst = context_lst[:3]
        return context_lst

    def analyzing(self):
        r"""Analyze the planning output to create detailed implementation logic.
        
        For each file in the task list, generates detailed logic analysis that
        describes the implementation details, interfaces, and functionality.
        Updates the system prompt to focus on analysis and saves the results.
        """
        self.update_system_prompt(self.analyzing_system_message)

        with open(self.file_path) as f:
            paper_content: str = f.read()

        with open(f'{self.output_path}/planning_config.yaml') as f:
            config_yaml = f.read()

        context_lst = self.extract_planning(
            f'{self.output_path}/planning_trajectories.json')

        if os.path.exists(f'{self.output_path}/task_list.json'):
            with open(f'{self.output_path}/task_list.json') as f:
                task_list = json.load(f)
        else:
            task_list = self._content_to_json(context_lst[2])

        possible_keys = ['Task list', 'task_list', 'task list']
        todo_file_lst = []
        for key in possible_keys:
            if key in task_list:
                todo_file_lst = task_list[key]
                break
        if not todo_file_lst:
            logger.warning(
                f"No task list found in keys: {list(task_list.keys())}")

        done_file_lst = ['config.yaml']
        logic_analysis_dict = {}
        for desc in task_list['Logic Analysis']:
            logic_analysis_dict[desc[0]] = desc[1]

        artifact_output_dir = f'{self.output_path}/analyzing_artifacts'
        os.makedirs(artifact_output_dir, exist_ok=True)

        for todo_file_name in todo_file_lst:
            responses = []
            if todo_file_name == "config.yaml":
                continue

            if todo_file_name not in logic_analysis_dict:
                logic_analysis_dict[todo_file_name] = ""

            draft_desc = f"Write the logic analysis in '{todo_file_name}', which is intended for '{logic_analysis_dict[todo_file_name]}'."
            if len(logic_analysis_dict[todo_file_name].strip()) == 0:
                draft_desc = f"Write the logic analysis in '{todo_file_name}'."

            context = {
                "paper_content": paper_content or "",
                "context_lst0": context_lst[0] or "",
                "context_lst1": context_lst[1] or "",
                "context_lst2": context_lst[2] or "",
                "config_yaml": config_yaml or "",
                "draft_desc": draft_desc or "",
            }
            template = Template(_ANALYSIS_USER_PROMPT)
            instruction_msg = template.render(**context)
            completion = super().step(instruction_msg)

            completion_json = json.loads(completion.model_dump_json())
            responses.append(completion_json)

            with open(
                    f'{artifact_output_dir}/{todo_file_name}_simple_analysis.txt',
                    'w') as f:
                f.write(completion.msg.content)

            done_file_lst.append(todo_file_name)
            todo_file_name = todo_file_name.replace("/", "_")
            with open(
                    f'{self.output_path}/{todo_file_name}_simple_analysis_response.json',
                    'w') as f:
                json.dump(responses, f)

    def update_system_prompt(self, prompt: BaseMessage) -> None:
        r"""Update the agent's system prompt and clear the memory.
        
        Args:
            prompt (BaseMessage): The new system prompt to use for the agent.
        """
        self.memory.clear()
        self.update_memory(prompt, OpenAIBackendRole.SYSTEM)

    def coding(self):
        r"""Generate code based on the planning and analysis outputs.
        
        This phase uses the planning outputs, analysis, and configuration to
        generate actual code files for each task in the task list. The generated
        code is saved to the output repository directory.
        """
        self.update_system_prompt(self.coding_system_message)

        with open(self.file_path) as f:
            paper_content: str = f.read()

        with open(f'{self.output_path}/planning_config.yaml') as f:
            config_yaml = f.read()

        context_lst = self.extract_planning(
            f'{self.output_path}/planning_trajectories.json')
        task_list = self._content_to_json(context_lst[2])

        todo_file_lst = task_list['Task list']
        done_file_lst = ['config.yaml']
        done_file_dict = {}

        code_files = ""
        for done_file in done_file_lst:
            if done_file.endswith(".yaml"): continue
            code_files += f"""
        ```python
        {done_file_dict[done_file]}
        ```
        """

        detailed_logic_analysis_dict = {}
        for todo_file_name in todo_file_lst:
            save_todo_file_name = todo_file_name.replace("/", "_")

            if todo_file_name == "config.yaml":
                continue

            with open(
                    f"{self.output_path}/{save_todo_file_name}_simple_analysis_response.json"
            ) as f:
                detailed_logic_analysis_response = json.load(f)

            detailed_logic_analysis_dict[
                todo_file_name] = detailed_logic_analysis_response[0]['msgs'][
                    0]['content']

        artifact_output_dir = f'{self.output_path}/coding_artifacts'
        os.makedirs(artifact_output_dir, exist_ok=True)

        for todo_file_name in todo_file_lst:
            responses = []
            if todo_file_name == "config.yaml":
                continue

            context = {
                "paper_content": paper_content or "",
                "context_lst0": context_lst[0] or "",
                "context_lst1": context_lst[1] or "",
                "context_lst2": context_lst[2] or "",
                "config_yaml": config_yaml or "",
                "code_files": code_files or "",
                "todo_file_name": todo_file_name or "",
                "done_file_lst": done_file_lst or []
            }
            template = Template(_CODE_USER_PROMPT)
            instruction_msg = template.render(**context)

            completion = super().step(instruction_msg)
            completion_json = json.loads(completion.model_dump_json())
            responses.append(completion_json)

            message = completion.msg.content
            done_file_lst.append(todo_file_name)

            os.makedirs(f'{self.output_repo_path}', exist_ok=True)
            save_todo_file_name = todo_file_name.replace("/", "_")

            with open(
                    f'{artifact_output_dir}/{save_todo_file_name}_coding.txt',
                    'w') as f:
                f.write(message)

            code = self._extract_code_from_content(message)
            if len(code) == 0:
                code = message

            done_file_dict[todo_file_name] = code
            if save_todo_file_name != todo_file_name:
                todo_file_dir = '/'.join(todo_file_name.split("/")[:-1])
                os.makedirs(f"{self.output_repo_path}/{todo_file_dir}",
                            exist_ok=True)

            with open(f"{self.output_repo_path}/{todo_file_name}", 'w') as f:
                f.write(code)

    def _extract_code_from_content(self, content):
        r"""Extract code blocks from content text.
        
        Args:
            content (str): The content text that may contain code blocks
                enclosed in Markdown-style code fence (```).
                
        Returns:
            str: The extracted code without the code fence markers, or an empty
                string if no code block is found.
        """
        pattern = r'^```(?:\w+)?\s*\n(.*?)(?=^```)```'
        code = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        return code[0] if len(code) > 0 else ""

    def _content_to_json(self, data):
        r"""Convert string content to JSON with robust error handling.
        
        Attempts multiple approaches to parse potentially malformed JSON content,
        applying various cleaning operations to increase the chances of successful parsing.
        
        Args:
            data (str): The string content to convert to JSON.
            
        Returns:
            dict: The parsed JSON data as a dictionary, or an empty dictionary if
                parsing fails after all attempts.
        """
        if not data or not isinstance(data, str):
            return {}

        cleaned = re.sub(r'\[CONTENT\]|\[/CONTENT\]', '', data).strip()
        try:
            clean_data = cleaned
            clean_data = re.sub(r'(".*?"),\s*#.*', r'\1,', clean_data)
            clean_data = re.sub(r',\s*\]', ']', clean_data)
            clean_data = re.sub(r'\n\s*', '', clean_data)

            return json.loads(clean_data)
        except json.JSONDecodeError:
            pass

        try:
            clean_data = cleaned
            clean_data = re.sub(r'(".*?"),\s*#.*', r'\1,', clean_data)
            clean_data = re.sub(r'(".*?")\s*#.*', r'\1', clean_data)
            clean_data = re.sub(r',\s*\]', ']', clean_data)
            clean_data = re.sub(r'\n\s*', '', clean_data)

            return json.loads(clean_data)
        except json.JSONDecodeError:
            pass

        try:
            clean_data = cleaned
            clean_data = re.sub(r'(".*?"),\s*#.*', r'\1,', clean_data)
            clean_data = re.sub(r'(".*?")\s*#.*', r'\1', clean_data)
            clean_data = re.sub(r',\s*\]', ']', clean_data)
            clean_data = re.sub(r'\n\s*', '', clean_data)
            clean_data = re.sub(r'"""', '"', clean_data)
            clean_data = re.sub(r"'''", "'", clean_data)
            clean_data = re.sub(r"\\", "'", clean_data)

            return json.loads(f"""{clean_data}""")
        except json.JSONDecodeError:
            pass

        pattern = r'"Logic Analysis":\s*(\[\s\S]*?\])\s*,\s*"Task list":\s*(\[\s\S]*?\])'
        match = re.search(pattern, data)

        if match:
            try:
                logic_analysis = json.loads(match.group(1))
                task_list = json.loads(match.group(2))
                return {
                    "Logic Analysis": logic_analysis,
                    "Task list": task_list
                }
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse JSON with all approaches")
        return {}
