from typing import List, Literal, Optional, Union

from camel.interpreters import (
    DockerInterpreter,
    E2BInterpreter,
    InternalPythonInterpreter,
    JupyterKernelInterpreter,
    SubprocessInterpreter,
)
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class MathCodeToolkit(BaseToolkit):
    r"""A toolkit for solving mathematical problems through code execution,
    with a special focus on symbolic computations using sympy.

    This toolkit is designed to help you solve math problems by executing
    Python code that leverages sympy. It supports various sandboxed environments
    for safe code execution, making it an ideal tool for performing algebraic
    manipulations, calculus operations, and other symbolic mathematics tasks.


    Args:
        sandbox (str): The environment type used to execute code. Options include:
            "internal_python", "jupyter", "docker", "subprocess", "e2b".
        verbose (bool): Whether to print the output of the code execution.
            (default: :obj:`False`)
        unsafe_mode (bool): If `True`, the interpreter runs the code using `eval()`
            without any security checks. (default: :obj:`False`)
        import_white_list (Optional[List[str]]): A list of allowed imports.
            (default: :obj:`None`)
        require_confirm (bool): Whether to require confirmation before executing code.
            (default: :obj:`False`)
    """

    def __init__(
        self,
        sandbox: Literal[
            "internal_python", "jupyter", "docker", "subprocess", "e2b"
        ] = "internal_python",
        verbose: bool = False,
        unsafe_mode: bool = False,
        import_white_list: Optional[List[str]] = None,
        require_confirm: bool = False,
        output_cap: int = 5000,
        timeout: int = 180,
    ) -> None:
        self.verbose = verbose
        self.unsafe_mode = unsafe_mode
        self.import_white_list = import_white_list or list()
        self.output_cap = output_cap
        self.timeout = timeout

        # Type annotation for interpreter to allow all possible types
        self.interpreter: Union[
            InternalPythonInterpreter,
            JupyterKernelInterpreter,
            DockerInterpreter,
            SubprocessInterpreter,
            E2BInterpreter,
        ]

        if sandbox == "internal_python":
            self.interpreter = InternalPythonInterpreter(
                unsafe_mode=self.unsafe_mode,
                import_white_list=self.import_white_list,
            )
        elif sandbox == "jupyter":
            self.interpreter = JupyterKernelInterpreter(
                require_confirm=require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif sandbox == "docker":
            self.interpreter = DockerInterpreter(
                require_confirm=require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif sandbox == "subprocess":
            self.interpreter = SubprocessInterpreter(
                require_confirm=require_confirm,
                print_stdout=self.verbose,
                print_stderr=self.verbose,
            )
        elif sandbox == "e2b":
            self.interpreter = E2BInterpreter(require_confirm=require_confirm)
        else:
            raise RuntimeError(
                f"The sandbox type `{sandbox}` is not supported."
            )

    def execute_code(self, code: str) -> str:
        r"""Execute a given Python code snippet for solving math problems.

        This function is particularly useful for executing code that utilizes sympy
        to perform symbolic mathematics. It can be used to evaluate expressions,
        solve equations, or carry out any math-related computations provided in the code.


        Ensure that your code:  

        1. **Uses Proper Indentation:** Strict adherence to correct Python indentation is required. Incorrect indentation may lead to execution errors.  
        2. **Provides a Solution in Symbolic Form:** If applicable, simplify the result using `simplify()`, `expand()`, or other relevant SymPy functions.  
        3. **Generate fully executable code**: Please always generate **the full executable** code and define all the variables. 
        4. **Define result from previous code**: Result from previous code should be directly hard-coded instead of recomputing it again.

        Args:
            code (str): The input Python code containing math problem solutions using sympy.

        Returns:
            str: A formatted string showing the executed code and its output.
        """
        code = "from sympy import *\nimport sympy as sp\n"+code
        output = self.interpreter.run(code, "python")
        if len(output) > self.output_cap:
            output = output[:self.output_cap] # take the first 2000 character to avoid overflow
            output += f"..Later output removed due to limit on output {self.output_cap}..."
        elif len(output) == 0:
            output = "No output from the stdout: did you print the final result?"
        content = (
            f"Executed the code below:\n```py\n{code}\n```\n> Execution Results:\n{output}"
        )
        if self.verbose:
            print(content)
        return content

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions in the math toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the available functions.
        """
        return [FunctionTool(self.execute_code)]
