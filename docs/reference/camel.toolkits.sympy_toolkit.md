<a id="camel.toolkits.sympy_toolkit"></a>

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit"></a>

## SymPyToolkit

```python
class SymPyToolkit(BaseToolkit):
```

A toolkit for performing symbolic computations using SymPy.
This includes methods for Algebraic manipulation calculus
and Linear Algebra.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    default_variable: str = 'x',
    timeout: Optional[float] = None
):
```

Initializes the toolkit with a default variable and logging.

**Parameters:**

- **default_variable** (str): The default variable for operations (default: :obj:`x`)

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.simplify_expression"></a>

### simplify_expression

```python
def simplify_expression(self, expression: str):
```

Simplifies a mathematical expression.

**Parameters:**

- **expression** (str): The mathematical expression to simplify, provided as a string.

**Returns:**

  str: JSON string containing the simplified mathematical
expression in the `"result"` field. If an error occurs,
the `"status"` field will be set to `"error"` with a
corresponding `"message"`.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.expand_expression"></a>

### expand_expression

```python
def expand_expression(self, expression: str):
```

Expands an algebraic expression.

**Parameters:**

- **expression** (str): The algebraic expression to expand, provided as a string.

**Returns:**

  str: JSON string containing the expanded algebraic expression
in the `"result"` field. If an error occurs, the JSON
string will include an `"error"` field with the corresponding
error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.factor_expression"></a>

### factor_expression

```python
def factor_expression(self, expression: str):
```

Factors an algebraic expression.

**Parameters:**

- **expression** (str): The algebraic expression to factor, provided as a string.

**Returns:**

  str: JSON string containing the factored algebraic expression
in the `"result"` field. If an error occurs, the JSON string
will include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.solve_linear_system"></a>

### solve_linear_system

```python
def solve_linear_system(self, equations: List[str], variables: List[str]):
```

Solves a system of linear equations.

**Parameters:**

- **equations** (List[str]): A list of strings representing the linear equations to be solved.
- **variables** (List[str]): A list of strings representing the variables involved in the equations.

**Returns:**

  str: JSON string containing the solution to the system of equations
in the `"result"` field. Each solution is represented as
a tuple of values corresponding to the variables. If an
error occurs, the JSON string will include an `"error"`
field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.solve_nonlinear_system"></a>

### solve_nonlinear_system

```python
def solve_nonlinear_system(self, sympy_equations: List[str], variables: List[str]):
```

Solves a system of nonlinear equations.

**Parameters:**

- **sympy_equations** (List[str]): A list of strings representing the nonlinear equations to be solved. The equation to solve, must be compatible with SymPy, provided as a string.
- **variables** (List[str]): A list of strings representing the variables involved in the equations.

**Returns:**

  str: JSON string containing the solutions to the system of
equations in the `"result"` field. Each solution is
represented as a tuple of values corresponding to the
variables. If an error occurs, the JSON string will
include an `"error"` field with the corresponding
error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.solve_univariate_inequality"></a>

### solve_univariate_inequality

```python
def solve_univariate_inequality(self, inequality: str, variable: str):
```

Solves a single-variable inequality.

**Parameters:**

- **inequality** (str): A string representing the inequality to be solved.
- **variable** (str): The variable in the inequality.

**Returns:**

  str: JSON string containing the solution to the inequality in the
`"result"` field. The solution is represented in a symbolic
format (e.g., intervals or expressions). If an error occurs,
the JSON string will include an `"error"` field with the
corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.reduce_inequalities"></a>

### reduce_inequalities

```python
def reduce_inequalities(self, inequalities: List[str]):
```

Reduces a system of inequalities.

**Parameters:**

- **inequalities** (List[str]): A list of strings representing the inequalities to be reduced.

**Returns:**

  str: JSON string containing the reduced system of inequalities
in the `"result"` field. The solution is represented in
a symbolic format (e.g., combined intervals or expressions).
If an error occurs, the JSON string will include an `"error"`
field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.polynomial_representation"></a>

### polynomial_representation

```python
def polynomial_representation(self, expression: str, variable: str):
```

Represents an expression as a polynomial.

**Parameters:**

- **expression** (str): The mathematical expression to represent as a polynomial, provided as a string.
- **variable** (str): The variable with respect to which the polynomial representation will be created.

**Returns:**

  str: JSON string containing the polynomial representation of the
expression in the `"result"` field. The polynomial is returned
in a symbolic format. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.polynomial_degree"></a>

### polynomial_degree

```python
def polynomial_degree(self, expression: str, variable: str):
```

Returns the degree of a polynomial.

**Parameters:**

- **expression** (str): The polynomial expression for which the degree is to be determined, provided as a string.
- **variable** (str): The variable with respect to which the degree of the polynomial is calculated.

**Returns:**

  str: JSON string containing the degree of the polynomial in the
`"result"` field. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.polynomial_coefficients"></a>

### polynomial_coefficients

```python
def polynomial_coefficients(self, expression: str, variable: str):
```

Returns the coefficients of a polynomial.

**Parameters:**

- **expression** (str): The polynomial expression from which the coefficients are to be extracted, provided as a string.
- **variable** (str): The variable with respect to which the polynomial coefficients are determined.

**Returns:**

  str: JSON string containing the list of coefficients of the
polynomial in the `"result"` field. The coefficients are
ordered from the highest degree term to the constant term.
If an error occurs, the JSON string will include an `"error"
field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.solve_equation"></a>

### solve_equation

```python
def solve_equation(self, sympy_equation: str, variable: Optional[str] = None):
```

Solves an equation for a specific variable.

**Parameters:**

- **sympy_equation** (str): The equation to solve, must be compatible with SymPy, provided as a string.
- **variable** (str, optional): The variable to solve for. If not specified, the function will use the default variable.

**Returns:**

  str: JSON string containing the solutions to the equation in the
`"result"` field. Each solution is represented as a string.
If an error occurs, the JSON string will include an `"error"`
field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.find_roots"></a>

### find_roots

```python
def find_roots(self, expression: str):
```

Finds the roots of a polynomial or algebraic equation.

**Parameters:**

- **expression** (str): The polynomial or algebraic equation for which the roots are to be found, provided as a string.

**Returns:**

  str: JSON string containing the roots of the expression in the
`"result"` field. The roots are represented as a list of
solutions. If an error occurs, the JSON string will include
a `"status"` field set to `"error"` and a `"message"` field
with the corresponding error description.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.differentiate"></a>

### differentiate

```python
def differentiate(self, expression: str, variable: Optional[str] = None):
```

Differentiates an expression with respect to a variable.

**Parameters:**

- **expression** (str): The mathematical expression to differentiate, provided as a string.
- **variable** (str, optional): The variable with respect to which the differentiation is performed. If not specified, the default variable is used.

**Returns:**

  str: JSON string containing the derivative of the expression in the
`"result"` field. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.integrate"></a>

### integrate

```python
def integrate(self, expression: str, variable: Optional[str] = None):
```

Integrates an expression with respect to a variable.

**Parameters:**

- **expression** (str): The mathematical expression to integrate, provided as a string.
- **variable** (str, optional): The variable with respect to which the integration is performed. If not specified, the default variable is used.

**Returns:**

  str: JSON string containing the integral of the expression in the
`"result"` field. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.definite_integral"></a>

### definite_integral

```python
def definite_integral(
    self,
    expression: str,
    variable: str,
    lower: float,
    upper: float
):
```

Computes the definite integral of an expression within given
bounds.

**Parameters:**

- **expression** (str): The mathematical expression to integrate, provided as a string.
- **variable** (str): The variable with respect to which the definite integration is performed.
- **lower** (float): The lower limit of the integration.
- **upper** (float): The upper limit of the integration.

**Returns:**

  str: JSON string containing the result of the definite integral
in the `"result"` field. If an error occurs, the JSON string
will include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.series_expansion"></a>

### series_expansion

```python
def series_expansion(
    self,
    expression: str,
    variable: str,
    point: float,
    order: int
):
```

Expands an expression into a Taylor series around a given point up
to a specified order.

**Parameters:**

- **expression** (str): The mathematical expression to expand, provided as a string.
- **variable** (str): The variable with respect to which the series expansion is performed.
- **point** (float): The point around which the Taylor series is expanded.
- **order** (int): The order up to which the series expansion is computed.

**Returns:**

  str: JSON string containing the Taylor series expansion of the
expression in the `"result"` field. If an error occurs,
the JSON string will include an `"error"` field with the
corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_limit"></a>

### compute_limit

```python
def compute_limit(
    self,
    expression: str,
    variable: str,
    point: float
):
```

Computes the limit of an expression as a variable approaches
a point.

**Parameters:**

- **expression** (str): The mathematical expression for which the limit is to be computed, provided as a string.
- **variable** (str): The variable with respect to which the limit is computed.
- **point** (float): The point that the variable approaches.

**Returns:**

  str: JSON string containing the computed limit of the expression
in the `"result"` field. If an error occurs, the JSON string
will include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.find_critical_points"></a>

### find_critical_points

```python
def find_critical_points(self, expression: str, variable: str):
```

Finds the critical points of an expression by setting its
derivative to zero.

**Parameters:**

- **expression** (str): The mathematical expression for which critical points are to be found, provided as a string.
- **variable** (str): The variable with respect to which the critical points are determined.

**Returns:**

  str: JSON string containing the critical points of the expression
in the `"result"` field. The critical points are returned as a
list of values corresponding to the variable. If an error
occurs, the JSON string will include an `"error"` field with
the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.check_continuity"></a>

### check_continuity

```python
def check_continuity(
    self,
    expression: str,
    variable: str,
    point: float
):
```

Checks if an expression is continuous at a given point.

**Parameters:**

- **expression** (str): The mathematical expression to check for continuity, provided as a string.
- **variable** (str): The variable with respect to which continuity is checked.
- **point** (float): The point at which the continuity of the expression is checked.

**Returns:**

  str: JSON string containing the result of the continuity check in
the `"result"` field. The result will be `"True"` if the
expression is continuous at the given point, otherwise
`"False"`. If an error occurs, the JSON string will include
an `"error"` field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_determinant"></a>

### compute_determinant

```python
def compute_determinant(self, matrix: List[List[float]]):
```

Computes the determinant of a matrix.

**Parameters:**

- **matrix** (List[List[float]]): A two-dimensional list representing the matrix for which the determinant is to be computed.

**Returns:**

  str: JSON string containing the determinant of the matrix in the
`"result"` field. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_inverse"></a>

### compute_inverse

```python
def compute_inverse(self, matrix: List[List[float]]):
```

Computes the inverse of a matrix.

**Parameters:**

- **matrix** (List[List[float]]): A two-dimensional list representing the matrix for which the inverse is to be computed.

**Returns:**

  str: JSON string containing the inverse of the matrix in the
`"result"` field. The inverse is represented in a symbolic
matrix format. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_eigenvalues"></a>

### compute_eigenvalues

```python
def compute_eigenvalues(self, matrix: List[List[float]]):
```

Computes the eigenvalues of a matrix.

**Parameters:**

- **matrix** (List[List[float]]): A two-dimensional list representing the matrix for which the eigenvalues are to be computed.

**Returns:**

  str: JSON string containing the eigenvalues of the matrix in the
`"result"` field. The eigenvalues are represented as a
dictionary where keys are the eigenvalues (as strings) and
values are their multiplicities (as strings). If an error
occurs, the JSON string will include an `"error"` field
with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_eigenvectors"></a>

### compute_eigenvectors

```python
def compute_eigenvectors(self, matrix: List[List[float]]):
```

Computes the eigenvectors of a matrix.

**Parameters:**

- **matrix** (List[List[float]]): A two-dimensional list representing the matrix for which the eigenvectors are to be computed.

**Returns:**

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

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_nullspace"></a>

### compute_nullspace

```python
def compute_nullspace(self, matrix: List[List[float]]):
```

Computes the null space of a matrix.

**Parameters:**

- **matrix** (List[List[float]]): A two-dimensional list representing the matrix for which the null space is to be computed.

**Returns:**

  str: JSON string containing the null space of the matrix in the
`"result"` field. The null space is represented as a list of
basis vectors, where each vector is given as a string in
symbolic format. If an error occurs, the JSON string will
include an `"error"` field with the corresponding error
message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_rank"></a>

### compute_rank

```python
def compute_rank(self, matrix: List[List[float]]):
```

Computes the rank of a matrix.

**Parameters:**

- **matrix** (List[List[float]]): A two-dimensional list representing the matrix for which the rank is to be computed.

**Returns:**

  str: JSON string containing the rank of the matrix in the
`"result"` field. The rank is represented as an integer.
If an error occurs,the JSON string will include an
`"error"` field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.compute_inner_product"></a>

### compute_inner_product

```python
def compute_inner_product(self, vector1: List[float], vector2: List[float]):
```

Computes the inner (dot) product of two vectors.

**Parameters:**

- **vector1** (List[float]): The first vector as a list of floats.
- **vector2** (List[float]): The second vector as a list of floats.

**Returns:**

  str: JSON string containing the inner product in the `"result"`
field. If an error occurs, the JSON string will include an
`"error"` field with the corresponding error message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.handle_exception"></a>

### handle_exception

```python
def handle_exception(self, func_name: str, error: Exception):
```

Handles exceptions by logging and returning error details.

**Parameters:**

- **func_name** (str): The name of the function where the exception occurred.
- **error** (Exception): The exception object containing details about the error.

**Returns:**

  str: JSON string containing the error details.
The JSON includes:
- `"status"`: Always set to `"error"`.
- `"message"`: A string representation of the
exception message.

<a id="camel.toolkits.sympy_toolkit.SymPyToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of `FunctionTool` objects representing
the toolkit's methods, making them accessible to the agent.
