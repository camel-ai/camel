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

import logging
from typing import List, Literal, Optional, Union

from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer


@MCPServer()
class MathToolkit(CodeExecutionToolkit):
    r"""A toolkit for performing basic and advanced mathematical computations.

    Attributes:
        math_packages (list): List of math packages to use.

    Args:
        math_packages (List[str], optional): List of Python packages to use
            for mathematical computations (e.g., `numpy`, `sympy`).
        sandbox (str, optional): The environment for code execution
            (`internal_python`, `jupyter`, `docker`, `subprocess`, `e2b`).
            (default: `subprocess`)
        verbose (bool, optional): If True, prints code execution output.
            (default: :obj:`False`)
        unsafe_mode (bool): If `True`, the interpreter runs the code
            by `eval()` without any security check. (default: :obj:`False`)
        import_white_list (Optional[List[str]]): A list of allowed imports.
            (default: :obj:`None`)
        require_confirm (bool): Whether to require confirmation before
            executing code. (default: :obj:`False`)
    """

    def __init__(
        self,
        math_packages: Optional[List[str]] = None,
        sandbox: Literal[
            "internal_python", "jupyter", "docker", "subprocess", "e2b"
        ] = "subprocess",
        verbose: bool = False,
        unsafe_mode: bool = False,
        import_white_list: Optional[List[str]] = None,
        require_confirm: bool = False,
    ) -> None:
        self.math_packages = [
            'math'
        ]  # Always include the built-in math module
        if math_packages:
            self.math_packages.extend([pkg.lower() for pkg in math_packages])

        import_white_list = list(
            set(import_white_list or []) | set(self.math_packages)
        )
        super().__init__(
            sandbox=sandbox,
            verbose=verbose,
            unsafe_mode=unsafe_mode,
            import_white_list=import_white_list,
            require_confirm=require_confirm,
        )
        self._install_packages()

    def _round_result(self, value: float, decimal_places: int) -> float:
        r"""Round a number to the specified number of decimal places.

        Args:
            value: The number to round.
            decimal_places: Number of decimal places to round to.

        Returns:
            float: The rounded number.
        """
        return round(value, decimal_places)

    def add(self, a: Union[float, int], b: Union[float, int]) -> float:
        r"""Adds two numbers.

        Args:
            a (float): The first number to be added.
            b (float): The second number to be added.

        Returns:
            float: The sum of the two numbers.
        """
        return float(a) + float(b)

    def sub(self, a: Union[float, int], b: Union[float, int]) -> float:
        r"""Do subtraction between two numbers.

        Args:
            a (float): The minuend in subtraction.
            b (float): The subtrahend in subtraction.

        Returns:
            float: The result of subtracting :obj:`b` from :obj:`a`.
        """
        return float(a) - float(b)

    def multiply(
        self,
        a: Union[float, int],
        b: Union[float, int],
        decimal_places: int = 2,
    ) -> float:
        r"""Multiplies two numbers.

        Args:
            a (float): The multiplier in the multiplication.
            b (float): The multiplicand in the multiplication.
            decimal_places (int, optional): The number of decimal
                places to round to. Defaults to 2.

        Returns:
            float: The product of the two numbers.
        """
        return self._round_result(float(a) * float(b), decimal_places)

    def divide(
        self,
        a: Union[float, int],
        b: Union[float, int],
        decimal_places: int = 2,
    ) -> float:
        r"""Divides two numbers.

        Args:
            a (float): The dividend in the division.
            b (float): The divisor in the division.
            decimal_places (int, optional): The number of
                decimal places to round to. Defaults to 2.

        Returns:
            float: The result of dividing :obj:`a` by :obj:`b`.
        """
        if b == 0:
            raise ValueError("Division by zero is not allowed")
        return self._round_result(float(a) / float(b), decimal_places)

    def round(self, a: Union[float, int], decimal_places: int = 0) -> float:
        r"""Round a number to the specified number of decimal places.

        Args:
            a: The number to round.
            decimal_places: Number of decimal places to round to.
                Defaults to 0.

        Returns:
            float: The rounded number.
        """
        return self._round_result(float(a), decimal_places)

    def _install_packages(self) -> None:
        r"""Install required math packages using pip.

        Attempts to import each package and installs it if not already
        available. Skips the built-in `math` package.

        Raises:
            RuntimeError: If a package installation fails.
        """
        logger = logging.getLogger(__name__)
        packages_to_install = [
            pkg for pkg in self.math_packages if pkg != 'math'
        ]
        if not packages_to_install:
            return

        for package in packages_to_install:
            try:
                __import__(package)
                logger.info(f"Package {package} is already installed.")
            except ImportError:
                logger.info(f"Installing {package}...")
                install_code = f"""
                import sys
                import subprocess
                try:
                    subprocess.check_call([
                        sys.executable,
                        '-m', 'pip', 'install', '{package}'
                    ])
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f'Failed to install {package}: {{e}}')
                """
                self.execute_code(install_code)
                logger.info(f"Successfully installed {package}")

    def _generate_imports(self) -> str:
        r"""Generate import statements for the specified math packages.

        Uses standard aliases for common packages (e.g., `numpy as np`) and
        simple `import` statements for others.

        Returns:
            str: A string containing import statements for all math packages.
        """
        package_aliases = {
            'math': 'import math',
            'numpy': 'import numpy as np',
            'sympy': 'import sympy as sp',
            'scipy': 'from scipy import *',
            'pandas': 'import pandas as pd',
        }
        imports = []
        for pkg in self.math_packages:
            if pkg in package_aliases:
                imports.append(package_aliases[pkg])
            else:
                # For custom packages, use a simple import statement
                imports.append(f"import {pkg}")
        return '\n'.join(imports)

    def solve_math(self, code: str) -> str:
        r"""Execute mathematical computations using Python's math packages.

        Combines the provided code with import statements for the specified
        packages and executes it in a sandboxed environment.

        Args:
            code: Python code containing mathematical computations.

        Returns:
            str: The result of the code execution.

        Raises:
            RuntimeError: If code execution fails or times out.
        """
        full_code = f"{self._generate_imports()}\n\n{code}"
        return self.execute_code(full_code)

    def get_tools(self) -> List[FunctionTool]:
        r"""Get a list of FunctionTool objects for the toolkit's methods.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects wrapping the
                toolkit's methods (`add`, `sub`, `multiply`, `divide`, `round`,
                `solve_math`).
        """
        return [
            FunctionTool(self.add),
            FunctionTool(self.sub),
            FunctionTool(self.multiply),
            FunctionTool(self.divide),
            FunctionTool(self.round),
            FunctionTool(self.solve_math),
        ]
