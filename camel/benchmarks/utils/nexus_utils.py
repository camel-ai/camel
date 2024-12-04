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

import ast
import textwrap
from dataclasses import dataclass
from datasets import load_dataset

TOOL_CALLING_PROMPT = """
You are given multiple functions and a user query.

Please proceed with generating a function call for the function with the proper arguments that best answers the given prompt.

Respond with nothing but the function call ONLY, such that I can directly execute your function call without any post processing necessary from my end. Do not use variables. 
If there are more than two function calls, separate them with a semicolon (;).

{tools}

Question: {input}
"""

# Define the data class
@dataclass
class NexusTool:
    function_calls: str
    descriptions: str

def construct_tool_descriptions(dataset_name) -> str:
    if dataset_name == "NVDLibrary":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="CVECPE")["train"]
    elif dataset_name == "VirusTotal":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="VirusTotal")["train"]
    elif dataset_name == "PlacesAPI":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="Places")["train"]
    elif dataset_name == "ClimateAPI":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="Climate")["train"]
    elif dataset_name == "OTX":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="OTX")["train"]
    elif dataset_name == "VirusTotal-NestedCalls":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="VT_Multi (Nested)")["train"]
    elif dataset_name == "VirusTotal-ParallelCalls":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="VT_Multi (Parallel)")["train"]
    elif dataset_name == "NVDLibrary-NestedCalls":
        dataset = load_dataset("Nexusflow/Function_Call_Definitions", name="CVECPE_Multi (Nested)")["train"]

    tools = [NexusTool(tool["function_calls"], tool["descriptions"]) for tool in dataset]
    
    tool_prompt = ""
    for tool in tools:
        tool_prompt += f"Function:\ndef {tool.function_calls}:\n" + "\"\"\"\n" + f"{tool.descriptions}" + "\n\"\"\"\n"
        
    return tool_prompt

def construct_prompt(input, tools) -> str:
    return TOOL_CALLING_PROMPT.format(tools=tools, input=input)

def parse_function_call(call) -> tuple:
    """
    Parse a function call string and handle nested function calls in both positional and keyword arguments.
    Example input: "func1(arg1=func2(3, 4), arg2=func3(key=func4(5)))"
    Returns a tuple: (function_name, positional_arguments, keyword_arguments).
    """
    def preprocess_input(call: str) -> str:
        """Remove formatting like code blocks and whitespace."""
        if call.strip().startswith("```python"):
            call = call.strip().removeprefix("```python").removesuffix("```")
        return textwrap.dedent(call).strip()

    def evaluate_arg(arg):
        r"""Recursively evaluate arguments, including nested calls."""
        if isinstance(arg, ast.Call):
            # Recursively parse nested calls
            func_name, args, kwargs = parse_function_call(ast.unparse(arg))
            return func_name, args, kwargs
        elif isinstance(arg, ast.Constant):  # Handle literals like numbers, strings, etc.
            return arg.value
        elif isinstance(arg, ast.List):  # Handle list literals
            return [evaluate_arg(el) for el in arg.elts]
        elif isinstance(arg, ast.Dict):  # Handle dictionary literals
            return {evaluate_arg(k): evaluate_arg(v) for k, v in zip(arg.keys, arg.values)}
        elif isinstance(arg, ast.Tuple):  # Handle tuple literals
            return tuple(evaluate_arg(el) for el in arg.elts)
        else:
            return ast.literal_eval(arg)  # Safely evaluate other types

    call = preprocess_input(call)
    parsed_calls = []

    try:
        # Parse the string into an AST
        parsed_calls = call.split(";")
        for single_call in parsed_calls:
            tree = ast.parse(single_call, mode='eval')
            
            # Ensure it's a function call
            if isinstance(tree.body, ast.Call):
                # Extract function name
                if isinstance(tree.body.func, ast.Name):  # Simple function call
                    func_name = tree.body.func.id
                elif isinstance(tree.body.func, ast.Attribute):  # Attribute function call
                    func_name = f"{tree.body.func.value.id}.{tree.body.func.attr}"
                else:
                    raise ValueError(f"Unsupported function call: {call}")
                
                # Extract positional arguments
                args = [evaluate_arg(arg) for arg in tree.body.args]
                
                # Extract keyword arguments
                kwargs = {kw.arg: evaluate_arg(kw.value) for kw in tree.body.keywords}
                print("Valid call.")
                return func_name, args, kwargs
        else:
            raise ValueError(f"Not a valid function call: {call}")
    except Exception as e:
        print(f"Error parsing call: {call}, {e}")
        return None, None, None

def compare_function_calls(agent_call, ground_truth_call) -> bool:
    r"""
    Compare the function name and arguments of agent_call and ground_truth_call.
    Returns:
        - True if the function names and arguments match.
        - False otherwise.
    """
    # Parse both calls
    agent_parsed = parse_function_call(agent_call)
    gt_parsed = parse_function_call(ground_truth_call)

    if agent_parsed and gt_parsed:
        return agent_parsed == gt_parsed
    else:
        return False
    
      