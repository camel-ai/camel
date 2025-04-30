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

import sympy as sp
from sympy.geometry import Line, Point  # type: ignore[import-untyped]
from sympy.printing import srepr

from camel.toolkits.sympy_toolkit import SymPyToolkit


class TestSymPyToolkit(unittest.TestCase):
    def setUp(self):
        self.toolkit = SymPyToolkit()

    def test_simplify_expression(self):
        response = self.toolkit.simplify_expression("(x**2 + 2*x + 1)/(x + 1)")
        result = json.loads(response)["result"]
        self.assertEqual(result, "Add(Symbol('x'), Integer(1))")

    def test_solve_equation(self):
        response = self.toolkit.solve_equation("x**2 - 4")
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["Integer(-2)", "Integer(2)"])

    def test_expand_expression(self):
        response = self.toolkit.expand_expression("(x + 2)*(x - 2)")
        result = json.loads(response)["result"]
        self.assertEqual(result, "Add(Pow(Symbol('x'), Integer(2)), Integer(-4))")

    def test_factor_expression(self):
        response = self.toolkit.factor_expression("x**2 - 4")
        result = json.loads(response)["result"]
        self.assertEqual(result, "Mul(Add(Symbol('x'), Integer(-2)), Add(Symbol('x'), Integer(2)))")

    def test_solve_linear_system(self):
        response = self.toolkit.solve_linear_system(
            ["2*x + y - 3", "x - y - 1"], ["x", "y"]
        )
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["Tuple(Rational(4, 3), Rational(1, 3))"])

    def test_polynomial_degree(self):
        response = self.toolkit.polynomial_degree("x**3 - 2*x + 1", "x")
        result = json.loads(response)["result"]
        self.assertEqual(result, 3)

    def test_polynomial_coefficients(self):
        response = self.toolkit.polynomial_coefficients("x**3 - 2*x + 1", "x")
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["Integer(1)", "Integer(0)", "Integer(-2)", "Integer(1)"])

    def test_differentiate(self):
        response = self.toolkit.differentiate("x**3")
        result = json.loads(response)["result"]
        self.assertEqual(result, "Mul(Integer(3), Pow(Symbol('x'), Integer(2)))")

    def test_integrate(self):
        response = self.toolkit.integrate("x**2")
        result = json.loads(response)["result"]
        self.assertEqual(result, "Mul(Rational(1, 3), Pow(Symbol('x'), Integer(3)))")

    def test_definite_integral(self):
        response = self.toolkit.definite_integral("x**2", "x", 0, 2)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Rational(8, 3)")

    def test_series_expansion(self):
        response = self.toolkit.series_expansion("sin(x)", "x", 0, 5)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Add(Symbol('x'), Mul(Integer(-1), Rational(1, 6), Pow(Symbol('x'), Integer(3))), Order(Pow(Symbol('x'), Integer(5)), Tuple(Symbol('x'), Integer(0))))")

    def test_compute_limit(self):
        response = self.toolkit.compute_limit("1/x", "x", 0)
        result = json.loads(response)["result"]
        self.assertEqual(result, "oo")

    def test_find_critical_points(self):
        response = self.toolkit.find_critical_points("x**3 - 3*x", "x")
        result = json.loads(response)["result"]
        self.assertListEqual(result, ["Integer(-1)", "Integer(1)"])

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
        self.assertEqual(result, "Integer(-2)")

    def test_compute_inverse(self):
        matrix = [[1, 2], [3, 4]]
        response = self.toolkit.compute_inverse(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, "MutableDenseMatrix([[Integer(-2), Integer(1)], [Rational(3, 2), Rational(-1, 2)]])")

    def test_compute_eigenvalues(self):
        matrix = [[5, 4], [2, 3]]
        response = self.toolkit.compute_eigenvalues(matrix)
        result = json.loads(response)["result"]
        expected = {"Integer(7)": 1, "Integer(1)": 1}
        self.assertDictEqual(result, expected)

    def test_compute_eigenvectors_exact_values(self):
        matrix = [[5, 4], [2, 3]]
        response = self.toolkit.compute_eigenvectors(matrix)
        result = json.loads(response)["result"]

        expected = [
            {
                "eigenvalue": "Integer(1)",
                "multiplicity": 1,
                "eigenvectors": ["MutableDenseMatrix([[Integer(-1)], [Integer(1)]])"],
            },
            {
                "eigenvalue": "Integer(7)",
                "multiplicity": 1,
                "eigenvectors": ["MutableDenseMatrix([[Integer(2)], [Integer(1)]])"],
            },
        ]

        self.assertEqual(result, expected)

    def test_compute_nullspace(self):
        matrix = [[1, 2], [2, 4]]
        response = self.toolkit.compute_nullspace(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, ["MutableDenseMatrix([[Integer(-2)], [Integer(1)]])"])  

    def test_compute_rank(self):
        matrix = [[1, 2], [3, 4]]
        response = self.toolkit.compute_rank(matrix)
        result = json.loads(response)["result"]
        self.assertEqual(result, 2)

    @unittest.skip("Method not implemented in toolkit")
    def test_create_point(self):
        response = self.toolkit.create_point(1, 2)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Point2D(Integer(1), Integer(2))")

    @unittest.skip("Method not implemented in toolkit")
    def test_create_line(self):
        response = self.toolkit.create_line([1, 2], [3, 4])
        result = json.loads(response)["result"]
        self.assertEqual(result, "Line2D(Point2D(Integer(1), Integer(2)), Point2D(Integer(3), Integer(4)))")

    @unittest.skip("Method not implemented in toolkit")
    def test_create_segment(self):
        response = self.toolkit.create_segment([1, 2], [3, 4])
        result = json.loads(response)["result"]
        self.assertEqual(result, "Segment2D(Point2D(Integer(1), Integer(2)), Point2D(Integer(3), Integer(4)))")

    @unittest.skip("Method not implemented in toolkit")
    def test_create_circle(self):
        response = self.toolkit.create_circle([1, 2], 5)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Circle(Point2D(Integer(1), Integer(2)), Integer(5))")

    @unittest.skip("Method not implemented in toolkit")
    def test_create_ellipse(self):
        response = self.toolkit.create_ellipse([1, 2], 5, 3)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Ellipse(Point2D(Integer(1), Integer(2)), Integer(5), Integer(3))")

    @unittest.skip("Method not implemented in toolkit")
    def test_create_polygon(self):
        response = self.toolkit.create_polygon(
            [[0, 0], [4, 0], [2, 3], [3, 5]]
        )
        result = json.loads(response)["result"]
        self.assertEqual(
            result,
            """
            "Polygon(Point2D(0, 0), Point2D(4, 0),
            Point2D(2, 3), Point2D(3, 5))",
            """,
        )

    @unittest.skip("Method not implemented in toolkit")
    def test_create_triangle(self):
        response = self.toolkit.create_triangle([0, 0], [4, 0], [2, 3])
        result = json.loads(response)["result"]
        self.assertEqual(
            result, "Triangle(Point2D(0, 0), Point2D(4, 0), Point2D(2, 3))"
        )

    @unittest.skip("Method not implemented in toolkit")
    def test_compute_line_bisectors(self):
        line1 = Line(Point(1, 2), Point(3, 4))
        line2 = Line(Point(5, 6), Point(7, 8))
        response = self.toolkit.compute_line_bisectors(line1, line2)
        result = json.loads(response)["result"]
        self.assertIsInstance(result, list)

    @unittest.skip("Method not implemented in toolkit")
    def test_compute_centroid(self):
        response = self.toolkit.compute_centroid(
            Point(0, 0), Point(4, 0), Point(2, 3)
        )
        result = json.loads(response)["result"]
        self.assertEqual(result, "Point2D(Integer(2), Integer(1))")

    @unittest.skip("Method not implemented in toolkit")
    def test_compute_orthocenter(self):
        response = self.toolkit.compute_orthocenter(
            Point(0, 0), Point(4, 0), Point(2, 3)
        )
        result = json.loads(response)["result"]
        self.assertIsInstance(result, str)

    @unittest.skip("Method not implemented in toolkit")
    def test_compute_midpoint_GH(self):
        G = Point(1, 2)
        H = Point(3, 4)
        response = self.toolkit.compute_midpoint_GH(G, H)
        result = json.loads(response)["result"]
        self.assertEqual(result, "Point2D(Integer(2), Integer(3))")

    @unittest.skip("Method not implemented in toolkit")
    def test_compute_point_distance(self):
        response = self.toolkit.compute_point_distance(
            Point(1, 2), Point(3, 4)
        )
        result = json.loads(response)["result"]
        self.assertEqual(result, "Mul(Integer(2), Pow(Integer(2), Rational(1, 2)))")

    @unittest.skip("Method not implemented in toolkit")
    def test_check_points_collinear(self):
        p1, p2, p3 = Point(0, 0), Point(1, 1), Point(2, 2)
        response = self.toolkit.check_points_collinear(p1, p2, p3)
        result = json.loads(response)["result"]
        self.assertEqual(result, True)

        p4 = Point(1, 2)
        response = self.toolkit.check_points_collinear(p1, p2, p4)
        result = json.loads(response)["result"]
        self.assertEqual(result, False)

    @unittest.skip("Method not implemented in toolkit")
    def test_compute_angle_between(self):
        line1 = Line(Point(1, 2), Point(3, 4))
        line2 = Line(Point(5, 6), Point(7, 8))
        response = self.toolkit.compute_angle_between(line1, line2)
        result = json.loads(response)["result"]
        self.assertIsInstance(result, str)


    def test_srepr_serialization(self):
        """Test that the toolkit is using srepr() instead of str() for serialization."""
        # Test with a simple expression
        expr = sp.symbols('x')**2 + 1
        expected_str = "x**2 + 1"  # str representation
        expected_srepr = srepr(expr)  # srepr representation
        
        # Verify they are different
        self.assertNotEqual(expected_str, expected_srepr)
        
        # Test with simplify_expression
        response = self.toolkit.simplify_expression("x**2 + 1")
        result = json.loads(response)["result"]
        
        # The result should match the srepr representation, not the str representation
        self.assertEqual(result, expected_srepr)
        self.assertNotEqual(result, expected_str)
        
        # Test with another function like expand_expression
        response = self.toolkit.expand_expression("(x+1)**2")
        result = json.loads(response)["result"]
        expanded_expr = sp.expand((sp.symbols('x')+1)**2)
        expected_expanded_srepr = srepr(expanded_expr)
        
        self.assertEqual(result, expected_expanded_srepr)
        self.assertNotEqual(result, str(expanded_expr))


if __name__ == "__main__":
    unittest.main()
