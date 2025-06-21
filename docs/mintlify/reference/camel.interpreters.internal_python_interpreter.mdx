<a id="camel.interpreters.internal_python_interpreter"></a>

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter"></a>

## InternalPythonInterpreter

```python
class InternalPythonInterpreter(BaseInterpreter):
```

A customized python interpreter to control the execution of
LLM-generated codes. The interpreter makes sure the code can only execute
functions given in action space and import white list. It also supports
fuzzy variable matching to retrieve uncertain input variable name.

.. highlight:: none

This class is adapted from the hugging face implementation
[python_interpreter.py](https://github.com/huggingface/transformers/blob/8f
093fb799246f7dd9104ff44728da0c53a9f67a/src/transformers/tools/python_interp
reter.py). The original license applies::

Copyright 2023 The HuggingFace Inc. team. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License.

We have modified the original code to suit our requirements. We have
encapsulated the original functions within a class and saved the
interpreter state after execution. We have added support for "import"
statements, "for" statements, and several binary and unary operators. We
have added import white list to keep `import` statement safe. Additionally,
we have modified the variable matching logic and introduced the
:obj:`fuzz_state` for fuzzy matching.

Modifications copyright (C) 2023 CAMEL-AI.org

**Parameters:**

- **action_space** (Dict[str, Any], optional): A dictionary that maps action names to their corresponding functions or objects. The interpreter can only execute functions that are either directly listed in this dictionary or are member functions of objects listed in this dictionary. The concept of :obj:`action_space` is derived from EmbodiedAgent, representing the actions that an agent is capable of performing. If `None`, set to empty dict. (default: :obj:`None`)
- **import_white_list** (List[str], optional): A list that stores the Python modules or functions that can be imported in the code. All submodules and functions of the modules listed in this list are importable. Any other import statements will be rejected. The module and its submodule or function name are separated by a period (:obj:`.`). (default: :obj:`None`)
- **unsafe_mode** (bool, optional): If `True`, the interpreter runs the code by `eval()` or `exec()` without any security check. (default: :obj:`False`)
- **raise_error** (bool, optional): Raise error if the interpreter fails. (default: :obj:`False`)
- **allow_builtins** (bool, optional): If `True`, safe built-in functions like print, len, str, etc. are added to the action space. (default: :obj:`True`)

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.__init__"></a>

### __init__

```python
def __init__(
    self,
    action_space: Optional[Dict[str, Any]] = None,
    import_white_list: Optional[List[str]] = None,
    unsafe_mode: bool = False,
    raise_error: bool = False,
    allow_builtins: bool = True
):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._add_safe_builtins"></a>

### _add_safe_builtins

```python
def _add_safe_builtins(self):
```

Add safe built-in functions to the action space.

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.run"></a>

### run

```python
def run(self, code: str, code_type: str = 'python'):
```

Executes the given code with specified code type in the
interpreter.

This method takes a string of code and its type, checks if the code
type is supported, and then executes the code. If `unsafe_mode` is
set to `False`, the code is executed in a controlled environment using
the `execute` method. If `unsafe_mode` is `True`, the code is executed
using `eval()` or `exec()` with the action space as the global context.
An `InterpreterError` is raised if the code type is unsupported or if
any runtime error occurs during execution.

**Parameters:**

- **code** (str): The python code to be executed.
- **code_type** (str): The type of the code, which should be one of the supported code types (`python`, `py`, `python3`, `python2`). (default: obj:`python`)

**Returns:**

  str: The string representation of the output of the executed code.

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.update_action_space"></a>

### update_action_space

```python
def update_action_space(self, action_space: Dict[str, Any]):
```

Updates action space for *python* interpreter.

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.supported_code_types"></a>

### supported_code_types

```python
def supported_code_types(self):
```

Provides supported code types by the interpreter.

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.execute"></a>

### execute

```python
def execute(
    self,
    code: str,
    state: Optional[Dict[str, Any]] = None,
    fuzz_state: Optional[Dict[str, Any]] = None,
    keep_state: bool = True
):
```

Execute the input python codes in a security environment.

**Parameters:**

- **code** (str): Generated python code to be executed.
- **state** (Optional[Dict[str, Any]], optional): External variables that may be used in the generated code. (default: :obj:`None`)
- **fuzz_state** (Optional[Dict[str, Any]], optional): External variables that do not have certain variable names. The interpreter will use fuzzy matching to access these variables. For example, if :obj:`fuzz_state` has a variable :obj:`image`, the generated code can use :obj:`input_image` to access it. (default: :obj:`None`)
- **keep_state** (bool, optional): If :obj:`True`, :obj:`state` and :obj:`fuzz_state` will be kept for later execution. Otherwise, they will be cleared. (default: :obj:`True`)

**Returns:**

  Any: The value of the last statement (excluding "import") in the
code. For this interpreter, the value of an expression is its
value, the value of an "assign" statement is the assigned
value, and the value of an "if" and "for" block statement is
the value of the last statement in the block.

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.clear_state"></a>

### clear_state

```python
def clear_state(self):
```

Initialize :obj:`state` and :obj:`fuzz_state`.

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_ast"></a>

### _execute_ast

```python
def _execute_ast(self, expression: ast.AST):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_assign"></a>

### _execute_assign

```python
def _execute_assign(self, assign: ast.Assign):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._assign"></a>

### _assign

```python
def _assign(self, target: ast.expr, value: Any):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_call"></a>

### _execute_call

```python
def _execute_call(self, call: ast.Call):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_subscript"></a>

### _execute_subscript

```python
def _execute_subscript(self, subscript: ast.Subscript):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_name"></a>

### _execute_name

```python
def _execute_name(self, name: ast.Name):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_condition"></a>

### _execute_condition

```python
def _execute_condition(self, condition: ast.Compare):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_if"></a>

### _execute_if

```python
def _execute_if(self, if_statement: ast.If):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_for"></a>

### _execute_for

```python
def _execute_for(self, for_statement: ast.For):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_import"></a>

### _execute_import

```python
def _execute_import(self, import_module: ast.Import):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_import_from"></a>

### _execute_import_from

```python
def _execute_import_from(self, import_from: ast.ImportFrom):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._validate_import"></a>

### _validate_import

```python
def _validate_import(self, full_name: str):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_binop"></a>

### _execute_binop

```python
def _execute_binop(self, binop: ast.BinOp):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._execute_unaryop"></a>

### _execute_unaryop

```python
def _execute_unaryop(self, unaryop: ast.UnaryOp):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter._get_value_from_state"></a>

### _get_value_from_state

```python
def _get_value_from_state(self, key: str):
```

<a id="camel.interpreters.internal_python_interpreter.InternalPythonInterpreter.execute_command"></a>

### execute_command

```python
def execute_command(self, command: str):
```

Execute a command in the internal python interpreter.

**Parameters:**

- **command** (str): The command to execute.

**Returns:**

  tuple: A tuple containing the stdout and stderr of the command.
