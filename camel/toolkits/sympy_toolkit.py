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

import json
import logging
from typing import List, Optional

import sympy as sp  # type: ignore[import]

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class SymPyToolkit(BaseToolkit):
    r"""A toolkit for performing symbolic computations using SymPy.
    This includes methods for Algebraic manipulation calculus
    and Linear Algebra
    """

    def __init__(self, default_variable: str = 'x', log_level=logging.INFO):
        r"""
        Initializes the toolkit with a default variable and logging.

        Args:
            default_variable (str): The default variable for
            operations (default: 'x').
            log_level (int): The logging level (default: logging.INFO).
        """

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.default_variable = sp.symbols(default_variable)
        self.logger.info(f"Default variable set to: {default_variable}")

    def simplify_expression(self, expression: str) -> str:
        r"""Simplifies a mathematical expression.

        Args:
            expression (str): The mathematical expression to simplify,
                provided as a string.

        Returns:
            str: JSON string containing the simplified mathematical
                expression in the `"result"` field. If an error occurs,
                the `"status"` field will be set to `"error"` with a
                corresponding `"message"`.

        Raises:
            Exception: If there is an error during the simplification
                process, such as invalid input or unsupported syntax.
        """
        try:
            self.logger.info(f"Simplifying expression: {expression}")
            expr = sp.sympify(expression)
            simplified = sp.simplify(expr)
            return json.dumps({"status": "success", "result": str(simplified)})
        except Exception as e:
            self.logger.error(
                f"Error simplifying expression: {expression} - {e}"
            )
            return json.dumps({"status": "error", "message": str(e)})

    def expand_expression(self, expression: str) -> str:
        r"""Expands an algebraic expression.

        Args:
            expression (str): The algebraic expression to expand,
                provided as a string.

        Returns:
            str: JSON string containing the expanded algebraic expression
                in the `"result"` field. If an error occurs, the JSON
                string will include an `"error"` field with the corresponding
                error message.

        Raises:
            Exception: If there is an error during the expansion process,
                such as invalid input or unsupported syntax.
        """
        try:
            self.logger.info(f"Expanding expression: {expression}")
            expr = sp.sympify(expression)
            expanded_expr = sp.expand(expr)
            return json.dumps({"result": str(expanded_expr)})
        except Exception as e:
            return self.handle_exception("expand_expression", e)

    def factor_expression(self, expression: str) -> str:
        r"""Factors an algebraic expression.

        Args:
            expression (str): The algebraic expression to factor,
                provided as a string.

        Returns:
            str: JSON string containing the factored algebraic expression
                in the `"result"` field. If an error occurs, the JSON string
                will include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the factoring process,
                such as invalid input or unsupported syntax.
        """
        try:
            self.logger.info(f"Factoring expression: {expression}")
            expr = sp.sympify(expression)
            factored_expr = sp.factor(expr)
            return json.dumps({"result": str(factored_expr)})
        except Exception as e:
            return self.handle_exception("factor_expression", e)

    def solve_linear_system(self, equations: list, variables: list) -> str:
        r"""Solves a system of linear equations.

        Args:
            equations (list): A list of strings representing the linear
                equations to be solved.
            variables (list): A list of strings representing the variables
                involved in the equations.

        Returns:
            str: JSON string containing the solution to the system of equations
                in the `"result"` field. Each solution is represented as
                a tuple of values corresponding to the variables. If an
                error occurs, the JSON string will include an `"error"`
                field with the corresponding error message.

        Raises:
            Exception: If there is an error during the solving process, such as
                invalid equations, incompatible variables, or an
                unsolvable system.
        """
        try:
            self.logger.info(
                f"""Solving linear system: {equations}
                with variables: {variables}"""
            )
            eqs = [sp.sympify(eq) for eq in equations]
            vars = sp.symbols(variables)
            solution = sp.linsolve(eqs, vars)
            return json.dumps({"result": [str(sol) for sol in solution]})
        except Exception as e:
            return self.handle_exception("solve_linear_system", e)

    def solve_nonlinear_system(self, equations: list, variables: list) -> str:
        r"""Solves a system of nonlinear equations.

        Args:
            equations (list): A list of strings representing the nonlinear
                equations to be solved.
            variables (list): A list of strings representing the variables
                involved in the equations.

        Returns:
            str: JSON string containing the solutions to the system of
                equations in the `"result"` field. Each solution is
                represented as a tuple of values corresponding to the
                variables. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding
                error message.

        Raises:
            Exception: If there is an error during the solving process,
                such as invalid equations, incompatible variables, or
                an unsolvable system.
        """
        try:
            self.logger.info(
                f"""Solving nonlinear system: {equations}
                with variables: {variables}"""
            )
            eqs = [sp.sympify(eq) for eq in equations]
            vars = sp.symbols(variables)
            solution = sp.nonlinsolve(eqs, vars)
            return json.dumps({"result": [str(sol) for sol in solution]})
        except Exception as e:
            return self.handle_exception("solve_nonlinear_system", e)

    def solve_univariate_inequality(
        self, inequality: str, variable: str
    ) -> str:
        r"""Solves a single-variable inequality.

        Args:
            inequality (str): A string representing the inequality
                to be solved.
            variable (str): The variable in the inequality.

        Returns:
            str: JSON string containing the solution to the inequality in the
                `"result"` field. The solution is represented in a symbolic
                format (e.g., intervals or expressions). If an error occurs,
                the JSON string will include an `"error"` field with the
                corresponding error message.

        Raises:
            Exception: If there is an error during the solving process, such as
                invalid input, unsupported syntax, or issues with the variable
                definition.
        """
        try:
            self.logger.info(
                f"""Solving univariate inequality: {inequality} 
                for variable: {variable}"""
            )
            var = sp.symbols(variable)
            ineq = sp.sympify(inequality)
            solution = sp.solve_univariate_inequality(ineq, var)
            return json.dumps({"result": str(solution)})
        except Exception as e:
            return self.handle_exception("solve_univariate_inequality", e)

    def reduce_inequalities(self, inequalities: list) -> str:
        r"""Reduces a system of inequalities.

        Args:
            inequalities (list): A list of strings representing the
                inequalities to be reduced.

        Returns:
            str: JSON string containing the reduced system of inequalities
                in the `"result"` field. The solution is represented in
                a symbolic format (e.g., combined intervals or expressions).
                If an error occurs, the JSON string will include an `"error"`
                field with the corresponding error message.

        Raises:
            Exception: If there is an error during the reduction process, such
                as invalid input, unsupported syntax, or inconsistencies in the
                inequalities.
        """
        try:
            self.logger.info(f"Reducing inequalities: {inequalities}")
            ineqs = [sp.sympify(ineq) for ineq in inequalities]
            solution = sp.reduce_inequalities(ineqs)
            return json.dumps({"result": str(solution)})
        except Exception as e:
            return self.handle_exception("reduce_inequalities", e)

    def polynomial_representation(self, expression: str, variable: str) -> str:
        r"""Represents an expression as a polynomial.

        Args:
            expression (str): The mathematical expression to represent as
                a polynomial, provided as a string.
            variable (str): The variable with respect to which the polynomial
                representation will be created.

        Returns:
            str: JSON string containing the polynomial representation of the
                expression in the `"result"` field. The polynomial is returned
                in a symbolic format. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the polynomial conversion
                process, such as invalid input or unsupported syntax.
        """
        try:
            self.logger.info(
                f"""Creating polynomial representation of: {expression} 
                with variable: {variable}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            poly = sp.Poly(expr, var)
            return json.dumps({"result": str(poly)})
        except Exception as e:
            return self.handle_exception("polynomial_representation", e)

    def polynomial_degree(self, expression: str, variable: str) -> str:
        r"""Returns the degree of a polynomial.

        Args:
            expression (str): The polynomial expression for which the degree
                is to be determined, provided as a string.
            variable (str): The variable with respect to which the degree
                of the polynomial is calculated.

        Returns:
            str: JSON string containing the degree of the polynomial in the
                `"result"` field. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the degree calculation
                process, such as invalid input, unsupported syntax, or if
                the expression is not a valid polynomial.
        """
        try:
            self.logger.info(
                f"""Getting degree of polynomial: {expression} 
                with variable: {variable}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            degree = int(sp.degree(expr, var))
            return json.dumps({"result": degree})
        except Exception as e:
            return self.handle_exception("polynomial_degree", e)

    def polynomial_coefficients(self, expression: str, variable: str) -> str:
        r"""Returns the coefficients of a polynomial.

        Args:
            expression (str): The polynomial expression from which the
                coefficients are to be extracted, provided as a string.
            variable (str): The variable with respect to which the polynomial
                coefficients are determined.

        Returns:
            str: JSON string containing the list of coefficients of the
                polynomial in the `"result"` field. The coefficients are
                ordered from the highest degree term to the constant term.
                If an error occurs, the JSON string will include an `"error"
                field with the corresponding error message.

        Raises:
            Exception: If there is an error during the coefficient extraction
                process, such as invalid input, unsupported syntax, or if the
                expression is not a valid polynomial.
        """
        try:
            self.logger.info(
                f"""Getting coefficients of polynomial: {expression} 
                with variable: {variable}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            coeffs = sp.Poly(expr, var).all_coeffs()
            return json.dumps({"result": [str(coeff) for coeff in coeffs]})
        except Exception as e:
            return self.handle_exception("polynomial_coefficients", e)

    def solve_equation(
        self, equation: str, variable: Optional[str] = None
    ) -> str:
        r"""Solves an equation for a specific variable.

        Args:
            equation (str): The equation to solve, provided as a string.
            variable (str, optional): The variable to solve for. If not
                specified, the function will use the default variable.

        Returns:
            str: JSON string containing the solutions to the equation in the
                `"result"` field. Each solution is represented as a string.
                If an error occurs, the JSON string will include an `"error"`
                field with the corresponding error message.

        Raises:
            Exception: If there is an error during the solving process, such as
                invalid input, unsupported syntax, or an undefined variable.
        """
        try:
            variable = (
                sp.symbols(variable) if variable else self.default_variable
            )
            self.logger.info(f"Solving equation: {equation} for {variable}")
            eq = sp.sympify(equation)
            solutions = sp.solve(eq, variable)
            return json.dumps({"result": [str(sol) for sol in solutions]})
        except Exception as e:
            return self.handle_exception("solve_equation", e)

    def find_roots(self, expression: str) -> str:
        r"""Finds the roots of a polynomial or algebraic equation.

        Args:
            expression (str): The polynomial or algebraic equation for which
                the roots are to be found, provided as a string.

        Returns:
            str: JSON string containing the roots of the expression in the
                `"result"` field. The roots are represented as a list of
                solutions. If an error occurs, the JSON string will include
                a `"status"` field set to `"error"` and a `"message"` field
                with the corresponding error description.

        Raises:
            ValueError: If the input expression is empty or contains only
                whitespace.
            Exception: If there is an error during the root-finding process,
                such as invalid input, unsupported syntax, or if the equation
                is not solvable.
        """
        try:
            self.logger.info(f"Finding roots for expression: {expression}")
            if not expression.strip():
                raise ValueError(
                    "Expression cannot be empty or whitespace"
                )  # is this necessary
            expr = sp.sympify(expression)
            roots = sp.solve(expr)
            return json.dumps({"status": "success", "result": str(roots)})

        except Exception as e:
            self.logger.error(
                f"Error finding roots for expression: {expression} - {e}"
            )
            return json.dumps({"status": "error", "message": str(e)})

    def differentiate(
        self, expression: str, variable: Optional[str] = None
    ) -> str:
        r"""Differentiates an expression with respect to a variable.

        Args:
            expression (str): The mathematical expression to differentiate,
                provided as a string.
            variable (str, optional): The variable with respect to which the
                differentiation is performed. If not specified, the default
                variable is used.

        Returns:
            str: JSON string containing the derivative of the expression in the
                `"result"` field. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the differentiation process,
                such as invalid input, unsupported syntax, or issues with the
                variable definition.
        """
        try:
            variable = (
                sp.symbols(variable) if variable else self.default_variable
            )
            self.logger.info(
                f"Differentiating {expression} with respect to {variable}"
            )
            expr = sp.sympify(expression)
            derivative = sp.diff(expr, variable)
            return json.dumps({"result": str(derivative)})
        except Exception as e:
            return self.handle_exception("differentiate", e)

    def integrate(
        self, expression: str, variable: Optional[str] = None
    ) -> str:
        r"""Integrates an expression with respect to a variable.

        Args:
            expression (str): The mathematical expression to integrate,
                provided as a string.
            variable (str, optional): The variable with respect to which the
                integration is performed. If not specified, the default
                variable is used.

        Returns:
            str: JSON string containing the integral of the expression in the
                `"result"` field. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the integration process,
                such as invalid input, unsupported syntax, or issues with
                the variable definition.
        """
        try:
            variable = (
                sp.symbols(variable) if variable else self.default_variable
            )
            self.logger.info(
                f"Integrating {expression} with respect to {variable}"
            )
            expr = sp.sympify(expression)
            integral = sp.integrate(expr, variable)
            return json.dumps({"result": str(integral)})
        except Exception as e:
            return self.handle_exception("integrate", e)

    def definite_integral(
        self, expression: str, variable: str, lower: float, upper: float
    ) -> str:
        r"""Computes the definite integral of an expression within given
        bounds.

        Args:
            expression (str): The mathematical expression to integrate,
                provided as a string.
            variable (str): The variable with respect to which the definite
                integration is performed.
            lower (float): The lower limit of the integration.
            upper (float): The upper limit of the integration.

        Returns:
            str: JSON string containing the result of the definite integral
                in the `"result"` field. If an error occurs, the JSON string
                will include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the definite integration
                process, such as invalid input, unsupported syntax, or issues
                with the variable or bounds.
        """
        try:
            self.logger.info(
                f"""Computing definite integral of: {expression} 
                with respect to {variable} from {lower} to {upper}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            integral = sp.integrate(expr, (var, lower, upper))
            return json.dumps({"result": str(integral)})
        except Exception as e:
            return self.handle_exception("definite_integral", e)

    def series_expansion(
        self, expression: str, variable: str, point: float, order: int
    ) -> str:
        r"""Expands an expression into a Taylor series around a given point up
        to a specified order.

        Args:
            expression (str): The mathematical expression to expand, provided
                as a string.
            variable (str): The variable with respect to which the series
                expansion is performed.
            point (float): The point around which the Taylor series is
                expanded.
            order (int): The order up to which the series expansion is
            computed.

        Returns:
            str: JSON string containing the Taylor series expansion of the
                expression in the `"result"` field. If an error occurs,
                the JSON string will include an `"error"` field with the
                corresponding error message.

        Raises:
            Exception: If there is an error during the series expansion
                process, such as invalid input, unsupported syntax, or
                issues with the variable, point, or order.
        """
        try:
            self.logger.info(
                f"""Expanding expression: {expression} 
                into Taylor series at {point} up to order {order}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            series = sp.series(expr, var, point, order)
            return json.dumps({"result": str(series)})
        except Exception as e:
            return self.handle_exception("series_expansion", e)

    def compute_limit(
        self,
        expression: str,
        variable: str,
        point: float,
        direction: str = 'both',
    ) -> str:
        r"""Computes the limit of an expression as a variable approaches
        a point.

        Args:
            expression (str): The mathematical expression for which the limit
                is to be computed, provided as a string.
            variable (str): The variable with respect to which the limit is
                computed.
            point (float): The point that the variable approaches.
            direction (str, optional): The direction from which the limit is
                approached. Options are `'both'`, `'+'` (right-hand limit),
                or `'-'` (left-hand limit). Defaults to `'both'`.

        Returns:
            str: JSON string containing the computed limit of the expression
                in the `"result"` field. If an error occurs, the JSON string
                will include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the limit computation
                process, such as invalid input, unsupported syntax, or
                issues with the variable, point, or direction.
        """
        try:
            self.logger.info(
                f"""Computing limit of expression: {expression} 
                as {variable} approaches {point} 
                from direction: {direction}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            limit = sp.limit(expr, var, point)
            return json.dumps({"result": str(limit)})
        except Exception as e:
            return self.handle_exception("compute_limit", e)

    def find_critical_points(self, expression: str, variable: str) -> str:
        r"""Finds the critical points of an expression by setting its
        derivative to zero.

        Args:
            expression (str): The mathematical expression for which critical
                points are to be found, provided as a string.
            variable (str): The variable with respect to which the critical
                points are determined.

        Returns:
            str: JSON string containing the critical points of the expression
                in the `"result"` field. The critical points are returned as a
                list of values corresponding to the variable. If an error
                occurs, the JSON string will include an `"error"` field with
                the corresponding error message.

        Raises:
            Exception: If there is an error during the critical point
                computation process, such as invalid input, unsupported
                syntax, or issues with the variable or the expression.
        """
        try:
            self.logger.info(
                f"""Finding critical points of expression: {expression} 
                with respect to {variable}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            derivative = sp.diff(expr, var)
            critical_points = sp.solve(derivative, var)
            return json.dumps(
                {"result": [str(point) for point in critical_points]}
            )
        except Exception as e:
            return self.handle_exception("find_critical_points", e)

    def check_continuity(
        self, expression: str, variable: str, point: float
    ) -> str:
        r"""Checks if an expression is continuous at a given point.

        Args:
            expression (str): The mathematical expression to check for
                continuity, provided as a string.
            variable (str): The variable with respect to which continuity
                is checked.
            point (float): The point at which the continuity of the expression
                is checked.

        Returns:
            str: JSON string containing the result of the continuity check in
                the `"result"` field. The result will be `"True"` if the
                expression is continuous at the given point, otherwise
                `"False"`. If an error occurs, the JSON string will include
                an `"error"` field with the corresponding error message.

        Raises:
            Exception: If there is an error during the continuity check
                process, such as invalid input, unsupported syntax, or
                issues with the variable or the point.
        """
        try:
            self.logger.info(
                f"""Checking continuity of expression: {expression} 
                at point {point}"""
            )
            var = sp.symbols(variable)
            expr = sp.sympify(expression)
            left_limit = sp.limit(expr, var, point, dir='-')
            right_limit = sp.limit(expr, var, point, dir='+')
            value_at_point = expr.subs(var, point)
            is_continuous = left_limit == right_limit == value_at_point
            return json.dumps({"result": str(is_continuous)})
        except Exception as e:
            return self.handle_exception("check_continuity", e)

    def compute_determinant(self, matrix: list) -> str:
        r"""Computes the determinant of a matrix.

        Args:
            matrix (list): A two-dimensional list representing the matrix for
                which the determinant is to be computed.

        Returns:
            str: JSON string containing the determinant of the matrix in the
                `"result"` field. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the determinant computation
                process, such as invalid input, unsupported syntax, or if the
                matrix is not square.
        """
        try:
            self.logger.info(f"Computing determinant of matrix: {matrix}")
            mat = sp.Matrix(matrix)
            determinant = mat.det()
            return json.dumps({"result": str(determinant)})
        except Exception as e:
            return self.handle_exception("compute_determinant", e)

    def compute_inverse(self, matrix: list) -> str:
        r"""Computes the inverse of a matrix.

        Args:
            matrix (list): A two-dimensional list representing the matrix for
                which the inverse is to be computed.

        Returns:
            str: JSON string containing the inverse of the matrix in the
                `"result"` field. The inverse is represented in a symbolic
                matrix format. If an error occurs, the JSON string will include
                an `"error"` field with the corresponding error message.

        Raises:
            Exception: If there is an error during the inverse computation
                process, such as invalid input, unsupported syntax, or if
                the matrix is not invertible (i.e., its determinant is zero).
        """
        try:
            self.logger.info(f"Computing inverse of matrix: {matrix}")
            mat = sp.Matrix(matrix)
            inverse = mat.inv()
            return json.dumps({"result": str(inverse)})
        except Exception as e:
            return self.handle_exception("compute_inverse", e)

    def compute_eigenvalues(self, matrix: list) -> str:
        r"""Computes the eigenvalues of a matrix.

        Args:
            matrix (list): A two-dimensional list representing the matrix for
                which the eigenvalues are to be computed.

        Returns:
            str: JSON string containing the eigenvalues of the matrix in the
                `"result"` field. The eigenvalues are represented as a
                dictionary where keys are the eigenvalues (as strings) and
                values are their multiplicities (as strings). If an error
                occurs, the JSON string will include an `"error"` field
                with the corresponding error message.

        Raises:
            Exception: If there is an error during the eigenvalue
                computation process, such as invalid input, unsupported
                syntax, or if the matrix is not square.
        """
        try:
            self.logger.info(f"Computing eigenvalues of matrix: {matrix}")
            mat = sp.Matrix(matrix)
            eigenvalues = mat.eigenvals()
            return json.dumps(
                {"result": {str(k): str(v) for k, v in eigenvalues.items()}}
            )
        except Exception as e:
            return self.handle_exception("compute_eigenvalues", e)

    def compute_eigenvectors(self, matrix: list) -> str:
        r"""Computes the eigenvectors of a matrix.

        Args:
            matrix (list): A two-dimensional list representing the matrix for
                which the eigenvectors are to be computed.

        Returns:
            str: JSON string containing the eigenvectors of the matrix in the
                `"result"` field. Each eigenvalue is represented as a
                dictionary with the following keys:
                - `"eigenvalue"`: The eigenvalue (as a string).
                - `"multiplicity"`: The multiplicity of the eigenvalue
                (as an integer).
                - `"eigenvectors"`: A list of eigenvectors
                (each represented as a string).

                If an error occurs, the JSON string will include an `"error"`
                field with the corresponding error message.

        Raises:
            Exception: If there is an error during the eigenvector
                computation process, such as invalid input, unsupported
                syntax, or if the matrix is not square.
        """
        try:
            self.logger.info(f"Computing eigenvectors of matrix: {matrix}")
            mat = sp.Matrix(matrix)
            eigenvectors = mat.eigenvects()
            result = [
                {
                    "eigenvalue": str(eigenvalue),
                    "multiplicity": multiplicity,
                    "eigenvectors": [str(v) for v in vectors],
                }
                for eigenvalue, multiplicity, vectors in eigenvectors
            ]
            return json.dumps({"result": result})
        except Exception as e:
            return self.handle_exception("compute_eigenvectors", e)

    def compute_nullspace(self, matrix: list) -> str:
        r"""Computes the null space of a matrix.

        Args:
            matrix (list): A two-dimensional list representing the matrix for
                which the null space is to be computed.

        Returns:
            str: JSON string containing the null space of the matrix in the
                `"result"` field. The null space is represented as a list of
                basis vectors, where each vector is given as a string in
                symbolic format. If an error occurs, the JSON string will
                include an `"error"` field with the corresponding error
                message.

        Raises:
            Exception: If there is an error during the null space computation
            process, such as invalid input, unsupported syntax, or if the
            matrix is malformed.
        """
        try:
            self.logger.info(f"Computing null space of matrix: {matrix}")
            mat = sp.Matrix(matrix)
            nullspace = mat.nullspace()
            return json.dumps({"result": [str(vec) for vec in nullspace]})
        except Exception as e:
            return self.handle_exception("compute_nullspace", e)

    def compute_rank(self, matrix: list) -> str:
        r"""Computes the rank of a matrix.

        Args:
            matrix (list): A two-dimensional list representing the matrix for
                which the rank is to be computed.

        Returns:
            str: JSON string containing the rank of the matrix in the
                `"result"` field. The rank is represented as an integer.
                If an error occurs,the JSON string will include an
                `"error"` field with the corresponding error message.

        Raises:
            Exception: If there is an error during the rank computation
                process, such as invalid input, unsupported
                syntax, or if the matrix is malformed.
        """
        try:
            self.logger.info(f"Computing rank of matrix: {matrix}")
            mat = sp.Matrix(matrix)
            rank = mat.rank()
            return json.dumps({"result": rank})
        except Exception as e:
            return self.handle_exception("compute_rank", e)

    def handle_exception(self, func_name: str, error: Exception) -> str:
        r"""Handles exceptions by logging and returning error details.

        Args:
            func_name (str): The name of the function where the
            exception occurred.
            error (Exception): The exception object containing
            details about the error.

        Returns:
            str: JSON string containing the error details.
                The JSON includes:
                - `"status"`: Always set to `"error"`.
                - `"message"`: A string representation of the
                exception message.

        Raises:
            None: This function does not raise exceptions. It is used to handle
                and report exceptions from other methods.
        """
        self.logger.error(f"Error in {func_name}: {error}")
        return json.dumps({"status": "error", "message": str(error)})

    def get_tools(self) -> List[FunctionTool]:
        r"""Exposes the tool's methods to the agent framework.

        Returns:
            List[FunctionTool]: A list of `FunctionTool` objects representing
                the toolkit's methods, making them accessible to the agent.
        """
        return [
            FunctionTool(self.simplify_expression),
            FunctionTool(self.expand_expression),
            FunctionTool(self.factor_expression),
            FunctionTool(self.solve_linear_system),
            FunctionTool(self.solve_nonlinear_system),
            FunctionTool(self.solve_univariate_inequality),
            FunctionTool(self.reduce_inequalities),
            FunctionTool(self.polynomial_representation),
            FunctionTool(self.polynomial_degree),
            FunctionTool(self.polynomial_coefficients),
            FunctionTool(self.solve_equation),
            FunctionTool(self.find_roots),
            FunctionTool(self.differentiate),
            FunctionTool(self.integrate),
            FunctionTool(self.definite_integral),
            FunctionTool(self.series_expansion),
            FunctionTool(self.compute_limit),
            FunctionTool(self.find_critical_points),
            FunctionTool(self.check_continuity),
            FunctionTool(self.compute_determinant),
            FunctionTool(self.compute_inverse),
            FunctionTool(self.compute_eigenvalues),
            FunctionTool(self.compute_eigenvectors),
            FunctionTool(self.compute_nullspace),
            FunctionTool(self.compute_rank),
        ]
