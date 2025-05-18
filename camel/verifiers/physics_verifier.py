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

import asyncio
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from camel.extractors.base import BaseExtractor
from camel.logger import get_logger

from .models import VerificationOutcome, VerificationResult
from .python_verifier import PythonVerifier

logger = get_logger(__name__)


class UnitParser:
    r"""Class for handling unit parsing and manipulation operations."""

    def __init__(self):
        from sympy.physics import units

        # Base unit dictionary
        extra_allowed_units = {
            'hrs': units.hour,
            'min': units.minute,
            'Joule': units.joule,
            'Joules': units.joule,
            'circ': units.degree,
            "Omega": units.ohm,
            '%': units.Unit('percent'),
        }

        self.allowed_units = self._load_sympy_units()
        self.allowed_units.update(extra_allowed_units)

        # Add SI prefixed units
        self._add_si_prefixes()

    @staticmethod
    def _load_sympy_units() -> Dict[str, Any]:
        r"""Load all available units from sympy.physics.units.

        Returns:
            Dict[str, Any]: Dictionary mapping unit names to their
                corresponding sympy Quantity objects.
        """
        from sympy.physics import units

        sympy_units = {}

        for attr_name in dir(units):
            unit_obj = getattr(units, attr_name)
            if isinstance(unit_obj, units.Quantity):
                sympy_units[attr_name] = unit_obj

        return sympy_units

    def _add_si_prefixes(self):
        r"""Add SI prefixed units (like km, MHz, etc.) to the allowed units."""
        from sympy.physics.units.prefixes import PREFIXES

        prefixed_units = {}
        for prefix, prefix_obj in PREFIXES.items():
            for unit_name, base_unit in self.allowed_units.copy().items():
                prefixed_unit_name = (
                    f"{prefix}{unit_name}"  # Example: "MJ", "kN"
                )
                prefixed_units[prefixed_unit_name] = (
                    prefix_obj.scale_factor * base_unit
                )

        # Add only new prefixed units that don't conflict with existing ones
        prefixed_units = {
            k: v
            for k, v in prefixed_units.items()
            if k not in self.allowed_units
        }
        self.allowed_units.update(prefixed_units)

    def parse_unit(self, unit_str: str) -> Optional[Any]:
        r"""Parse a unit string into a SymPy expression using the appropriate
        method.

        Args:
            unit_str (str): The unit string to parse.

        Returns:
            Optional[Any]: SymPy expression representing the unit, or None
                if parsing fails or the unit is dimensionless.
        """

        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr

        if not unit_str or unit_str == "dimensionless":
            return None

        if "$" in unit_str or "\\" in unit_str:
            # Likely a LaTeX formatted string
            return self.parse_unit_with_latex(unit_str)

        # Standard unit string
        processed_str = self.preprocess_unit_string(unit_str)

        try:
            expr = parse_expr(
                processed_str, local_dict=self.allowed_units, evaluate=True
            )
            return sp.simplify(expr)
        except Exception as e:
            logger.info(
                f"Failed to parse unit '{unit_str}' (processed a"
                f"s '{processed_str}'): {e}"
            )
            return None

    def parse_unit_with_latex(self, unit_str: str) -> Any:
        r"""Parse a unit string using SymPy's LaTeX parser.

        Args:
            unit_str (str): The unit string in LaTeX format.

        Returns:
            Any: SymPy expression representing the unit, or the
                original string if parsing fails.
        """

        import sympy as sp
        from sympy.parsing.latex import parse_latex

        # Clean the LaTeX string
        unit_str = unit_str.strip().lstrip("$").rstrip("$").lstrip("^")
        unit_str = re.sub(r'\\mathrm\{([^}]*)\}', r'{\\\1}', unit_str)
        unit_str = re.sub(r'\\text\{(.*?)\}', r'\1', unit_str)
        unit_str = unit_str.replace('~', '')

        try:
            expr = parse_latex(unit_str)
            logger.info(f"Parsed LaTeX unit: {expr}.")
        except Exception as e:
            logger.warning(f"Failed to parse LaTeX unit '{unit_str}': {e}")
            return unit_str

        # Substitute allowed unit symbols
        for key, unit_obj in self.allowed_units.items():
            sym = sp.symbols(key)
            expr = expr.subs(sym, unit_obj)

        simplified_expr = sp.simplify(expr)
        logger.info(f"Simplified LaTeX unit: {simplified_expr}")
        return simplified_expr

    def detect_scaling_factor(
        self, unit_expr: Any
    ) -> Tuple[Union[int, float, Any], Any]:
        r"""Detect a scaling factor in the unit expression.

        Args:
            unit_expr (Any): The unit expression.

        Returns:
            Tuple[Union[int, float, Any], Any]: Tuple of scale
                factor and base unit.
        """

        import sympy as sp

        value, base_unit = self.extract_value_and_unit(unit_expr)

        if isinstance(value, (int, float, sp.Number)):
            return value, base_unit
        return 1, unit_expr

    @staticmethod
    def preprocess_unit_string(unit_str: str) -> str:
        r"""Preprocess a unit string to replace '^' with '**' for
        exponentiation.

        Args:
            unit_str (str): The unit string to preprocess.

        Returns:
            str: Preprocessed unit string.
        """
        superscript_map = {
            "\u00b2": "2",  # Superscript ²
            "\u00b3": "3",  # Superscript ³
            "\u2070": "0",
            "\u2071": "1",
            "\u2074": "4",
            "\u2075": "5",
            "\u2076": "6",
            "\u2077": "7",
            "\u2078": "8",
            "\u2079": "9",
        }

        for unicode_char, normal_char in superscript_map.items():
            unit_str = unit_str.replace(unicode_char, "**" + normal_char)

        unit_str = unit_str.replace('^', '**').strip()
        return unit_str

    @staticmethod
    def unit_is_none(unit_str: Optional[str]) -> bool:
        r"""Check if a unit string represents 'no unit' or is empty.

        Args:
            unit_str (Optional[str]): The unit string to check.

        Returns:
            bool: True if the unit is None or represents 'no unit'.
        """
        if unit_str is None:
            return True

        if isinstance(unit_str, str):
            unit_str = unit_str.strip().lower()

            if unit_str in ['none', '', 'dimensionless', 'unitless']:
                return True

        return False

    @staticmethod
    def extract_value_and_unit(
        expr: Any,
    ) -> Tuple[Union[int, float, Any], Any]:
        r"""Extract numerical value and unit components from a SymPy
        expression.

        Args:
            expr (Any): SymPy expression with units.

        Returns:
            Tuple[Union[int, float, Any], Any]: Numerical
                value and unit expression.
        """

        import sympy as sp

        factors = sp.Mul.make_args(expr)
        numeric_terms: List[Any] = []
        unit_terms: List[Any] = []

        for term in factors:
            if isinstance(term, (int, float, sp.Number)):
                numeric_terms.append(term)
            elif isinstance(term, sp.Symbol):
                unit_terms.append(term)
            elif hasattr(term, 'is_commutative') and term.is_commutative:
                # For other expressions like powers
                unit_terms.append(term)
            else:
                # For complex expressions, try to separate
                unit_terms.append(term)

        value = sp.Mul(*numeric_terms) if numeric_terms else 1
        unit_expr = sp.Mul(*unit_terms) if unit_terms else 1

        return value, unit_expr

    @staticmethod
    def detect_unit_args(unit_expr: Any) -> List[Any]:
        r"""Extract the base units from a composite SymPy unit expression.

        Args:
            unit_expr (Any): SymPy expression representing a composite unit.

        Returns:
            List[Any]: List of SymPy base unit components.
        """

        import sympy as sp

        factors = sp.Mul.make_args(unit_expr)
        base_units = [
            factor.base
            if hasattr(factor, 'is_Pow') and factor.is_Pow
            else factor
            for factor in factors
        ]
        return base_units


class PhysicsSolutionComparator:
    r"""Class for compare solutions and reference answers that contains value
    and units.

    Args:
        solution (str): The output from running the solution code.
        reference_answer (str): The reference answer to compare against.
        float_tolerance (Optional[float], optional): The tolerance for
            floating point comparisons. (default: :obj:`None`)
    """

    def __init__(
        self,
        solution: str,
        reference_answer: str,
        float_tolerance: Optional[float] = None,
    ) -> None:
        self.solution: str = solution
        self.reference_answer: str = reference_answer
        self.tolerance = (
            float(float_tolerance) if float_tolerance is not None else 1e-2
        )
        self.unit_parser: UnitParser = UnitParser()

        # Initialize fields that will be set in _get_value_unit_pairs
        self.gt_value: Any = None
        self.gt_unit: str = ''
        self.sol_value: Any = None
        self.sol_unit: str = ''
        self.gt_unit_expr: Any = None
        self.sol_unit_expr: Any = None

    @staticmethod
    def _split_value_unit(s: str) -> Tuple[str, str]:
        r"""Split a string into value and unit components.
        Handles LaTeX-style units enclosed in dollar signs.

        Args:
            s (str): The input string.

        Returns:
            Tuple[str, str]: Tuple of (value, unit) as strings.
        """
        # Check if we have a LaTeX unit at the end (pattern: $ followed by
        # anything up to $)
        if s.split(' ')[-1] == '':
            return s.strip(), ''

        latex_unit_match = re.search(r'\s(\$[^$]*\$)$', s)

        if latex_unit_match:
            # Extract the LaTeX unit part
            unit = latex_unit_match.group(1)
            # Remove the unit part from the original string to get the value
            value = s[: latex_unit_match.start()].strip()
            return value, unit

        # If no LaTeX unit, fall back to the original logic
        parts = s.split(' ')
        if len(parts) == 1:
            return parts[0], ''
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            return ' '.join(parts[:-1]), parts[-1]

    @staticmethod
    def _clean_answer(raw_answer: str) -> str:
        r"""Clean a raw answer string by removing LaTeX formatting.

        Args:
            raw_answer (str): The raw answer string potentially containing
                LaTeX formatting.

        Returns:
            str: The cleaned answer string without LaTeX formatting.
        """
        # Remove whitespace
        answer = raw_answer.strip()

        # Remove dollar signs that indicate LaTeX math mode
        if answer.startswith("$") and answer.endswith("$"):
            answer = answer[1:-1].strip()

        # Replace LaTeX scientific notation format (e.g., 1 \times 10^{14})
        answer = re.sub(
            r'([\d.]+)\s*\\times\s*10\^\{(\d+)\}', r'\1e\2', answer
        )

        # Remove \mathrm commands
        answer = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', answer)

        # Remove other common LaTeX formatting
        # answer = answer.replace('\\', '')

        return answer

    @staticmethod
    def _parse_expression(expr: Any) -> Any:
        r"""Parse an expression into a SymPy expression.

        Args:
            expr (Any): Expression to parse, can be a string, number, or other
                type.

        Returns:
            Any: Parsed SymPy expression.
        """

        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr

        # If already a number, return as is
        if isinstance(expr, (int, float)):
            return sp.Float(expr)

        # If not a string, try to convert to string first
        if not isinstance(expr, str):
            try:
                expr = str(expr)
            except Exception as e:
                logger.info(f"Failed to convert expression to string: {e}")
                return expr

        try:
            # Replace common symbols with their SymPy equivalents
            replacements = {
                sp.Symbol('pi'): sp.pi,
                sp.Symbol('e'): sp.E,
            }

            parsed_expr = parse_expr(expr)
            for old, new in replacements.items():
                parsed_expr = parsed_expr.subs(old, new)

            return parsed_expr
        except Exception as e:
            logger.info(f"Failed to parse expression '{expr}': {e}")
            return expr

    @staticmethod
    def _is_number(s: Any) -> bool:
        r"""Check if a value can be converted to a number.

        Args:
            s (Any): Value to check.

        Returns:
            bool: True if the value can be converted to a number.
        """
        if isinstance(s, (int, float)):
            return True

        if not isinstance(s, str):
            return False

        try:
            float(s)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _detect_tolerance(default_tolerance: float, value: str) -> float:
        if 'e' in value:
            match = re.match(r'(-?\d*\.?\d*)[eE]', value)
            significant_part = match.group(1) if match else value
            exponent_match = re.search(r'[eE]([+-]?\d+)', value)
            exponent = int(exponent_match.group(1)) if exponent_match else 0
        else:
            exponent = 0
            significant_part = value

        if float(value) == 0:
            factor = 1.0
        else:
            factor = float(value)

        if '.' in significant_part:
            decimal_places = len(significant_part.split('.')[1])
            rel_tol = float(
                abs(round(10 ** (exponent - decimal_places) / factor, 2))
            )
        else:
            rel_tol = float(abs(round(10**exponent / factor, 2)))

        # limit the maximum tolerance to (default_tolerance, 10 *
        # default_tolerance)
        rel_tol = min(rel_tol, 10 * default_tolerance)
        rel_tol = max(rel_tol, default_tolerance)

        logger.info(f"Detected tolerance: {rel_tol}")

        return rel_tol

    def _convert_units(self) -> None:
        r"""Convert the solution units to match gt units"""
        import sympy as sp
        from sympy.physics import units

        try:
            sol_with_unit = self.sol_value * self.sol_unit_expr

            # Get scaling factor and base gt units
            scaling_factor, base_unit = self.unit_parser.detect_scaling_factor(
                self.gt_unit_expr
            )

            gt_unit_args = self.unit_parser.detect_unit_args(base_unit)

            if len(gt_unit_args) > 1:
                logger.info(
                    f"Ground truth unit is a composite unit "
                    f"with: {gt_unit_args}"
                )

            # Perform the unit conversion
            converted_sol_expr = units.convert_to(sol_with_unit, gt_unit_args)
            logger.info(f'Converted solution expr: {converted_sol_expr}')

            self.sol_value, self.sol_unit_expr = (
                self.unit_parser.extract_value_and_unit(converted_sol_expr)
            )

            if not isinstance(self.sol_value, (int, float, sp.Number)):
                raise ValueError(
                    f"Failed to extract value from converted "
                    f"value: {self.sol_value}"
                )

            self.sol_value = float(self.sol_value)

            # Apply scaling factor if needed
            if scaling_factor != 1:
                logger.info(
                    f"Applying scaling factor {scaling_factor} for "
                    f"ground truth units"
                )
                self.sol_value /= scaling_factor
                self.sol_unit_expr *= scaling_factor

            logger.info(f'Converted solution value: {self.sol_value}')
            logger.info(f'Converted solution unit: {self.sol_unit_expr}')

        except Exception as e:
            logger.error(f'Unit conversion failed: {e}')

    @staticmethod
    def verify_unit(sol_unit_expr: Any, gt_unit_expr: Any) -> bool:
        try:
            import sympy as sp
            from sympy.physics import units

            logger.info(
                f"Comparing response unit ({sol_unit_expr}) with answer "
                f"unit ({gt_unit_expr})"
            )
            # Case 1: Both are Quantity objects - compare numerically
            if isinstance(sol_unit_expr, units.Quantity) and isinstance(
                gt_unit_expr, units.Quantity
            ):
                diff = sp.simplify(sol_unit_expr - gt_unit_expr)
                return diff == 0
            # Case 2: Both are general SymPy expressions (like Mul, Add,
            # Symbol) - try symbolic comparison
            elif isinstance(sol_unit_expr, sp.Expr) and isinstance(
                gt_unit_expr, sp.Expr
            ):
                try:
                    # Attempt to simplify the difference, handles compatible
                    # symbolic units
                    diff = sp.simplify(sol_unit_expr - gt_unit_expr)
                    return diff == 0
                except TypeError:
                    # If subtraction fails (e.g., incompatible symbolic
                    # units), compare directly
                    return sp.simplify(sol_unit_expr).equals(
                        sp.simplify(gt_unit_expr)
                    )
            # Case 3: Both are strings - compare directly
            elif isinstance(sol_unit_expr, str) and isinstance(
                gt_unit_expr, str
            ):
                return sol_unit_expr.strip() == gt_unit_expr.strip()
            # Case 4: Mixed or other types - cannot compare
            else:
                logger.warning(
                    f"Cannot compare units of incompatible "
                    f"types: {type(sol_unit_expr)} and {type(gt_unit_expr)}"
                )
                return False
        except Exception as e:
            logger.error("Failed to compare units: %s", e)
            return False

    def compare_solution_to_reference(self) -> VerificationResult:
        r"""Compare the solution output to the reference answer.

        Returns:
            VerificationResult with comparison status.
        """
        try:
            self._get_value_unit_pairs()
            logger.info(
                f"Solution value: {self.sol_value}; Ground truth "
                f"value: {self.gt_value}"
            )
            logger.info(
                f"Solution unit: {self.sol_unit_expr}; Ground truth "
                f"unit: {self.gt_unit_expr}"
            )

            if self._is_number(self.gt_value):
                # Ensure values are strings before calling string methods
                if isinstance(self.sol_value, str) and isinstance(
                    self.gt_value, str
                ):
                    self.sol_value, self.gt_value = (
                        self.sol_value.lower().strip(),
                        self.gt_value.lower().strip(),
                    )
                result_match = self._compare_numeric_values()
            else:
                result_match = self._compare_symbolic_values()

            if self.unit_parser.unit_is_none(self.gt_unit):
                # If the answer is dimensionless, the response should also be
                # dimensionless
                unit_match = self.unit_parser.unit_is_none(self.sol_unit)
            elif self.sol_unit_expr is None or self.gt_unit_expr is None:
                unit_match = False
            else:
                unit_match = self.verify_unit(
                    self.sol_unit_expr, self.gt_unit_expr
                )

            if result_match and unit_match:
                return VerificationResult(
                    status=VerificationOutcome.SUCCESS,
                    result=f'{self.sol_value} {self.sol_unit_expr}',
                )
            elif result_match:
                return VerificationResult(
                    status=VerificationOutcome.FAILURE,
                    result=f'{self.sol_value} {self.sol_unit_expr}',
                    error_message="Units do not match.",
                )
            elif unit_match:
                return VerificationResult(
                    status=VerificationOutcome.FAILURE,
                    result=f'{self.sol_value} {self.sol_unit_expr}',
                    error_message="Values do not match.",
                )
            else:
                return VerificationResult(
                    status=VerificationOutcome.FAILURE,
                    result=f'{self.sol_value} {self.sol_unit_expr}',
                    error_message="Both values and units do not match.",
                )
        except Exception as e:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result=f'{self.solution}',
                error_message=f"Comparison failed: {e}",
            )

    def _get_value_unit_pairs(self) -> None:
        self.gt_value, self.gt_unit = self._split_value_unit(
            self.reference_answer
        )

        if self.gt_unit == '':
            self.sol_value, self.sol_unit = self.solution, ''
        else:
            self.sol_value, self.sol_unit = self._split_value_unit(
                self.solution
            )

        self.gt_value = self._clean_answer(self.gt_value)

        if self.unit_parser.unit_is_none(
            self.gt_unit
        ) and self.unit_parser.unit_is_none(self.sol_unit):
            self.gt_unit_expr, self.sol_unit_expr = None, None
        else:
            self.gt_unit_expr = self.unit_parser.parse_unit(self.gt_unit)
            self.sol_unit_expr = self.unit_parser.parse_unit(self.sol_unit)

    def _compare_numeric_values(self) -> bool:
        r"""Compare numerical values, with unit conversion if needed."""
        rel_tol = self._detect_tolerance(self.tolerance, self.gt_value)
        self.gt_value = float(self.gt_value)

        if self._is_number(self.sol_value):
            self.sol_value = float(self.sol_value)
        else:
            logger.info(
                f'Convert output expr {self.sol_value} into numerical.'
            )
            try:
                sol_expr = self._parse_expression(self.sol_value)
                self.sol_value = sol_expr.evalf()
            except Exception as e:
                raise ValueError(
                    f"Failed to evaluate output {self.sol_value}: {e}"
                )

        if (
            self.gt_unit_expr is not None
            and self.sol_unit_expr is not None
            and not self.verify_unit(self.gt_unit_expr, self.sol_unit_expr)
        ):
            logger.info(
                'Units do not match directly. Attempting conversion...'
            )
            self._convert_units()

        # try:
        # Compare numerical values
        logger.info(f'Solution value: {self.sol_value}')
        logger.info(f'Ground truth value: {self.gt_value}')

        return math.isclose(self.sol_value, self.gt_value, rel_tol=rel_tol)

    def _compare_symbolic_values(self) -> bool:
        r"""Compare symbolic expressions for equivalence."""

        import sympy as sp

        gt_expr = self._parse_expression(self.gt_value)
        sol_expr = self._parse_expression(self.sol_value)

        logger.info(f'Solution expression: {sol_expr}')
        logger.info(f'Ground truth expression: {gt_expr}')

        sol_symbols = sol_expr.free_symbols
        gt_symbols = gt_expr.free_symbols

        if sol_symbols != gt_symbols:
            symbol_mapping = {}
            for gt_sym in gt_symbols:
                gt_name = str(gt_sym)
                for sol_sym in sol_symbols:
                    if str(sol_sym) == gt_name:
                        symbol_mapping[gt_sym] = sol_sym
                        break
            gt_expr = gt_expr.subs(symbol_mapping)

        # Handle Equalities
        if isinstance(sol_expr, sp.Eq) and isinstance(gt_expr, sp.Eq):
            sol_expr = sp.simplify(sol_expr.rhs)
            gt_expr = sp.simplify(gt_expr.rhs)
        elif not isinstance(sol_expr, sp.Eq) and not isinstance(
            gt_expr, sp.Eq
        ):
            sol_expr = sp.simplify(sol_expr)
            gt_expr = sp.simplify(gt_expr)
        else:
            raise ValueError(
                f"Cannot compare an equation with a non-equation "
                f"directly: {sol_expr}, {gt_expr}"
            )

        try:
            self.sol_value = float(
                sol_expr
                if isinstance(sol_expr, (int, float, sp.Number))
                else sol_expr.evalf()
            )
            self.gt_value = float(
                gt_expr
                if isinstance(gt_expr, (int, float, sp.Number))
                else gt_expr.evalf()
            )
            return math.isclose(
                self.sol_value, self.gt_value, rel_tol=self.tolerance
            )
        except Exception:
            try:
                return math.isclose(sol_expr, gt_expr, rel_tol=self.tolerance)
            except Exception:
                return sol_expr == gt_expr


class PhysicsVerifier(PythonVerifier):
    r"""The PhysicsVerifier inherits PythonVerifier and makes it able to
    compare and convert units.

    Args:
        extractor (Optional[BaseExtractor]): The extractor to use for
            extracting code from messages. (default: :obj:`None`)
        timeout (Optional[float]): The timeout for code execution in seconds.
            (default: :obj:`30.0`)
        required_packages (Optional[List[str]]): The required packages for code
            execution. (default: :obj:`None`)
        float_tolerance (Optional[float]): The relative tolerance used to
            compare numerical values. (default: :obj:`None`)
        **kwargs: Additional keyword arguments to pass to the parent class.
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        timeout: Optional[float] = 30.0,
        required_packages: Optional[List[str]] = None,
        float_tolerance: Optional[float] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            extractor=extractor,
            timeout=timeout,
            required_packages=required_packages,
            **kwargs,
        )
        self.tolerance = float_tolerance

    async def _verify_implementation(
        self, solution: str, reference_answer: Optional[str]
    ) -> VerificationResult:
        # Check for virtual environment setup
        if not self.venv_path:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Virtual environment is not set up.",
            )

        # run the code block,
        # which should already include a print(...) in the end
        venv_python = os.path.join(
            self.venv_path,
            self.bin_dir,
            "python.exe" if os.name == 'nt' else "python",
        )
        if not os.path.exists(venv_python):
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Python binary not found in virtual environment",
            )

        try:
            sol_out, sol_err, sol_code = await self._run_code_block(
                solution, venv_python
            )
            if sol_code != 0:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result=sol_out,
                    error_message=f"Solution code error:\n{sol_err}",
                )

            logger.info(f"Solution: {sol_out}")

            if reference_answer is None:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result="",
                    error_message=(
                        "Reference answer is required for physics "
                        "verification."
                    ),
                )

            comparator = PhysicsSolutionComparator(
                sol_out, reference_answer, self.tolerance
            )

            return comparator.compare_solution_to_reference()

        except asyncio.TimeoutError:
            return VerificationResult(
                status=VerificationOutcome.TIMEOUT,
                result="",
                error_message="Execution timed out.",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=f"Unexpected error: {e}",
            )
