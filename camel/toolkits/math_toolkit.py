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

import subprocess
import sys
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
            for mathematical computations (e.g., `numpy`, `sympy`, `cvxpy`,
              `scipy`, `networkx`).
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
        auto_install (bool): If True, automatically install required packages
            during initialization. (default: :obj:`False`)
    """

    def __init__(
        self,
        math_packages: Optional[Union[List[str], str]] = None,
        sandbox: Literal[
            "internal_python", "jupyter", "docker", "subprocess", "e2b"
        ] = "subprocess",
        verbose: bool = False,
        unsafe_mode: bool = False,
        import_white_list: Optional[List[str]] = None,
        require_confirm: bool = False,
        auto_install: bool = False,
    ) -> None:
        self.math_packages = [
            'math'
        ]  # Always include the built-in math module

        # Support a single string or a list of strings
        if math_packages:
            if isinstance(math_packages, str):
                self.math_packages.append(math_packages.lower())
            else:
                self.math_packages.extend(
                    [pkg.lower() for pkg in math_packages]
                )

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

        # Optionally install packages during initialization
        if auto_install:
            self._install_packages()

    def add(self, a: Union[float, int], b: Union[float, int]) -> float:
        r"""Adds two numbers.

        Args:
            a (Union[float, int]): The first number to be added.
            b (Union[float, int]): The second number to be added.

        Returns:
            float: The sum of the two numbers.
        """
        return a + b

    def sub(self, a: Union[float, int], b: Union[float, int]) -> float:
        r"""Do subtraction between two numbers.

        Args:
            a (Union[float, int]): The minuend in subtraction.
            b (Union[float, int]): The subtrahend in subtraction.

        Returns:
            float: The result of subtracting :obj:`b` from :obj:`a`.
        """
        return a - b

    def multiply(
        self,
        a: Union[float, int],
        b: Union[float, int],
        decimal_places: int = 2,
    ) -> float:
        r"""Multiplies two numbers.

        Args:
            a (Union[float, int]): The multiplier in the multiplication.
            b (Union[float, int]): The multiplicand in the multiplication.
            decimal_places (int, optional): The number of decimal
                places to round to. (default: :obj:`2`)

        Returns:
            float: The product of the two numbers.
        """
        return round(a * b, decimal_places)

    def divide(
        self,
        a: Union[float, int],
        b: Union[float, int],
        decimal_places: int = 2,
    ) -> float:
        r"""Divides two numbers.

        Args:
            a (Union[float, int]): The dividend in the division.
            b (Union[float, int]): The divisor in the division.
            decimal_places (int, optional): The number of
                decimal places to round to. (default: :obj:`2`)

        Returns:
            float: The result of dividing :obj:`a` by :obj:`b`.
        """
        if b == 0:
            raise ValueError("Division by zero is not allowed")
        return round(a / b, decimal_places)

    def round(self, a: float, decimal_places: int = 0) -> float:
        r"""Rounds a number to a specified number of decimal places.
        Args:
            a (float): The number to be rounded.
            decimal_places (int, optional): The number of decimal places
                to round to. (default: :obj:`0`)
        Returns:
            float: The rounded number.
        """
        return round(a, decimal_places)

    def _install_packages(self) -> None:
        r"""Install required math packages using pip.

        First tries to use uv if available, falls back to pip if not.
        Installs packages one at a time to better handle failures.

        Raises:
            RuntimeError: If package installation fails.
        """
        if not self.math_packages:
            return

        # Try uv first
        try:
            subprocess.run(
                [sys.executable, '-m', 'uv', '--version'],
                check=True,
                capture_output=True,
            )
            installer = [sys.executable, '-m', 'uv', 'pip', 'install']
        except subprocess.CalledProcessError:
            # Fall back to pip
            installer = [sys.executable, '-m', 'pip', 'install']

        for package in self.math_packages:
            if package == 'math':  # Skip built-in modules
                continue
            try:
                subprocess.run(
                    [*installer, package], check=True, capture_output=True
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to install {package}: {e.stderr.decode()}"
                )

    def _generate_imports(self) -> str:
        r"""Generate import statements for the specified math packages.

        Returns:
            str: A string containing import statements for all math packages.
        """
        return '\n'.join(f'import {pkg}' for pkg in self.math_packages)

    def solve_math_with_code(self, code: str) -> str:
        r"""Execute mathematical computations using Python's math packages.

        Args:
            code (str): Python code containing mathematical computations.

        Returns:
            str: The result of the code execution.

        Raises:
            RuntimeError: If code execution fails or times out.
        """

        full_code = f"{self._generate_imports()}\n\n{code}"
        return self.execute_code(full_code)

    def install_math_packages(
        self, packages: Optional[List[str]] = None
    ) -> str:
        r"""Install specified math packages.

        Args:
            packages (Optional[List[str]]): Optional list of packages to
                install. If not provided, uses the packages specified during
                initialization. (default: :obj:`None`)

        Returns:
            str: Message indicating success or failure.
        """
        if packages:
            seen = set()
            self.math_packages = []
            for x in packages:
                if x not in seen:
                    self.math_packages.append(x)
                    seen.add(x)

        try:
            self._install_packages()
            packages_str = ', '.join(self.math_packages)
            msg = f"Successfully installed packages: {packages_str}"
            return msg
        except Exception as e:
            return f"Failed to install packages: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Get a list of FunctionTool objects for the toolkit's methods.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects wrapping the
                toolkit's methods (`add`, `sub`, `multiply`, `divide`, `round`,
                `solve_math_with_code`, `install_math_packages`).
        """
        return [
            FunctionTool(self.add),
            FunctionTool(self.sub),
            FunctionTool(self.multiply),
            FunctionTool(self.divide),
            FunctionTool(self.round),
            FunctionTool(self.solve_math_with_code),
            FunctionTool(self.install_math_packages),
        ]
