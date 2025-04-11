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
import unittest

from camel.toolkits.sympy_toolkit import SymPyToolkit


class TestSymPyToolkit(unittest.TestCase):
    def setUp(self):
        self.toolkit = SymPyToolkit()

    def test_simplify_expression(self):
        response = self.toolkit.simplify_expression("(x**2 + 2*x + 1)/(x + 1)")
        result = json.loads(response)["result"]
        self.assertEqual(result, "x + 1")

    def test_solve_equation(self):
        response = self.toolkit.solve_equation("x**2 - 4")
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["-2", "2"])

    def test_expand_expression(self):
        response = self.toolkit.expand_expression("(x + 2)*(x - 2)")
        result = json.loads(response)["result"]
        self.assertEqual(result, "x**2 - 4")

    def test_factor_expression(self):
        response = self.toolkit.factor_expression("x**2 - 4")
        result = json.loads(response)["result"]
        self.assertEqual(result, "(x - 2)*(x + 2)")

    def test_solve_linear_system(self):
        response = self.toolkit.solve_linear_system(
            ["2*x + y - 3", "x - y - 1"], ["x", "y"]
        )
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["(4/3, 1/3)"])

    def test_polynomial_degree(self):
        response = self.toolkit.polynomial_degree("x**3 - 2*x + 1", "x")
        result = json.loads(response)["result"]
        self.assertEqual(result, 3)

    def test_polynomial_coefficients(self):
        response = self.toolkit.polynomial_coefficients("x**3 - 2*x + 1", "x")
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["1", "0", "-2", "1"])

    def test_differentiate(self):
        response = self.toolkit.differentiate("x**3")
        result = json.loads(response)["result"]
        self.assertEqual(result, "3*x**2")

    def test_integrate(self):
        response = self.toolkit.integrate("x**2")
        result = json.loads(response)["result"]
        self.assertEqual(result, "x**3/3")

    def test_definite_integral(self):
        response = self.toolkit.definite_integral("x**2", "x", 0, 2)
        result = json.loads(response)["result"]
        self.assertEqual(result, "8/3")

    def test_series_expansion(self):
        response = self.toolkit.series_expansion("sin(x)", "x", 0, 5)
        result = json.loads(response)["result"]
        self.assertEqual(result, "x - x**3/6 + O(x**5)")

    def test_compute_limit(self):
        response = self.toolkit.compute_limit("1/x", "x", 0)
        result = json.loads(response)["result"]
        self.assertEqual(result, "oo")

    def test_find_critical_points(self):
        response = self.toolkit.find_critical_points("x**3 - 3*x", "x")
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["-1", "1"])

    def test_check_continuity_continuous(self):
        response = self.toolkit.check_continuity("x**2", "x", 2)
        result = json.loads(response)["result"]
        self.assertEqual(result, "True")

    def test_check_continuity_discontinuous(self):
        response = self.toolkit.check_continuity("1/(x - 1)", "x", 1)
        result = json.loads(response)["result"]
        self.assertEqual(result, "False")

    def test_compute_determinant(self):
        matrix = [[1, 2], [3, 4]]
        response = self.toolkit.compute_determinant(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, "-2")

    def test_compute_inverse(self):
        matrix = [[1, 2], [3, 4]]
        response = self.toolkit.compute_inverse(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Matrix([[-2, 1], [3/2, -1/2]])")

    def test_compute_eigenvalues(self):
        matrix = [[5, 4], [2, 3]]
        response = self.toolkit.compute_eigenvalues(matrix)
        result = json.loads(response)["result"]
        expected = {"7": "1", "1": "1"}
        self.assertDictEqual(result, expected)

    def test_compute_eigenvectors_exact_values(self):
        matrix = [[5, 4], [2, 3]]
        response = self.toolkit.compute_eigenvectors(matrix)
        result = json.loads(response)["result"]

        expected = [
            {
                "eigenvalue": "1",
                "multiplicity": 1,
                "eigenvectors": ["Matrix([[-1], [1]])"],
            },
            {
                "eigenvalue": "7",
                "multiplicity": 1,
                "eigenvectors": ["Matrix([[2], [1]])"],
            },
        ]

        self.assertEqual(result, expected)

    def test_compute_nullspace(self):
        matrix = [[1, 2], [2, 4]]
        response = self.toolkit.compute_nullspace(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, ["Matrix([[-2], [1]])"])

    def test_compute_rank(self):
        matrix = [[1, 2], [3, 4]]
        response = self.toolkit.compute_rank(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
