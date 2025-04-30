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
from typing import List

import sympy as sp  # type: ignore[import]

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class EnhancedGeometryToolkit(BaseToolkit):
    r"""An enhanced toolkit for performing geometric computations using SymPy.

    This toolkit provides functions for working with basic geometric objects
    (points, lines, triangles, polygons) as well as conic sections (circles,
    ellipses, parabolas, hyperbolas). It is designed to solve problems from
    the conic10k dataset and other geometric challenges.
    """

    def __init__(self, log_level=logging.INFO, timeout: int = 180):
        r"""
        Initializes the toolkit with logging.

        Args:
            log_level (int): The logging level (default: logging.INFO).
            timeout (int): Maximum execution time in seconds (default: 180).
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.timeout = timeout
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def handle_exception(
        self, function_name: str, exception: Exception
    ) -> str:
        r"""Handles exceptions in a consistent way across the toolkit.

        Args:
            function_name (str): Name of the function where exception occurred
            exception (Exception): The exception that was raised

        Returns:
            str: JSON string with error information
        """
        self.logger.error(f"Error in {function_name}: {exception!s}")
        return json.dumps({"status": "error", "message": str(exception)})

    # ====================== CORE GEOMETRIC FUNCTIONS ======================

    def compute_distance_point_to_line(
        self,
        point_x: float,
        point_y: float,
        line_point1_x: float,
        line_point1_y: float,
        line_point2_x: float,
        line_point2_y: float,
    ) -> str:
        """Computes the shortest distance from a point to a line.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            line_point1_x: x-coordinate of the first point on the line
            line_point1_y: y-coordinate of the first point on the line
            line_point2_x: x-coordinate of the second point on the line
            line_point2_y: y-coordinate of the second point on the line

        Returns:
            str: JSON string with the computed distance
        """
        try:
            # Convert to float to ensure precision
            px, py = float(point_x), float(point_y)
            x1, y1 = float(line_point1_x), float(line_point1_y)
            x2, y2 = float(line_point2_x), float(line_point2_y)

            # Check if the two points defining the line are the same
            if x1 == x2 and y1 == y2:
                # Calculate distance to a point
                distance = sp.sqrt((px - x1) ** 2 + (py - y1) ** 2)
                return json.dumps({"result": str(float(distance))})

            # Calculate the distance using the formula:
            # d = |Ax + By + C| / sqrt(A^2 + B^2)
            # where Ax + By + C = 0 is the line equation

            # Convert to the form Ax + By + C = 0
            A = y2 - y1
            B = x1 - x2
            C = x2 * y1 - x1 * y2

            # Calculate distance
            numerator = abs(A * px + B * py + C)
            denominator = sp.sqrt(A**2 + B**2)
            distance = numerator / denominator

            return json.dumps({"result": str(float(distance))})
        except Exception as e:
            return self.handle_exception("compute_distance_point_to_line", e)

    def compute_distance(
        self,
        object1: List[float],
        object2: List[float],
        object_type1: str = "point",
        object_type2: str = "point",
    ) -> str:
        r"""Unified distance function that computes distances between various
            geometric objects.

        Args:
            object1: First object (format depends on object_type1)
                - "point": List[float] with [x, y] coordinates
                - "line": List[List[float]] with [[x1, y1], [x2, y2]] defining
                   two points
            object2: Second object (format depends on object_type2)
            object_type1: Type of first object ("point", "line")
            object_type2: Type of second object ("point", "line")

        Returns:
            str: JSON string with the computed distance in the "result" field
        """
        try:
            self.logger.info(
                f"Computing distance between {object_type1} and {object_type2}"
            )

            # Point to point distance
            if object_type1 == "point" and object_type2 == "point":
                p1 = sp.Point(float(object1[0]), float(object1[1]))
                p2 = sp.Point(float(object2[0]), float(object2[1]))
                distance = p1.distance(p2)

            # Point to line distance
            elif object_type1 == "point" and object_type2 == "line":
                p = sp.Point(float(object1[0]), float(object1[1]))
                # Extract coordinates from the line endpoints
                if not isinstance(object2, (list, tuple)) or len(object2) != 2:
                    raise ValueError("Line must be defined by two points")
                line_start, line_end = object2
                if not isinstance(line_start, (list, tuple)) or not isinstance(
                    line_end, (list, tuple)
                ):
                    raise ValueError("Line endpoints must be coordinate pairs")
                p1 = sp.Point(float(line_start[0]), float(line_start[1]))
                p2 = sp.Point(float(line_end[0]), float(line_end[1]))

                # Check if the two points defining the line are the same
                if p1 == p2:
                    distance = p.distance(p1)
                else:
                    line = sp.Line(p1, p2)
                    distance = line.distance(p)

            # Line to point distance (same as point to line)
            elif object_type1 == "line" and object_type2 == "point":
                return self.compute_distance(object2, object1, "point", "line")

            else:
                raise ValueError(
                    f"Unsupported obj types:{object_type1} and {object_type2}"
                )

            return json.dumps({"result": str(distance)})
        except Exception as e:
            return self.handle_exception("compute_distance", e)

    def compute_vector_operations(
        self, vectors: List[List[float]], operation: str = "dot_product"
    ) -> str:
        r"""Unified vector operations function.

        Args:
            vectors: List of vectors to operate on
                - For dot_product: Two vectors [vector1, vector2]
                - For angle: Four points defining two lines
                            [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            operation: Operation to perform ("dot_product", "angle",
                       "cross_product", "projection")

        Returns:
            str: JSON string with the operation result in the "result" field
        """
        try:
            self.logger.info(f"Computing vector operation: {operation}")

            if operation == "dot_product":
                if len(vectors) != 2:
                    raise ValueError(
                        "Dot product requires exactly two vectors"
                    )

                vector1, vector2 = vectors
                v1 = sp.Matrix([float(x) for x in vector1])
                v2 = sp.Matrix([float(x) for x in vector2])

                if v1.shape != v2.shape:
                    raise ValueError(
                        "Vectors must have the same dimensions"
                        "to compute the inner product."
                    )

                result = v1.dot(v2)

            elif operation == "angle":
                if len(vectors) != 4:
                    raise ValueError(
                        "Angle calculation requires four points"
                        "defining two lines"
                    )

                p1 = sp.Point(float(vectors[0][0]), float(vectors[0][1]))
                p2 = sp.Point(float(vectors[1][0]), float(vectors[1][1]))
                p3 = sp.Point(float(vectors[2][0]), float(vectors[2][1]))
                p4 = sp.Point(float(vectors[3][0]), float(vectors[3][1]))

                l1 = sp.Line(p1, p2)
                l2 = sp.Line(p3, p4)
                result = l1.angle_between(l2)

            elif operation == "cross_product":
                if (
                    len(vectors) != 2
                    or len(vectors[0]) != 3
                    or len(vectors[1]) != 3
                ):
                    raise ValueError(
                        "Cross product requires exactly two 3D vectors"
                    )

                vector1, vector2 = vectors
                v1 = sp.Matrix([float(x) for x in vector1])
                v2 = sp.Matrix([float(x) for x in vector2])
                result = v1.cross(v2)
                result = [float(result[0]), float(result[1]), float(result[2])]

            elif operation == "projection":
                if len(vectors) != 2:
                    raise ValueError("Projection requires exactly two vectors")

                vector1, vector2 = vectors
                v1 = sp.Matrix([float(x) for x in vector1])
                v2 = sp.Matrix([float(x) for x in vector2])

                # Project v1 onto v2
                dot_product = v1.dot(v2)
                v2_magnitude_squared = v2.dot(v2)

                if v2_magnitude_squared == 0:
                    raise ValueError("Cannot project onto a zero vector")

                scalar = dot_product / v2_magnitude_squared
                projection = scalar * v2
                result = [float(projection[i]) for i in range(len(projection))]

            else:
                raise ValueError(f"Unsupported operation: {operation}")

            return json.dumps({"result": str(result)})
        except Exception as e:
            return self.handle_exception("compute_vector_operations", e)

    def compute_area_triangle_vertices(
        self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float
    ) -> str:
        r"""Computes the area of a triangle given its vertices.

        Args:
            x1: x-coordinate of the first vertex
            y1: y-coordinate of the first vertex
            x2: x-coordinate of the second vertex
            y2: y-coordinate of the second vertex
            x3: x-coordinate of the third vertex
            y3: y-coordinate of the third vertex

        Returns:
            str: JSON string with the computed area
        """
        try:
            # Convert to float to ensure precision
            x1, y1 = float(x1), float(y1)
            x2, y2 = float(x2), float(y2)
            x3, y3 = float(x3), float(y3)

            # Calculate area using the Shoelace formula
            area = 0.5 * abs(
                (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
            )

            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_area_triangle_vertices", e)

    def compute_area_triangle_sides(
        self, side1: float, side2: float, side3: float
    ) -> str:
        r"""Computes the area of a triangle given its side lengths.

        Args:
            side1: Length of the first side
            side2: Length of the second side
            side3: Length of the third side

        Returns:
            str: JSON string with the computed area
        """
        try:
            # Convert to float to ensure precision
            a, b, c = float(side1), float(side2), float(side3)

            # Check if the sides can form a triangle
            if a + b <= c or a + c <= b or b + c <= a:
                return json.dumps(
                    {
                        "status": "error",
                        "message": (
                            "The given side lengths cannot form a triangle. "
                            "The sum of the lengths of any two sides must be "
                            "greater than the length of the third side."
                        ),
                    }
                )

            # Calculate semi-perimeter
            s = (a + b + c) / 2

            # Calculate area using Heron's formula
            area = sp.sqrt(s * (s - a) * (s - b) * (s - c))

            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_area_triangle_sides", e)

    def compute_area_polygon(self, vertices: List[List[float]]) -> str:
        r"""Computes the area of a polygon given its vertices.

        Args:
            vertices: List of [x, y] coordinates of the polygon vertices
                in order

        Returns:
            str: JSON string with the computed area
        """
        try:
            # Check if we have at least 3 vertices
            if len(vertices) < 3:
                return json.dumps(
                    {
                        "status": "error",
                        "message": "A polygon must have at least 3 vertices.",
                    }
                )

            # Extract x and y coordinates
            x_coords = [float(vertex[0]) for vertex in vertices]
            y_coords = [float(vertex[1]) for vertex in vertices]

            # Ensure the polygon is closed (last point = first point)
            if x_coords[0] != x_coords[-1] or y_coords[0] != y_coords[-1]:
                x_coords.append(x_coords[0])
                y_coords.append(y_coords[0])

            # Calculate area using the Shoelace formula (Gauss's area formula)
            n = len(x_coords)
            area = 0.0

            for i in range(n - 1):
                area += (
                    x_coords[i] * y_coords[i + 1]
                    - x_coords[i + 1] * y_coords[i]
                )

            area = abs(area) / 2.0

            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_area_polygon", e)

    def compute_midpoint(
        self, point1: List[float], point2: List[float]
    ) -> str:
        r"""Computes the midpoint between two points.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the midpoint.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            midpoint = p1.midpoint(p2)
            return json.dumps({"result": str(midpoint)})
        except Exception as e:
            return self.handle_exception("compute_midpoint", e)

    def compute_line_bisector(
        self, point1: List[float], point2: List[float]
    ) -> str:
        r"""Computes the perpendicular bisector of a line segment.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the perpendicular bisector.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            line_segment = sp.Segment(p1, p2)
            bisector = line_segment.perpendicular_bisector()
            return json.dumps({"result": str(bisector)})
        except Exception as e:
            return self.handle_exception("compute_line_bisector", e)

    def check_points_collinear(self, points: List[List[float]]) -> str:
        r"""Checks if a set of points are collinear.

        Args:
            points (List[List[float]]): List of [x, y] coordinates
            for each point.

        Returns:
            str: A JSON string with the "result" field containing True if
                the points are collinear, False otherwise.
        """
        try:
            pts = [
                sp.Point(float(point[0]), float(point[1])) for point in points
            ]
            collinear = sp.Point.is_collinear(*pts)
            return json.dumps({"result": str(collinear)})
        except Exception as e:
            return self.handle_exception("check_points_collinear", e)

    # ====================== CONIC SECTION HELPERS ======================

    def identify_conic_section_type(self, equation: str) -> str:
        r"""Identifies the type of conic section from its equation.

        Args:
            equation: The equation of the conic section
                (e.g., "x^2 + y^2 = 25" or "x^2/9 + y^2/4 = 1")

        Returns:
            str: JSON string with the identified conic section type
                 and properties
        """
        try:
            # Clean up the equation
            eq = equation.replace(" ", "").replace("^", "**").lower()

            # Parse the equation using sympy
            lhs, rhs = eq.split("=")
            expr = sp.sympify(lhs) - sp.sympify(rhs)

            # Convert to standard form Ax^2 + Bxy + Cy^2 + Dx + Ey + F = 0
            expr = sp.expand(expr)

            # Extract coefficients
            x, y = sp.symbols('x y')
            coeffs = {
                'A': expr.coeff(x, 2),
                'B': expr.coeff(x * y),
                'C': expr.coeff(y, 2),
                'D': expr.coeff(x, 1),
                'E': expr.coeff(y, 1),
                'F': expr.subs({x: 0, y: 0}),
            }

            # Determine the type of conic section
            discriminant = coeffs['B'] ** 2 - 4 * coeffs['A'] * coeffs['C']

            if abs(discriminant) < 1e-10:  # Discriminant ≈ 0
                if coeffs['A'] == coeffs['C'] and coeffs['A'] != 0:
                    if coeffs['F'] == 0:
                        conic_type = "degenerate (point)"
                    else:
                        conic_type = "circle"
                else:
                    conic_type = "parabola"
            elif discriminant < 0:
                if abs(coeffs['A'] - coeffs['C']) < 1e-10:
                    conic_type = "circle"
                else:
                    conic_type = "ellipse"
            else:  # discriminant > 0
                conic_type = "hyperbola"

            # Check for degenerate cases
            if (
                abs(coeffs['A']) < 1e-10
                and abs(coeffs['B']) < 1e-10
                and abs(coeffs['C']) < 1e-10
            ):
                if abs(coeffs['D']) < 1e-10 and abs(coeffs['E']) < 1e-10:
                    if abs(coeffs['F']) < 1e-10:
                        conic_type = "degenerate (all points)"
                    else:
                        conic_type = "degenerate (no points)"
                else:
                    conic_type = "degenerate (line)"

            return json.dumps(
                {
                    "result": {
                        "equation": equation,
                        "conic_type": conic_type,
                        "coefficients": {
                            k: float(v) if not v.is_integer else int(v)
                            for k, v in coeffs.items()
                        },
                        "discriminant": float(discriminant),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("identify_conic_section_type", e)

    def parse_circle_equation(self, equation: str) -> str:
        r"""Parses a circle equation and extracts its properties.

        Args:
            equation: The equation of the circle
                    (e.g., "x^2 + y^2 = 25" or "(x-3)^2 + (y+2)^2 = 16")

        Returns:
            str: JSON string with the circle properties
        """
        try:
            # Clean up the equation
            eq = equation.replace(" ", "").replace("^", "**").lower()

            # Parse the equation using sympy
            lhs, rhs = eq.split("=")
            expr = sp.sympify(lhs) - sp.sympify(rhs)

            # Convert to standard form x^2 + y^2 + Dx + Ey + F = 0
            expr = sp.expand(expr)

            # Extract coefficients
            x, y = sp.symbols('x y')
            coeffs = {
                'A': expr.coeff(x, 2),
                'B': expr.coeff(y, 2),
                'D': expr.coeff(x, 1),
                'E': expr.coeff(y, 1),
                'F': expr.subs({x: 0, y: 0}),
            }

            # Check if it's a circle (A = B = 1)
            if abs(coeffs['A'] - 1) > 1e-10 or abs(coeffs['B'] - 1) > 1e-10:
                return json.dumps(
                    {
                        "result": {
                            "error": "Not a circle in standard form",
                            "equation": equation,
                        }
                    }
                )

            # Calculate center and radius
            h = -coeffs['D'] / 2
            k = -coeffs['E'] / 2
            r_squared = h**2 + k**2 - coeffs['F']

            if r_squared < 0:
                return json.dumps(
                    {
                        "result": {
                            "error": "equation represents an imaginary circle",
                            "equation": equation,
                            "center": [float(h), float(k)],
                            "radius_squared": float(r_squared),
                        }
                    }
                )

            radius = sp.sqrt(r_squared)

            # Standard form: (x - h)^2 + (y - k)^2 = r^2
            standard_form = (
                f"(x - {float(h)})² + (y - {float(k)})² = {float(radius)}²"
            )

            return json.dumps(
                {
                    "result": {
                        "equation": equation,
                        "standard_form": standard_form,
                        "center": [float(h), float(k)],
                        "radius": float(radius),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("parse_circle_equation", e)

    def parse_ellipse_equation(self, equation: str) -> str:
        r"""Parses an ellipse equation and extracts its properties.

        Args:
            equation: The equation of the ellipse
                    (e.g., "x^2/9 + y^2/4 = 1" or "(x-2)^2/25+(y+3)^2/16 = 1")

        Returns:
            str: JSON string with the ellipse properties
        """
        try:
            # Clean up the equation
            eq = equation.replace(" ", "").replace("^", "**").lower()

            # Parse the equation using sympy
            lhs, rhs = eq.split("=")
            expr = sp.sympify(lhs) - sp.sympify(rhs)

            # Convert to standard form Ax^2 + Cy^2 + Dx + Ey + F = 0
            expr = sp.expand(expr)

            # Extract coefficients
            x, y = sp.symbols('x y')
            coeffs = {
                'A': expr.coeff(x, 2),
                'C': expr.coeff(y, 2),
                'D': expr.coeff(x, 1),
                'E': expr.coeff(y, 1),
                'F': expr.subs({x: 0, y: 0}),
            }

            # Check if it's an ellipse (A and C have the same sign)
            if coeffs['A'] * coeffs['C'] <= 0:
                return json.dumps(
                    {
                        "result": {
                            "error": "equation does not represent an ellipse",
                            "equation": equation,
                        }
                    }
                )

            # Calculate center
            h = -coeffs['D'] / (2 * coeffs['A'])
            k = -coeffs['E'] / (2 * coeffs['C'])

            # Calculate semi-major and semi-minor axes
            constant = (
                coeffs['F']
                - (coeffs['D'] ** 2 / (4 * coeffs['A']))
                - (coeffs['E'] ** 2 / (4 * coeffs['C']))
            )

            if constant == 0:
                return json.dumps(
                    {
                        "result": {
                            "error": "equation represents degenerate ellipse",
                            "equation": equation,
                            "center": [float(h), float(k)],
                        }
                    }
                )

            a_squared = -constant / coeffs['A']
            b_squared = -constant / coeffs['C']

            if a_squared <= 0 or b_squared <= 0:
                return json.dumps(
                    {
                        "result": {
                            "error": "Not a real ellipse",
                            "equation": equation,
                        }
                    }
                )

            a = sp.sqrt(a_squared)
            b = sp.sqrt(b_squared)

            # Determine orientation
            if a_squared > b_squared:
                semi_major = a
                semi_minor = b
                orientation = "x"
            else:
                semi_major = b
                semi_minor = a
                orientation = "y"

            # Calculate eccentricity and foci
            c = sp.sqrt(abs(semi_major**2 - semi_minor**2))
            e = c / semi_major

            if orientation == "x":
                focus1 = [float(h + c), float(k)]
                focus2 = [float(h - c), float(k)]
            else:
                focus1 = [float(h), float(k + c)]
                focus2 = [float(h), float(k - c)]

            return json.dumps(
                {
                    "result": {
                        "equation": equation,
                        "center": [float(h), float(k)],
                        "semi_major": float(semi_major),
                        "semi_minor": float(semi_minor),
                        "orientation": orientation,
                        "eccentricity": float(e),
                        "foci": [focus1, focus2],
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("parse_ellipse_equation", e)

    def parse_hyperbola_equation(self, equation: str) -> str:
        r"""Parses a hyperbola equation and extracts its properties.

        Args:
            equation: The equation of the hyperbola
                    (e.g., "x^2/9 - y^2/4 = 1" or "(y-3)^2/16-(x+2)^2/25 = 1")

        Returns:
            str: JSON string with the hyperbola properties
        """
        try:
            # Clean up the equation
            eq = equation.replace(" ", "").replace("^", "**").lower()

            # Parse the equation using sympy
            lhs, rhs = eq.split("=")
            expr = sp.sympify(lhs) - sp.sympify(rhs)

            # Convert to standard form Ax^2 + Cy^2 + Dx + Ey + F = 0
            expr = sp.expand(expr)

            # Extract coefficients
            x, y = sp.symbols('x y')
            coeffs = {
                'A': expr.coeff(x, 2),
                'C': expr.coeff(y, 2),
                'D': expr.coeff(x, 1),
                'E': expr.coeff(y, 1),
                'F': expr.subs({x: 0, y: 0}),
            }

            # Check if it's a hyperbola (A and C have opposite signs)
            if coeffs['A'] * coeffs['C'] >= 0:
                return json.dumps(
                    {
                        "result": {
                            "error": "equation does not represent a hyperbola",
                            "equation": equation,
                        }
                    }
                )

            # Calculate center
            h = (
                -coeffs['D'] / (2 * coeffs['A'])
                if coeffs['A'] != 0
                else -coeffs['D'] / (2 * coeffs['C'])
            )
            k = (
                -coeffs['E'] / (2 * coeffs['C'])
                if coeffs['C'] != 0
                else -coeffs['E'] / (2 * coeffs['A'])
            )

            # Calculate semi-axes
            constant = (
                coeffs['F']
                - (coeffs['D'] ** 2 / (4 * coeffs['A']))
                - (coeffs['E'] ** 2 / (4 * coeffs['C']))
            )

            # Determine orientation and calculate semi-axes
            if coeffs['A'] > 0 and coeffs['C'] < 0:
                # Transverse axis along x-axis: x²/a² - y²/b² = 1
                orientation = "x"
                a_squared = -constant / coeffs['A']
                b_squared = constant / coeffs['C']
            else:  # coeffs['A'] < 0 and coeffs['C'] > 0
                # Transverse axis along y-axis: y²/a² - x²/b² = 1
                orientation = "y"
                a_squared = -constant / coeffs['C']
                b_squared = constant / coeffs['A']

            if a_squared <= 0 or b_squared <= 0:
                return json.dumps(
                    {
                        "result": {
                            "error": "Invalid hyperbola equation",
                            "equation": equation,
                        }
                    }
                )

            a = sp.sqrt(a_squared)
            b = sp.sqrt(b_squared)

            # Calculate focal distance and eccentricity
            c = sp.sqrt(a_squared + b_squared)
            e = c / a

            # Calculate foci
            if orientation == "x":
                focus1 = [float(h + c), float(k)]
                focus2 = [float(h - c), float(k)]
            else:
                focus1 = [float(h), float(k + c)]
                focus2 = [float(h), float(k - c)]

            # Calculate asymptotes
            if orientation == "x":
                slope = b / a
                asymptote1 = f"y = {k} + {float(slope)}(x - {h})"
                asymptote2 = f"y = {k} - {float(slope)}(x - {h})"
            else:
                slope = a / b
                asymptote1 = f"y = {k} + {float(slope)}(x - {h})"
                asymptote2 = f"y = {k} - {float(slope)}(x - {h})"

            return json.dumps(
                {
                    "result": {
                        "equation": equation,
                        "center": [float(h), float(k)],
                        "semi_major": float(a),
                        "semi_minor": float(b),
                        "orientation": orientation,
                        "eccentricity": float(e),
                        "foci": [focus1, focus2],
                        "asymptotes": [asymptote1, asymptote2],
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("parse_hyperbola_equation", e)

    def parse_parabola_equation(self, equation: str) -> str:
        r"""Parses a parabola equation and extracts its properties.

        Args:
            equation: The equation of the parabola
                    (e.g., "y = x^2" or "x = 2(y-3)^2 + 1")

        Returns:
            str: JSON string with the parabola properties
        """
        try:
            # Clean up the equation
            eq = equation.replace(" ", "").replace("^", "**").lower()

            # Parse the equation using sympy
            lhs, rhs = eq.split("=")
            expr = sp.sympify(lhs) - sp.sympify(rhs)

            # Convert to standard form Ax^2 + Bxy + Cy^2 + Dx + Ey + F = 0
            expr = sp.expand(expr)

            # Extract coefficients
            x, y = sp.symbols('x y')
            coeffs = {
                'A': expr.coeff(x, 2),
                'B': expr.coeff(x * y),
                'C': expr.coeff(y, 2),
                'D': expr.coeff(x, 1),
                'E': expr.coeff(y, 1),
                'F': expr.subs({x: 0, y: 0}),
            }

            # Check if it's a parabola (one of A or C is zero, but not both)
            if (abs(coeffs['A']) < 1e-10 and abs(coeffs['C']) < 1e-10) or abs(
                coeffs['B']
            ) > 1e-10:
                return json.dumps(
                    {
                        "result": {
                            "error": "Not a standard form parabola",
                            "equation": equation,
                        }
                    }
                )

            # Determine orientation and vertex
            if abs(coeffs['A']) < 1e-10:  # C ≠ 0, A = 0
                # Parabola opens left or right: x = a(y-k)² + h
                orientation = "right" if coeffs['C'] > 0 else "left"
                a = coeffs['C']

                # Complete the square for y
                # Original: Cy² + Ey + (Dx + F) = 0
                # Rewrite as: C(y² + (E/C)y) + Dx + F = 0
                # Complete square: C(y + E/(2C))² - CE²/(4C²) + Dx + F = 0
                # Simplify: C(y + E/(2C))² + Dx + F - E²/(4C) = 0
                # Rearrange: x = -(C(y + E/(2C))² + F - E²/(4C))/D

                k = -coeffs['E'] / (2 * coeffs['C'])
                h = (
                    -(coeffs['F'] - coeffs['E'] ** 2 / (4 * coeffs['C']))
                    / coeffs['D']
                )

            else:  # A ≠ 0, C = 0
                # Parabola opens up or down: y = a(x-h)² + k
                orientation = "up" if coeffs['A'] > 0 else "down"
                a = coeffs['A']

                # Complete the square for x
                # Original: Ax² + Dx + (Ey + F) = 0
                # Rewrite as: A(x² + (D/A)x) + Ey + F = 0
                # Complete square: A(x + D/(2A))² - AD²/(4A²) + Ey + F = 0
                # Simplify: A(x + D/(2A))² + Ey + F - D²/(4A) = 0
                # Rearrange: y = -(A(x + D/(2A))² + F - D²/(4A))/E

                h = -coeffs['D'] / (2 * coeffs['A'])
                k = (
                    -(coeffs['F'] - coeffs['D'] ** 2 / (4 * coeffs['A']))
                    / coeffs['E']
                )

            # Calculate focal distance and focus
            p = 1 / (4 * abs(a))

            if orientation == "up":
                focus = [float(h), float(k + p)]
                directrix = f"y = {float(k - p)}"
            elif orientation == "down":
                focus = [float(h), float(k - p)]
                directrix = f"y = {float(k + p)}"
            elif orientation == "right":
                focus = [float(h + p), float(k)]
                directrix = f"x = {float(h - p)}"
            else:  # orientation == "left"
                focus = [float(h - p), float(k)]
                directrix = f"x = {float(h + p)}"

            # Vertex form
            if orientation in ["up", "down"]:
                vertex_form = f"y = {float(a)}(x - {float(h)})² + {float(k)}"
            else:
                vertex_form = f"x = {float(a)}(y - {float(k)})² + {float(h)}"

            return json.dumps(
                {
                    "result": {
                        "equation": equation,
                        "vertex": [float(h), float(k)],
                        "focus": focus,
                        "directrix": directrix,
                        "orientation": orientation,
                        "coefficient": float(a),
                        "vertex_form": vertex_form,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("parse_parabola_equation", e)

    def solve_quadratic(self, a: float, b: float, c: float) -> str:
        r"""Solves a quadratic equation ax² + bx + c = 0.

        Args:
            a: Coefficient of x²
            b: Coefficient of x
            c: Constant term

        Returns:
            str: JSON string with the roots of the equation
        """
        try:
            self.logger.info(
                f"Solving quadratic equation: {a}x² + {b}x + {c} = 0"
            )

            # Handle the case where a is zero (linear equation)
            if abs(a) < 1e-10:
                if abs(b) < 1e-10:
                    if abs(c) < 1e-10:
                        return json.dumps({"result": "infinite solutions"})
                    else:
                        return json.dumps({"result": "no solutions"})
                else:
                    x = -c / b
                    return json.dumps({"result": [float(x)]})

            # Calculate the discriminant
            discriminant = b**2 - 4 * a * c

            # Calculate roots based on the discriminant
            if abs(discriminant) < 1e-10:  # Discriminant is approximately zero
                x = -b / (2 * a)
                return json.dumps({"result": [float(x)]})
            elif discriminant > 0:
                x1 = (-b + sp.sqrt(discriminant)) / (2 * a)
                x2 = (-b - sp.sqrt(discriminant)) / (2 * a)
                return json.dumps({"result": [float(x1), float(x2)]})
            else:
                real_part = -b / (2 * a)
                imag_part = sp.sqrt(-discriminant) / (2 * a)
                x1 = complex(float(real_part), float(imag_part))
                x2 = complex(float(real_part), -float(imag_part))
                return json.dumps({"result": [str(x1), str(x2)]})
        except Exception as e:
            return self.handle_exception("solve_quadratic", e)

    def generate_circle_equation(
        self, center_x: float, center_y: float, radius: float
    ) -> str:
        r"""Generates the equation of a circle.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            radius: radius of the circle

        Returns:
            str: JSON string with the equation in standard and general form
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(center_x), float(center_y)
            r = float(radius)

            # Standard form: (x - h)² + (y - k)² = r²
            standard_form = f"(x - {h})² + (y - {k})² = {r}²"

            # General form: x² + y² - 2hx - 2ky + (h² + k² - r²) = 0
            general_form = (
                f"x² + y² - {2*h}x - {2*k}y + {h**2 + k**2 - r**2} = 0"
            )

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("generate_circle_equation", e)

    def generate_ellipse_equation(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Generates the equation of an ellipse.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the equation in standard and general form
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            if orientation.lower() == "x":
                # Standard form: (x-h)²/a² + (y-k)²/b² = 1
                standard_form = f"(x-{h})²/{a}² + (y-{k})²/{b}² = 1"
                # General form: b²(x-h)² + a²(y-k)² = a²b²
                general_form = f"{b}²(x-{h})² + {a}²(y-{k})² = {a}²{b}²"
            else:  # orientation == "y"
                # Standard form: (x-h)²/b² + (y-k)²/a² = 1
                standard_form = f"(x-{h})²/{b}² + (y-{k})²/{a}² = 1"
                # General form: a²(x-h)² + b²(y-k)² = a²b²
                general_form = f"{a}²(x-{h})² + {b}²(y-{k})² = {a}²{b}²"

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("generate_ellipse_equation", e)

    def generate_parabola_equation(
        self,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Generates the equation of a parabola.

        Args:
            vertex_x: x-coordinate of the vertex
            vertex_y: y-coordinate of the vertex
            coefficient: coefficient of the squared term (determines how
                wide/narrow the parabola is)
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"

        Returns:
            str: JSON string with the equation in standard and general form
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(vertex_x), float(vertex_y)
            a = float(coefficient)

            if orientation.lower() == "right":
                # Standard form: (y-k)² = 4a(x-h)
                standard_form = f"(y-{k})² = {4*a}(x-{h})"
                # General form: y² - 2ky + k² - 4ax + 4ah = 0
                general_form = f"y² - {2*k}y + {k**2} - {4*a}x + {4*a*h} = 0"
            elif orientation.lower() == "left":
                # Standard form: (y-k)² = -4a(x-h)
                standard_form = f"(y-{k})² = -{4*a}(x-{h})"
                # General form: y² - 2ky + k² + 4ax - 4ah = 0
                general_form = f"y² - {2*k}y + {k**2} + {4*a}x - {4*a*h} = 0"
            elif orientation.lower() == "up":
                # Standard form: (x-h)² = 4a(y-k)
                standard_form = f"(x-{h})² = {4*a}(y-{k})"
                # General form: x² - 2hx + h² - 4ay + 4ak = 0
                general_form = f"x² - {2*h}x + {h**2} - {4*a}y + {4*a*k} = 0"
            else:  # orientation == "down"
                # Standard form: (x-h)² = -4a(y-k)
                standard_form = f"(x-{h})² = -{4*a}(y-{k})"
                # General form: x² - 2hx + h² + 4ay - 4ak = 0
                general_form = f"x² - {2*h}x + {h**2} + {4*a}y - {4*a*k} = 0"

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("generate_parabola_equation", e)

    def generate_hyperbola_equation(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Generates the equation of a hyperbola.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis (distance from center
                to vertex)
            semi_minor: length of the semi-minor axis
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the equation in standard and general form
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            if orientation.lower() == "x":
                # Standard form: (x-h)²/a² - (y-k)²/b² = 1
                standard_form = f"(x-{h})²/{a}² - (y-{k})²/{b}² = 1"
                # General form: b²(x-h)² - a²(y-k)² = a²b²
                general_form = f"{b}²(x-{h})² - {a}²(y-{k})² = {a}²{b}²"
            else:  # orientation == "y"
                # Standard form: (y-k)²/a² - (x-h)²/b² = 1
                standard_form = f"(y-{k})²/{a}² - (x-{h})²/{b}² = 1"
                # General form: b²(y-k)² - a²(x-h)² = a²b²
                general_form = f"{b}²(y-{k})² - {a}²(x-{h})² = {a}²{b}²"

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("generate_hyperbola_equation", e)

    # ====================== CONIC PROPERTY CALCULATORS ======================

    def compute_circle_properties(
        self, center_x: float, center_y: float, radius: float
    ) -> str:
        r"""Computes properties of a circle.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            radius: radius of the circle

        Returns:
            str: JSON string with the computed properties
        """
        try:
            r = float(radius)

            # Calculate properties
            area = sp.pi * r**2
            circumference = 2 * sp.pi * r

            properties = {
                "area": str(area),
                "circumference": str(circumference),
                "center": [float(center_x), float(center_y)],
                "radius": float(radius),
            }

            return json.dumps({"result": properties})
        except Exception as e:
            return self.handle_exception("compute_circle_properties", e)

    def compute_ellipse_properties(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes properties of an ellipse.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the computed properties
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Calculate properties
            area = sp.pi * a * b
            # Approximation of perimeter using Ramanujan's formula
            perimeter = sp.pi * (
                3 * (a + b) - sp.sqrt((3 * a + b) * (a + 3 * b))
            )
            eccentricity = sp.sqrt(1 - (b**2 / a**2))

            # Calculate foci
            c = sp.sqrt(a**2 - b**2)
            if orientation.lower() == "x":
                foci = [
                    [float(center_x) + c, float(center_y)],
                    [float(center_x) - c, float(center_y)],
                ]
            else:  # orientation == "y"
                foci = [
                    [float(center_x), float(center_y) + c],
                    [float(center_x), float(center_y) - c],
                ]

            properties = {
                "area": str(area),
                "perimeter_approx": str(perimeter),
                "eccentricity": str(eccentricity),
                "center": [float(center_x), float(center_y)],
                "semi_major_axis": float(semi_major),
                "semi_minor_axis": float(semi_minor),
                "foci": foci,
            }

            return json.dumps({"result": properties})
        except Exception as e:
            return self.handle_exception("compute_ellipse_properties", e)

    def compute_parabola_properties(
        self,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Computes properties of a parabola.

        Args:
            vertex_x: x-coordinate of the vertex
            vertex_y: y-coordinate of the vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"

        Returns:
            str: JSON string with the computed properties
        """
        try:
            a = float(coefficient)

            # Calculate focus
            if orientation.lower() in ["right", "left"]:
                focus_distance = abs(1 / (4 * a))
                if orientation.lower() == "right":
                    focus = [float(vertex_x) + focus_distance, float(vertex_y)]
                else:  # orientation == "left"
                    focus = [float(vertex_x) - focus_distance, float(vertex_y)]
            else:  # orientation in ["up", "down"]
                focus_distance = abs(1 / (4 * a))
                if orientation.lower() == "up":
                    focus = [float(vertex_x), float(vertex_y) + focus_distance]
                else:  # orientation == "down"
                    focus = [float(vertex_x), float(vertex_y) - focus_distance]

            properties = {
                "vertex": [float(vertex_x), float(vertex_y)],
                "focus": focus,
                "coefficient": float(coefficient),
                "orientation": orientation,
            }

            return json.dumps({"result": properties})
        except Exception as e:
            return self.handle_exception("compute_parabola_properties", e)

    def compute_hyperbola_properties(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes properties of a hyperbola.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the computed properties
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Calculate properties
            c = sp.sqrt(a**2 + b**2)
            eccentricity = c / a

            # Calculate foci and asymptotes
            if orientation.lower() == "x":
                foci = [
                    [float(center_x) + c, float(center_y)],
                    [float(center_x) - c, float(center_y)],
                ]
                asymptote1 = (
                    f"y = {float(center_y)} + {b/a}(x - {float(center_x)})"
                )
                asymptote2 = (
                    f"y = {float(center_y)} - {b/a}(x - {float(center_x)})"
                )
            else:  # orientation == "y"
                foci = [
                    [float(center_x), float(center_y) + c],
                    [float(center_x), float(center_y) - c],
                ]
                asymptote1 = (
                    f"y = {float(center_y)} + {a/b}(x - {float(center_x)})"
                )
                asymptote2 = (
                    f"y = {float(center_y)} - {a/b}(x - {float(center_x)})"
                )

            properties = {
                "center": [float(center_x), float(center_y)],
                "semi_major_axis": float(semi_major),
                "semi_minor_axis": float(semi_minor),
                "eccentricity": str(eccentricity),
                "foci": foci,
                "asymptotes": [asymptote1, asymptote2],
            }

            return json.dumps({"result": properties})
        except Exception as e:
            return self.handle_exception("compute_hyperbola_properties", e)

    def compute_circle_eccentricity(self) -> str:
        r"""Computes the eccentricity of a circle.

        Returns:
            str: JSON string with the eccentricity (always 0 for a circle)
        """
        try:
            return json.dumps({"result": "0"})
        except Exception as e:
            return self.handle_exception("compute_circle_eccentricity", e)

    def compute_ellipse_eccentricity(
        self, semi_major: float, semi_minor: float
    ) -> str:
        r"""Computes the eccentricity of an ellipse.

        Args:
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis

        Returns:
            str: JSON string with the computed eccentricity
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Ensure a > b
            if b > a:
                a, b = b, a

            eccentricity = sp.sqrt(1 - (b**2 / a**2))

            return json.dumps({"result": str(eccentricity)})
        except Exception as e:
            return self.handle_exception("compute_ellipse_eccentricity", e)

    def compute_parabola_eccentricity(self) -> str:
        r"""Computes the eccentricity of a parabola.

        Returns:
            str: JSON string with the eccentricity (always 1 for a parabola)
        """
        try:
            return json.dumps({"result": "1"})
        except Exception as e:
            return self.handle_exception("compute_parabola_eccentricity", e)

    def compute_hyperbola_eccentricity(
        self, semi_major: float, semi_minor: float
    ) -> str:
        r"""Computes the eccentricity of a hyperbola.

        Args:
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)

        Returns:
            str: JSON string with the computed eccentricity
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            c = sp.sqrt(a**2 + b**2)
            eccentricity = c / a

            return json.dumps({"result": str(eccentricity)})
        except Exception as e:
            return self.handle_exception("compute_hyperbola_eccentricity", e)

    def compute_circle_foci(self, center_x: float, center_y: float) -> str:
        r"""Computes the focus/foci of a circle.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center

        Returns:
            str: JSON string with the focus (same as center for a circle)
        """
        try:
            center = [float(center_x), float(center_y)]
            return json.dumps({"result": {"foci": [center]}})
        except Exception as e:
            return self.handle_exception("compute_circle_foci", e)

    def compute_ellipse_foci(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the foci of an ellipse.

        Args:
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the computed foci
        """
        try:
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Ensure a > b (semi-major > semi-minor)
            if b > a:
                a, b = b, a
                # Adjust orientation if we swapped a and b
                orientation = "y" if orientation.lower() == "x" else "x"

            # Calculate focal distance
            c = float(sp.sqrt(a**2 - b**2))

            # Calculate foci positions
            if orientation.lower() == "x":
                focus1 = [h + c, k]
                focus2 = [h - c, k]
            else:  # orientation == "y"
                focus1 = [h, k + c]
                focus2 = [h, k - c]

            # Convert to float to ensure JSON serialization
            focus1 = [float(focus1[0]), float(focus1[1])]
            focus2 = [float(focus2[0]), float(focus2[1])]

            return json.dumps(
                {
                    "result": {
                        "foci": [focus1, focus2],
                        "focal_distance": float(c),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_ellipse_foci", e)

    def compute_parabola_foci(
        self,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Computes the focus of a parabola.

        Args:
            vertex_x: x-coordinate of the vertex
            vertex_y: y-coordinate of the vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"

        Returns:
            str: JSON string with the computed focus
        """
        try:
            a = float(coefficient)

            # Calculate focus position
            p = 1 / (4 * abs(a))  # focal distance

            if orientation.lower() == "right":
                focus = [float(vertex_x) + p, float(vertex_y)]
            elif orientation.lower() == "left":
                focus = [float(vertex_x) - p, float(vertex_y)]
            elif orientation.lower() == "up":
                focus = [float(vertex_x), float(vertex_y) + p]
            else:  # orientation == "down"
                focus = [float(vertex_x), float(vertex_y) - p]

            return json.dumps({"result": {"foci": [focus]}})
        except Exception as e:
            return self.handle_exception("compute_parabola_foci", e)

    def compute_hyperbola_foci(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the foci of a hyperbola.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the computed foci
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Calculate focal distance
            c = sp.sqrt(a**2 + b**2)

            # Calculate foci positions
            if orientation.lower() == "x":
                focus1 = [float(center_x) + c, float(center_y)]
                focus2 = [float(center_x) - c, float(center_y)]
            else:  # orientation == "y"
                focus1 = [float(center_x), float(center_y) + c]
                focus2 = [float(center_x), float(center_y) - c]

            return json.dumps({"result": {"foci": [focus1, focus2]}})
        except Exception as e:
            return self.handle_exception("compute_hyperbola_foci", e)

    def compute_circle_directrix(self) -> str:
        r"""Computes the directrix/directrices of a circle.

        Returns:
            str: JSON string explaining that circles don't have directrices
        """
        try:
            return json.dumps(
                {
                    "result": {
                        "message": (
                            "Circles do not have directrices. The concept of "
                            "directrix applies to ellipses, parabolas, "
                            "and hyperbolas."
                        )
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_circle_directrix", e)

    def compute_ellipse_directrices(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the directrices of an ellipse.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the computed directrices
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Calculate eccentricity
            e = sp.sqrt(1 - (b**2 / a**2))

            # Calculate directrix distance from center
            d = a**2 / (a * e)

            # Define directrices
            if orientation.lower() == "x":
                directrix1 = f"x = {float(center_x) + d}"
                directrix2 = f"x = {float(center_x) - d}"
            else:  # orientation == "y"
                directrix1 = f"y = {float(center_y) + d}"
                directrix2 = f"y = {float(center_y) - d}"

            return json.dumps(
                {"result": {"directrices": [directrix1, directrix2]}}
            )
        except Exception as e:
            return self.handle_exception("compute_ellipse_directrices", e)

    def compute_parabola_directrix(
        self,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Computes the directrix of a parabola.

        Args:
            vertex_x: x-coordinate of the vertex
            vertex_y: y-coordinate of the vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"

        Returns:
            str: JSON string with the computed directrix
        """
        try:
            a = float(coefficient)

            # Calculate directrix distance from vertex
            p = 1 / (4 * abs(a))  # focal distance

            # Define directrix
            if orientation.lower() == "right":
                directrix = f"x = {float(vertex_x) - p}"
            elif orientation.lower() == "left":
                directrix = f"x = {float(vertex_x) + p}"
            elif orientation.lower() == "up":
                directrix = f"y = {float(vertex_y) - p}"
            else:  # orientation == "down"
                directrix = f"y = {float(vertex_y) + p}"

            return json.dumps({"result": {"directrix": directrix}})
        except Exception as e:
            return self.handle_exception("compute_parabola_directrix", e)

    def compute_hyperbola_directrices(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the directrices of a hyperbola.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the computed directrices
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Calculate eccentricity
            c = sp.sqrt(a**2 + b**2)
            e = c / a

            # Calculate directrix distance from center
            d = a**2 / (a * e)

            # Define directrices
            if orientation.lower() == "x":
                directrix1 = f"x = {float(center_x) + d}"
                directrix2 = f"x = {float(center_x) - d}"
            else:  # orientation == "y"
                directrix1 = f"y = {float(center_y) + d}"
                directrix2 = f"y = {float(center_y) - d}"

            return json.dumps(
                {"result": {"directrices": [directrix1, directrix2]}}
            )
        except Exception as e:
            return self.handle_exception("compute_hyperbola_directrices", e)

    def compute_circle_asymptotes(self) -> str:
        r"""Computes the asymptotes of a circle.

        Returns:
            str: JSON string explaining that circles don't have asymptotes
        """
        try:
            return json.dumps(
                {
                    "result": {
                        "message": (
                            "Circles do not have asymptotes. "
                            "Only hyperbolas have asymptotes."
                        )
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_circle_asymptotes", e)

    def compute_ellipse_asymptotes(self) -> str:
        r"""Computes the asymptotes of an ellipse.

        Returns:
            str: JSON string explaining that ellipses don't have asymptotes
        """
        try:
            return json.dumps(
                {
                    "result": {
                        "message": (
                            "Ellipses do not have asymptotes. "
                            "Only hyperbolas have asymptotes."
                        )
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_ellipse_asymptotes", e)

    def compute_parabola_asymptotes(self) -> str:
        r"""Computes the asymptotes of a parabola.

        Returns:
            str: JSON string explaining that parabolas don't have asymptotes
        """
        try:
            return json.dumps(
                {
                    "result": {
                        "message": (
                            "Parabolas do not have asymptotes. "
                            "Only hyperbolas have asymptotes."
                        )
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_parabola_asymptotes", e)

    def compute_hyperbola_asymptotes(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the asymptotes of a hyperbola.

        Args:
            center_x: x-coordinate of the center
            center_y: y-coordinate of the center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the computed asymptotes
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)
            h = float(center_x)
            k = float(center_y)

            # Calculate asymptotes
            if orientation.lower() == "x":
                slope = b / a
                asymptote1 = f"y = {k} + {slope}(x - {h})"
                asymptote2 = f"y = {k} - {slope}(x - {h})"

                # Alternative form
                asymptote1_alt = f"y = {slope}x + {k - slope*h}"
                asymptote2_alt = f"y = -{slope}x + {k + slope*h}"
            else:  # orientation == "y"
                slope = a / b
                asymptote1 = f"y = {k} + {slope}(x - {h})"
                asymptote2 = f"y = {k} - {slope}(x - {h})"

                # Alternative form
                asymptote1_alt = f"y = {slope}x + {k - slope*h}"
                asymptote2_alt = f"y = -{slope}x + {k + slope*h}"

            return json.dumps(
                {
                    "result": {
                        "asymptotes": [asymptote1, asymptote2],
                        "alternative_form": [asymptote1_alt, asymptote2_alt],
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_hyperbola_asymptotes", e)

    # ====================== GEOMETRIC OPERATIONS ======================

    def compute_line_circle_intersection(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        line_slope: float,
        line_y_intercept: float,
    ) -> str:
        r"""Computes the intersection points of a line and a circle.

        Args:
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle
            line_slope: slope of the line (m in y = mx + b)
            line_y_intercept: y-intercept of the line (b in y = mx + b)

        Returns:
            str: JSON string with the computed intersection points
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(center_x), float(center_y)
            r = float(radius)
            m = float(line_slope)
            b = float(line_y_intercept)

            # Circle equation: (x - h)² + (y - k)² = r²
            # Line equation: y = mx + b

            # Substitute line equation into circle equation
            # (x - h)² + (mx + b - k)² = r²
            circle_eq = (x - h) ** 2 + (m * x + b - k) ** 2 - r**2

            # Solve for x
            x_solutions = sp.solve(circle_eq, x)

            # Calculate corresponding y values
            intersection_points = []
            for x_sol in x_solutions:
                x_val = float(x_sol)
                y_val = float(m * x_val + b)
                intersection_points.append([x_val, y_val])

            return json.dumps(
                {
                    "result": {
                        "intersection_points": intersection_points,
                        "count": len(intersection_points),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_line_circle_intersection", e)

    def compute_line_ellipse_intersection(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
        line_slope: float,
        line_y_intercept: float,
    ) -> str:
        r"""Computes the intersection points of a line and an ellipse.

        Args:
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis
            line_slope: slope of the line (m in y = mx + b)
            line_y_intercept: y-intercept of the line (b in y = mx + b)

        Returns:
            str: JSON string with the computed intersection points
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)
            m = float(line_slope)
            c = float(
                line_y_intercept
            )  # Using c for y-intercept to avoid confusion with axis b

            # Ellipse equation depends on orientation
            if orientation.lower() == "x":
                # (x-h)²/a² + (y-k)²/b² = 1
                ellipse_eq = (
                    (x - h) ** 2 / a**2 + (m * x + c - k) ** 2 / b**2 - 1
                )
            else:  # orientation == "y"
                # (x-h)²/b² + (y-k)²/a² = 1
                ellipse_eq = (
                    (x - h) ** 2 / b**2 + (m * x + c - k) ** 2 / a**2 - 1
                )

            # Solve for x
            x_solutions = sp.solve(ellipse_eq, x)

            # Calculate corresponding y values
            intersection_points = []
            for x_sol in x_solutions:
                try:
                    x_val = float(x_sol)
                    y_val = float(m * x_val + c)
                    intersection_points.append([x_val, y_val])
                except Exception:
                    # Skip complex solutions
                    continue

            return json.dumps(
                {
                    "result": {
                        "intersection_points": intersection_points,
                        "count": len(intersection_points),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_line_ellipse_intersection", e
            )

    def compute_line_parabola_intersection(
        self,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
        line_slope: float,
        line_y_intercept: float,
    ) -> str:
        r"""Computes the intersection points of a line and a parabola.

        Args:
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"
            line_slope: slope of the line (m in y = mx + b)
            line_y_intercept: y-intercept of the line (b in y = mx + b)

        Returns:
            str: JSON string with the computed intersection points
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(vertex_x), float(vertex_y)
            a = float(coefficient)
            m = float(line_slope)
            b = float(line_y_intercept)

            # Parabola equation depends on orientation
            if orientation.lower() == "right":
                # y - k = a(x - h)²
                parabola_eq = m * x + b - (k + a * (x - h) ** 2)
            elif orientation.lower() == "left":
                # y - k = a(x - h)²
                parabola_eq = m * x + b - (k + a * (x - h) ** 2)
            elif orientation.lower() == "up":
                # x - h = a(y - k)²
                parabola_eq = x - h - a * (m * x + b - k) ** 2
            else:  # orientation == "down"
                # x - h = a(y - k)²
                parabola_eq = x - h - a * (m * x + b - k) ** 2

            # Solve for x
            x_solutions = sp.solve(parabola_eq, x)

            # Calculate corresponding y values
            intersection_points = []
            for x_sol in x_solutions:
                try:
                    x_val = float(x_sol)
                    y_val = float(m * x_val + b)
                    intersection_points.append([x_val, y_val])
                except Exception:
                    # Skip complex solutions
                    continue

            return json.dumps(
                {
                    "result": {
                        "intersection_points": intersection_points,
                        "count": len(intersection_points),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_line_parabola_intersection", e
            )

    def compute_line_hyperbola_intersection(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
        line_slope: float,
        line_y_intercept: float,
    ) -> str:
        r"""Computes the intersection points of a line and a hyperbola.

        Args:
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis
            line_slope: slope of the line (m in y = mx + b)
            line_y_intercept: y-intercept of the line (b in y = mx + b)

        Returns:
            str: JSON string with the computed intersection points
        """
        try:
            x, y = sp.symbols('x y')
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)
            m = float(line_slope)
            c = float(
                line_y_intercept
            )  # Using c for y-intercept to avoid confusion with axis b

            # Hyperbola equation depends on orientation
            if orientation.lower() == "x":
                # (x-h)²/a² - (y-k)²/b² = 1
                hyperbola_eq = (
                    (x - h) ** 2 / a**2 - (m * x + c - k) ** 2 / b**2 - 1
                )
            else:  # orientation == "y"
                # (y-k)²/a² - (x-h)²/b² = 1
                hyperbola_eq = (
                    (m * x + c - k) ** 2 / a**2 - (x - h) ** 2 / b**2 - 1
                )

            # Solve for x
            x_solutions = sp.solve(hyperbola_eq, x)

            # Calculate corresponding y values
            intersection_points = []
            for x_sol in x_solutions:
                try:
                    x_val = float(x_sol)
                    y_val = float(m * x_val + c)
                    intersection_points.append([x_val, y_val])
                except Exception:
                    # Skip complex solutions
                    continue

            return json.dumps(
                {
                    "result": {
                        "intersection_points": intersection_points,
                        "count": len(intersection_points),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_line_hyperbola_intersection", e
            )

    def check_point_position_circle(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> str:
        r"""Checks the position of a point relative to a circle.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle

        Returns:
            str: JSON string with the position ("inside", "outside", or "on")
        """
        try:
            p = sp.Point(float(point_x), float(point_y))
            c = sp.Point(float(center_x), float(center_y))
            r = float(radius)

            # Calculate distance from point to center
            distance = p.distance(c)

            # Determine position
            if (
                abs(distance - r) < 1e-10
            ):  # Account for floating-point precision
                position = "on"
            elif distance < r:
                position = "inside"
            else:
                position = "outside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "distance_from_center": str(distance),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_circle", e)

    def check_point_position_ellipse(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Checks the position of a point relative to an ellipse.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the position ("inside", "outside", or "on")
        """
        try:
            x = float(point_x)
            y = float(point_y)
            h = float(center_x)
            k = float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Evaluate the ellipse equation at the point
            if orientation.lower() == "x":
                # (x-h)²/a² + (y-k)²/b² = 1
                value = (x - h) ** 2 / a**2 + (y - k) ** 2 / b**2
            else:  # orientation == "y"
                # (x-h)²/b² + (y-k)²/a² = 1
                value = (x - h) ** 2 / b**2 + (y - k) ** 2 / a**2

            # Determine position
            if abs(value - 1) < 1e-10:  # Account for floating-point precision
                position = "on"
            elif value < 1:
                position = "inside"
            else:
                position = "outside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "equation_value": str(value),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_ellipse", e)

    def check_point_position_parabola(
        self,
        point_x: float,
        point_y: float,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Checks the position of a point relative to a parabola.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"

        Returns:
            str: JSON string with the position ("on", "inside", or "outside")
        """
        try:
            x = float(point_x)
            y = float(point_y)
            h = float(vertex_x)
            k = float(vertex_y)
            a = float(coefficient)

            # Evaluate the parabola equation at the point
            if orientation.lower() == "right":
                # y - k = a(x - h)²
                expected_y = k + a * (x - h) ** 2
                value = y - expected_y
            elif orientation.lower() == "left":
                # y - k = a(x - h)²
                expected_y = k + a * (x - h) ** 2
                value = y - expected_y
            elif orientation.lower() == "up":
                # x - h = a(y - k)²
                expected_x = h + a * (y - k) ** 2
                value = x - expected_x
            else:  # orientation == "down"
                # x - h = a(y - k)²
                expected_x = h + a * (y - k) ** 2
                value = x - expected_x

            # Determine position
            if abs(value) < 1e-10:  # Account for floating-point precision
                position = "on"
            else:
                # For parabolas, "inside" and "outside" depend
                # on the orientation
                if orientation.lower() == "right":
                    position = "inside" if value < 0 else "outside"
                elif orientation.lower() == "left":
                    position = "inside" if value > 0 else "outside"
                elif orientation.lower() == "up":
                    position = "inside" if value < 0 else "outside"
                else:  # orientation == "down"
                    position = "inside" if value > 0 else "outside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "equation_value": str(value),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_parabola", e)

    def check_point_position_hyperbola(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Checks the position of a point relative to a hyperbola.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the position ("on", "inside", or "outside")
        """
        try:
            x = float(point_x)
            y = float(point_y)
            h = float(center_x)
            k = float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Evaluate the hyperbola equation at the point
            if orientation.lower() == "x":
                # (x-h)²/a² - (y-k)²/b² = 1
                value = (x - h) ** 2 / a**2 - (y - k) ** 2 / b**2
            else:  # orientation == "y"
                # (y-k)²/a² - (x-h)²/b² = 1
                value = (y - k) ** 2 / a**2 - (x - h) ** 2 / b**2

            # Determine position
            if abs(value - 1) < 1e-10:  # Account for floating-point precision
                position = "on"
            else:
                # For hyperbolas, there's no clear "inside" or "outside"
                # "inside" for points between branches, "outside" otherwise
                position = (
                    "between branches" if value < 1 else "on branch side"
                )

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "equation_value": str(value),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_hyperbola", e)

    def compute_tangent_line_circle(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> str:
        r"""Computes the tangent line(s) to a circle from a point.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle

        Returns:
            str: JSON string with the tangent line equation(s)
        """
        try:
            p = sp.Point(float(point_x), float(point_y))
            c = sp.Point(float(center_x), float(center_y))
            r = float(radius)

            # Calculate distance from point to center
            distance = p.distance(c)

            # Check if point is inside the circle
            if distance < r:
                return json.dumps(
                    {
                        "result": {
                            "message": (
                                "No tangent lines exist from a point "
                                "inside the circle."
                            )
                        }
                    }
                )

            # Check if point is on the circle
            if (
                abs(distance - r) < 1e-10
            ):  # Account for floating-point precision
                # Point is on circle - one tangent line perpendicular to radius
                # Calculate the slope of the radius
                if abs(p.x - c.x) < 1e-10:  # Vertical radius
                    # Tangent is horizontal
                    tangent_eq = f"y = {float(p.y)}"
                else:
                    radius_slope = (p.y - c.y) / (p.x - c.x)
                    # Tangent slope is negative reciprocal of radius slope
                    tangent_slope = -1 / radius_slope
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {float(p.y)} = {float(tangent_slope)}"
                        f"(x - {float(p.x)})"
                    )
                    # Simplify to y = mx + b form
                    tangent_slope_val = float(tangent_slope)
                    tangent_y_intercept = float(p.y - tangent_slope * p.x)
                    tangent_eq_simplified = (
                        f"y = {tangent_slope_val}x + " f"{tangent_y_intercept}"
                    )

                return json.dumps(
                    {
                        "result": {
                            "tangent_lines": [tangent_eq],
                            "simplified_form": [tangent_eq_simplified]
                            if 'tangent_eq_simplified' in locals()
                            else None,
                            "count": 1,
                        }
                    }
                )

            # Point is outside the circle, so there are two tangent lines
            # This is more complex and requires solving a system of equations
            # We'll use the power of a point theorem

            # First, find the power of the point
            power = distance**2 - r**2

            # Calculate the points of tangency
            x, y = sp.symbols('x y')

            # Equation of the circle
            circle_eq = (x - c.x) ** 2 + (y - c.y) ** 2 - r**2

            # Points where line from p to (x,y) is tangent to circle
            # Dot product of (x-c.x, y-c.y) and (x-p.x, y-p.y) = 0
            tangent_condition = (x - c.x) * (x - p.x) + (y - c.y) * (y - p.y)

            # Solve the system of equations
            tangent_points = sp.solve([circle_eq, tangent_condition], [x, y])

            # Calculate the tangent lines
            tangent_lines = []
            tangent_lines_simplified = []

            for point in tangent_points:
                t_x, t_y = float(point[0]), float(point[1])

                # Check if the tangent line is vertical
                if abs(t_x - p.x) < 1e-10:
                    tangent_eq = f"x = {float(p.x)}"
                    tangent_lines.append(tangent_eq)
                    tangent_lines_simplified.append(tangent_eq)
                else:
                    # Calculate the slope of the tangent line
                    tangent_slope = (t_y - p.y) / (t_x - p.x)
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {float(p.y)} = {float(tangent_slope)}"
                        f"(x - {float(p.x)})"
                    )
                    # Simplify to y = mx + b form
                    b_value = float(p.y - tangent_slope * p.x)
                    tangent_eq_simplified = f"y = {float(tangent_slope)}x + "
                    tangent_eq_simplified += f"{b_value}"

                    tangent_lines.append(tangent_eq)
                    tangent_lines_simplified.append(tangent_eq_simplified)

            return json.dumps(
                {
                    "result": {
                        "tangent_lines": tangent_lines,
                        "simplified_form": tangent_lines_simplified,
                        "tangent_points": [
                            [float(point[0]), float(point[1])]
                            for point in tangent_points
                        ],
                        "count": len(tangent_lines),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_tangent_line_circle", e)

    def compute_tangent_line_at_point_circle(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> str:
        r"""Computes the tangent line to a circle at a specific point
            on the circle.

        Args:
            point_x: x-coordinate of the point on the circle
            point_y: y-coordinate of the point on the circle
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle

        Returns:
            str: JSON string with the tangent line equation
        """
        try:
            p = sp.Point(float(point_x), float(point_y))
            c = sp.Point(float(center_x), float(center_y))
            r = float(radius)

            # Check if the point is on the circle
            distance = p.distance(c)
            if abs(distance - r) > 1e-10:  # Not on the circle
                return json.dumps(
                    {
                        "result": {
                            "message": f"The point ({float(p.x)},{float(p.y)})"
                            f"is not on the circle. Distance from "
                            f"center: {float(distance)}, "
                            f"radius: {float(r)}."
                        }
                    }
                )

            # Calculate the tangent line (perpendicular to the radius)
            if abs(p.x - c.x) < 1e-10:  # Vertical radius
                # Tangent is horizontal
                tangent_eq = f"y = {float(p.y)}"
                tangent_eq_simplified = tangent_eq
            else:
                radius_slope = (p.y - c.y) / (p.x - c.x)
                # Tangent slope is negative reciprocal of radius slope
                tangent_slope = -1 / radius_slope
                # y - y1 = m(x - x1)
                tangent_eq = f"y - {float(p.y)} = {float(tangent_slope)}(x - "
                tangent_eq += f"{float(p.x)})"
                # Simplify to y = mx + b form
                b_value = float(p.y - tangent_slope * p.x)
                tangent_eq_simplified = f"y = {float(tangent_slope)}x + "
                tangent_eq_simplified += f"{b_value}"

            return json.dumps(
                {
                    "result": {
                        "tangent_line": tangent_eq,
                        "simplified_form": tangent_eq_simplified,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_tangent_line_at_point_circle", e
            )

    def compute_tangent_line_at_point_ellipse(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the tangent line to an ellipse at a specific point
            on the ellipse.

        Args:
            point_x: x-coordinate of the point on the ellipse
            point_y: y-coordinate of the point on the ellipse
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the tangent line equation
        """
        try:
            x, y = sp.symbols('x y')
            p_x = float(point_x)
            p_y = float(point_y)
            h = float(center_x)
            k = float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Check if the point is on the ellipse
            if orientation.lower() == "x":
                # (x-h)²/a² + (y-k)²/b² = 1
                value = (p_x - h) ** 2 / a**2 + (p_y - k) ** 2 / b**2
            else:  # orientation == "y"
                # (x-h)²/b² + (y-k)²/a² = 1
                value = (p_x - h) ** 2 / b**2 + (p_y - k) ** 2 / a**2

            if abs(value - 1) > 1e-10:  # Not on the ellipse
                return json.dumps(
                    {
                        "result": {
                            "message": f"The point ({p_x}, {p_y}) is not on"
                            f"the ellipse. Equation value: "
                            f"{float(value)}, expected: 1."
                        }
                    }
                )

            # Calculate the tangent line
            if orientation.lower() == "x":
                # Derivative of ellipse equation:
                # 2(x-h)/a² + 2(y-k)/b² * dy/dx = 0
                # Solve for dy/dx: dy/dx = -b²(x-h)/(a²(y-k))
                if (
                    abs(p_y - k) < 1e-10
                ):  # Point is at the top or bottom of the ellipse
                    tangent_eq = f"y = {p_y}"
                    tangent_eq_simplified = tangent_eq
                else:
                    tangent_slope = -(b**2) * (p_x - h) / (a**2 * (p_y - k))
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_slope_val = float(tangent_slope)
                    tangent_y_intercept = float(p_y - tangent_slope * p_x)
                    tangent_eq_simplified = (
                        f"y = {tangent_slope_val}x + {tangent_y_intercept}"
                    )
            else:  # orientation == "y"
                # Derivative of ellipse equation:
                # 2(x-h)/b² + 2(y-k)/a² * dy/dx = 0
                # Solve for dy/dx: dy/dx = -b²(x-h)/(a²(y-k))
                if (
                    abs(p_y - k) < 1e-10
                ):  # Point is at the left or right of the ellipse
                    tangent_eq = f"x = {p_x}"
                    tangent_eq_simplified = tangent_eq
                else:
                    tangent_slope = -(b**2) * (p_x - h) / (a**2 * (p_y - k))
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_slope_val = float(tangent_slope)
                    tangent_y_intercept = float(p_y - tangent_slope * p_x)
                    tangent_eq_simplified = (
                        f"y = {tangent_slope_val}x + {tangent_y_intercept}"
                    )

            return json.dumps(
                {
                    "result": {
                        "tangent_line": tangent_eq,
                        "simplified_form": tangent_eq_simplified,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_tangent_line_at_point_ellipse", e
            )

    def compute_tangent_line_at_point_parabola(
        self,
        point_x: float,
        point_y: float,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Computes the tangent line to a parabola at a specific point
            on the parabola.

        Args:
            point_x: x-coordinate of the point on the parabola
            point_y: y-coordinate of the point on the parabola
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"

        Returns:
            str: JSON string with the tangent line equation
        """
        try:
            p_x = float(point_x)
            p_y = float(point_y)
            h = float(vertex_x)
            k = float(vertex_y)
            a = float(coefficient)

            # Check if the point is on the parabola
            if orientation.lower() == "right":
                # y - k = a(x - h)²
                expected_y = k + a * (p_x - h) ** 2
                on_parabola = abs(p_y - expected_y) < 1e-10
            elif orientation.lower() == "left":
                # y - k = a(x - h)²
                expected_y = k + a * (p_x - h) ** 2
                on_parabola = abs(p_y - expected_y) < 1e-10
            elif orientation.lower() == "up":
                # x - h = a(y - k)²
                expected_x = h + a * (p_y - k) ** 2
                on_parabola = abs(p_x - expected_x) < 1e-10
            else:  # orientation == "down"
                # x - h = a(y - k)²
                expected_x = h + a * (p_y - k) ** 2
                on_parabola = abs(p_x - expected_x) < 1e-10

            if not on_parabola:
                return json.dumps(
                    {
                        "result": {
                            "message": f"The point ({p_x}, {p_y}) is not"
                            f"on the parabola."
                        }
                    }
                )

            # Calculate the tangent line
            if orientation.lower() == "right":
                # Derivative: dy/dx = 2a(x - h)
                tangent_slope = 2 * a * (p_x - h)
                # y - y1 = m(x - x1)
                tangent_eq = f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                # Simplify to y = mx + b form
                tangent_eq_simplified = (
                    f"y = {float(tangent_slope)}x + "
                    f"{float(p_y - tangent_slope*p_x)}"
                )
            elif orientation.lower() == "left":
                # Derivative: dy/dx = 2a(x - h)
                tangent_slope = 2 * a * (p_x - h)
                # y - y1 = m(x - x1)
                tangent_eq = f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                # Simplify to y = mx + b form
                tangent_eq_simplified = (
                    f"y = {float(tangent_slope)}x + "
                    f"{float(p_y - tangent_slope*p_x)}"
                )
            elif orientation.lower() == "up":
                # Derivative: dx/dy = 2a(y - k)
                # Convert to dy/dx = 1/(2a(y - k))
                if abs(p_y - k) < 1e-10:  # At vertex
                    tangent_eq = f"x = {p_x}"
                    tangent_eq_simplified = tangent_eq
                else:
                    tangent_slope = 1 / (2 * a * (p_y - k))
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_eq_simplified = (
                        f"y = {float(tangent_slope)}x + "
                        f"{float(p_y - tangent_slope*p_x)}"
                    )
            else:  # orientation == "down"
                # Derivative: dx/dy = 2a(y - k)
                # Convert to dy/dx = 1/(2a(y - k))
                if abs(p_y - k) < 1e-10:  # At vertex
                    tangent_eq = f"x = {p_x}"
                    tangent_eq_simplified = tangent_eq
                else:
                    tangent_slope = 1 / (2 * a * (p_y - k))
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_eq_simplified = (
                        f"y = {float(tangent_slope)}x + "
                        f"{float(p_y - tangent_slope*p_x)}"
                    )

            return json.dumps(
                {
                    "result": {
                        "tangent_line": tangent_eq,
                        "simplified_form": tangent_eq_simplified,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_tangent_line_at_point_parabola", e
            )

    def compute_tangent_line_at_point_hyperbola(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the tangent line to a hyperbola at a specific point
            on the hyperbola.

        Args:
            point_x: x-coordinate of the point on the hyperbola
            point_y: y-coordinate of the point on the hyperbola
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis

        Returns:
            str: JSON string with the tangent line equation
        """
        try:
            p_x = float(point_x)
            p_y = float(point_y)
            h = float(center_x)
            k = float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Check if the point is on the hyperbola
            if orientation.lower() == "x":
                # (x-h)²/a² - (y-k)²/b² = 1
                value = (p_x - h) ** 2 / a**2 - (p_y - k) ** 2 / b**2
            else:  # orientation == "y"
                # (y-k)²/a² - (x-h)²/b² = 1
                value = (p_y - k) ** 2 / a**2 - (p_x - h) ** 2 / b**2

            if abs(value - 1) > 1e-10:  # Not on the hyperbola
                return json.dumps(
                    {
                        "result": {
                            "message": f"The point ({p_x}, {p_y}) is not on"
                            f"the hyperbola. Equation value: "
                            f"{float(value)}, expected: 1."
                        }
                    }
                )

            # Calculate the tangent line
            if orientation.lower() == "x":
                # Derivative of hyperbola equation:
                # 2(x-h)/a² - 2(y-k)/b² * dy/dx = 0
                # Solve for dy/dx: dy/dx = b²(x-h)/(a²(y-k))
                if (
                    abs(p_y - k) < 1e-10
                ):  # This shouldn't happen for a hyperbola
                    return json.dumps(
                        {
                            "result": {
                                "message": f"The point ({p_x}, {p_y}) cannot"
                                f"be on the hyperbola with center"
                                f"({h}, {k}) and orientation 'x'."
                            }
                        }
                    )
                else:
                    tangent_slope = b**2 * (p_x - h) / (a**2 * (p_y - k))
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_eq_simplified = (
                        f"y = {float(tangent_slope)}x + "
                        f"{float(p_y - tangent_slope*p_x)}"
                    )
            else:  # orientation == "y"
                # Derivative of hyperbola equation:
                # -2(x-h)/b² + 2(y-k)/a² * dy/dx = 0
                # Solve for dy/dx: dy/dx = b²(x-h)/(a²(y-k))
                if (
                    abs(p_x - h) < 1e-10
                ):  # This shouldn't happen for a hyperbola
                    return json.dumps(
                        {
                            "result": {
                                "message": f"The point ({p_x}, {p_y}) cannot"
                                f"be on the hyperbola with center"
                                f"({h}, {k}) and orientation 'y'."
                            }
                        }
                    )
                else:
                    tangent_slope = a**2 * (p_y - k) / (b**2 * (p_x - h))
                    # y - y1 = m(x - x1)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_eq_simplified = (
                        f"y = {float(tangent_slope)}x + "
                        f"{float(p_y - tangent_slope*p_x)}"
                    )

            return json.dumps(
                {
                    "result": {
                        "tangent_line": tangent_eq,
                        "simplified_form": tangent_eq_simplified,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_tangent_line_at_point_hyperbola", e
            )

    # ====================== PROBLEM SOLVER LAYER ======================

    def compute_circle_area(self, radius: float) -> str:
        r"""Computes the area of a circle given its radius.

        Args:
            radius: The radius of the circle

        Returns:
            str: JSON string with the computed area
        """
        try:
            r = float(radius)
            area = sp.pi * r**2
            return json.dumps(
                {
                    "result": {
                        "area": str(float(area)),
                        "radius": r,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_circle_area", e)

    def compute_circle_circumference(self, radius: float) -> str:
        r"""Computes the circumference of a circle given its radius.

        Args:
            radius: The radius of the circle

        Returns:
            str: JSON string with the computed circumference
        """
        try:
            r = float(radius)
            circumference = 2 * sp.pi * r
            return json.dumps(
                {
                    "result": {
                        "circumference": str(float(circumference)),
                        "radius": r,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_circle_circumference", e)

    def check_point_position_on_circle(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> str:
        r"""Determines if a point is inside, on, or outside a circle.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle

        Returns:
            str: JSON string with the position ("inside", "on", or "outside")
        """
        try:
            px, py = float(point_x), float(point_y)
            cx, cy = float(center_x), float(center_y)
            r = float(radius)

            distance = sp.sqrt((px - cx) ** 2 + (py - cy) ** 2)

            if (
                abs(distance - r) < 1e-10
            ):  # Account for floating-point precision
                position = "on"
            elif distance < r:
                position = "inside"
            else:
                position = "outside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "distance_from_center": float(distance),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_on_circle", e)

    def compute_circle_line_intersection(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        line_slope: float,
        line_y_intercept: float,
    ) -> str:
        r"""Computes the intersection points of a circle and a line.

        Args:
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle
            line_slope: slope of the line (m in y = mx + b)
            line_y_intercept: y-intercept of the line (b in y = mx + b)

        Returns:
            str: JSON string with the intersection points
        """
        try:
            h, k = float(center_x), float(center_y)
            r = float(radius)
            m, b = float(line_slope), float(line_y_intercept)

            # Solve the system of equations:
            # Circle: (x - h)² + (y - k)² = r²
            # Line: y = mx + b

            # Substitute line equation into circle equation:
            # (x - h)² + (mx + b - k)² = r²

            # Expand:
            # x² - 2hx + h² + m²x² + 2mx(b-k) + (b-k)² = r²

            # Rearrange to standard form: Ax² + Bx + C = 0
            A = 1 + m**2
            B = 2 * (m * (b - k) - h)
            C = h**2 + (b - k) ** 2 - r**2

            # Calculate discriminant
            discriminant = B**2 - 4 * A * C

            if abs(discriminant) < 1e-10:  # One solution (tangent)
                x = -B / (2 * A)
                y = m * x + b

                return json.dumps(
                    {
                        "result": {
                            "intersection_points": [[float(x), float(y)]],
                            "count": 1,
                        }
                    }
                )

            elif discriminant < 0:  # No real solutions
                return json.dumps(
                    {
                        "result": {
                            "intersection_points": [],
                            "count": 0,
                        }
                    }
                )

            else:  # Two solutions
                x1 = (-B + sp.sqrt(discriminant)) / (2 * A)
                x2 = (-B - sp.sqrt(discriminant)) / (2 * A)

                y1 = m * x1 + b
                y2 = m * x2 + b

                return json.dumps(
                    {
                        "result": {
                            "intersection_points": [
                                [float(x1), float(y1)],
                                [float(x2), float(y2)],
                            ],
                            "count": 2,
                        }
                    }
                )
        except Exception as e:
            return self.handle_exception("compute_circle_line_intersection", e)

    def compute_circle_tangent_from_point(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> str:
        r"""Computes the tangent line(s) to a circle from an external point.

        Args:
            point_x: x-coordinate of the external point
            point_y: y-coordinate of the external point
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle

        Returns:
            str: JSON string with the tangent line equations
        """
        try:
            p_x, p_y = float(point_x), float(point_y)
            c_x, c_y = float(center_x), float(center_y)
            r = float(radius)

            # Calculate distance from point to center
            distance = sp.sqrt((p_x - c_x) ** 2 + (p_y - c_y) ** 2)

            # Check if point is inside the circle
            if distance < r:
                return json.dumps(
                    {
                        "result": {
                            "message": f"The point ({p_x}, {p_y}) is inside"
                            f"circle. No tangent can be drawn.",
                        }
                    }
                )

            # Check if point is on the circle
            if abs(distance - r) < 1e-10:
                # If point is on the circle, there's only one tangent line
                # (perpendicular to the radius)
                if (
                    abs(p_y - c_y) < 1e-10
                ):  # Point is directly to the right or left of center
                    tangent_eq = f"y = {p_y}"
                elif (
                    abs(p_x - c_x) < 1e-10
                ):  # Point is directly above or below center
                    tangent_eq = f"x = {p_x}"
                else:
                    # Slope of radius is (p_y - c_y)/(p_x - c_x)
                    # Slope of tangent is negative reciprocal:
                    # -(p_x - c_x)/(p_y - c_y)
                    tangent_slope = -(p_x - c_x) / (p_y - c_y)
                    tangent_eq = (
                        f"y - {p_y} = {float(tangent_slope)}(x - {p_x})"
                    )
                    # Simplify to y = mx + b form
                    tangent_eq_simplified = (
                        f"y = {float(tangent_slope)}x + "
                        f"{float(p_y - tangent_slope*p_x)}"
                    )

                return json.dumps(
                    {
                        "result": {
                            "tangent_lines": [tangent_eq],
                            "simplified_forms": [tangent_eq_simplified]
                            if 'tangent_eq_simplified' in locals()
                            else [],
                            "count": 1,
                        }
                    }
                )

            # Point is outside the circle
            # Use the power of a point theorem
            # The tangent points can be found using the formula

            # Calculate the tangent points using the formula
            # First, find the angle between the line from center to point
            # and the tangent lines
            cos_angle = r / distance
            sin_angle = sp.sqrt(1 - cos_angle**2)

            # Unit vector from center to point
            dx, dy = (p_x - c_x) / distance, (p_y - c_y) / distance

            # Calculate the tangent points by rotating the scaled unit vector
            t1_x = c_x + r * (dx * cos_angle - dy * sin_angle)
            t1_y = c_y + r * (dx * sin_angle + dy * cos_angle)

            t2_x = c_x + r * (dx * cos_angle + dy * sin_angle)
            t2_y = c_y + r * (dx * sin_angle - dy * cos_angle)

            # Calculate tangent line equations
            # Line through P and T1
            if abs(p_x - float(t1_x)) < 1e-10:  # Vertical line
                tangent1 = f"x = {p_x}"
                tangent1_simplified = tangent1
            else:
                m1 = (p_y - float(t1_y)) / (p_x - float(t1_x))
                b1 = p_y - m1 * p_x
                tangent1 = f"y - {p_y} = {float(m1)}(x - {p_x})"
                tangent1_simplified = f"y = {float(m1)}x + {float(b1)}"

            # Line through P and T2
            if abs(p_x - float(t2_x)) < 1e-10:  # Vertical line
                tangent2 = f"x = {p_x}"
                tangent2_simplified = tangent2
            else:
                m2 = (p_y - float(t2_y)) / (p_x - float(t2_x))
                b2 = p_y - m2 * p_x
                tangent2 = f"y - {p_y} = {float(m2)}(x - {p_x})"
                tangent2_simplified = f"y = {float(m2)}x + {float(b2)}"

            return json.dumps(
                {
                    "result": {
                        "tangent_lines": [tangent1, tangent2],
                        "simplified_forms": [
                            tangent1_simplified,
                            tangent2_simplified,
                        ],
                        "tangent_points": [
                            [float(t1_x), float(t1_y)],
                            [float(t2_x), float(t2_y)],
                        ],
                        "count": 2,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_circle_tangent_from_point", e
            )

    def compute_circle_equation(
        self, center_x: float, center_y: float, radius: float
    ) -> str:
        r"""Computes the equation of a circle in standard and general form.

        Args:
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle

        Returns:
            str: JSON string with the circle equations
        """
        try:
            h, k = float(center_x), float(center_y)
            r = float(radius)

            # Standard form: (x - h)² + (y - k)² = r²
            standard_form = f"(x - {h})² + (y - {k})² = {r}²"

            # General form: x² + y² + Dx + Ey + F = 0
            D = -2 * h
            E = -2 * k
            F = h**2 + k**2 - r**2

            general_form = f"x² + y² + {D}x + {E}y + {F} = 0"

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                        "center": [h, k],
                        "radius": r,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_circle_equation", e)

    def compute_circle_from_three_points(
        self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float
    ) -> str:
        r"""Computes the equation of a circle passing through three points.

        Args:
            x1: x-coordinate of the first point
            y1: y-coordinate of the first point
            x2: x-coordinate of the second point
            y2: y-coordinate of the second point
            x3: x-coordinate of the third point
            y3: y-coordinate of the third point

        Returns:
            str: JSON string with the circle equation
        """
        try:
            # Convert to float
            x1, y1 = float(x1), float(y1)
            x2, y2 = float(x2), float(y2)
            x3, y3 = float(x3), float(y3)

            # Check if points are collinear
            area = 0.5 * abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
            if abs(area) < 1e-10:
                return json.dumps(
                    {
                        "result": {
                            "message": "The three points are collinear."
                            "No circle can be constructed.",
                        }
                    }
                )

            # Set up the system of equations
            # For each point (x, y) on the circle: (x - h)² + (y - k)² = r²
            # Expanding: x² + y² - 2hx - 2ky + h² + k² - r² = 0
            # Let D = -2h, E = -2k, F = h² + k² - r²
            # Then: x² + y² + Dx + Ey + F = 0

            # For the three points, we get:
            # x₁² + y₁² + Dx₁ + Ey₁ + F = 0
            # x₂² + y₂² + Dx₂ + Ey₂ + F = 0
            # x₃² + y₃² + Dx₃ + Ey₃ + F = 0

            # Set up the matrix equation
            A = sp.Matrix([[x1, y1, 1], [x2, y2, 1], [x3, y3, 1]])

            b = sp.Matrix(
                [[-(x1**2 + y1**2)], [-(x2**2 + y2**2)], [-(x3**2 + y3**2)]]
            )

            # Solve for D, E, F
            solution = A.solve(b)
            D, E, F = solution[0], solution[1], solution[2]

            # Convert to center-radius form
            h = -D / 2
            k = -E / 2
            r = sp.sqrt(h**2 + k**2 - F)

            # Standard form: (x - h)² + (y - k)² = r²
            standard_form = (
                f"(x - {float(h)})² + (y - {float(k)})² = {float(r)}²"
            )

            # General form: x² + y² + Dx + Ey + F = 0
            general_form = (
                f"x² + y² + {float(D)}x + {float(E)}y + {float(F)} = 0"
            )

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                        "center": [float(h), float(k)],
                        "radius": float(r),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_circle_from_three_points", e)

    def compute_ellipse_area(
        self, semi_major: float, semi_minor: float
    ) -> str:
        r"""Computes the area of an ellipse given its semi-major
            and semi-minor axes.

        Args:
            semi_major: Length of the semi-major axis
            semi_minor: Length of the semi-minor axis

        Returns:
            str: JSON string with the computed area
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)
            area = sp.pi * a * b
            return json.dumps(
                {
                    "result": {
                        "area": str(float(area)),
                        "semi_major": a,
                        "semi_minor": b,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_ellipse_area", e)

    def compute_ellipse_perimeter_approximation(
        self, semi_major: float, semi_minor: float
    ) -> str:
        r"""Computes an approximation of the perimeter of an ellipse.

        Args:
            semi_major: Length of the semi-major axis
            semi_minor: Length of the semi-minor axis

        Returns:
            str: JSON string with the approximated perimeter
        """
        try:
            a = float(semi_major)
            b = float(semi_minor)

            # Ensure a > b
            if b > a:
                a, b = b, a

            # Ramanujan's approximation
            h = ((a - b) / (a + b)) ** 2
            perimeter = (
                sp.pi * (a + b) * (1 + 3 * h / (10 + sp.sqrt(4 - 3 * h)))
            )

            return json.dumps(
                {
                    "result": {
                        "perimeter": str(float(perimeter)),
                        "semi_major": a,
                        "semi_minor": b,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_ellipse_perimeter_approximation", e
            )

    def check_point_position_on_ellipse(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Determines if a point is inside, on, or outside an ellipse.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the position ("inside", "on", or "outside")
        """
        try:
            px, py = float(point_x), float(point_y)
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Ensure a > b
            if b > a:
                a, b = b, a
                # Adjust orientation if we swapped a and b
                orientation = "y" if orientation.lower() == "x" else "x"

            # Evaluate the ellipse equation at the point
            if orientation.lower() == "x":
                # (x-h)²/a² + (y-k)²/b² = 1
                value = ((px - h) ** 2 / a**2) + ((py - k) ** 2 / b**2)
            else:  # orientation == "y"
                # (x-h)²/b² + (y-k)²/a² = 1
                value = ((px - h) ** 2 / b**2) + ((py - k) ** 2 / a**2)

            if abs(value - 1) < 1e-10:  # Account for floating-point precision
                position = "on"
            elif value < 1:
                position = "inside"
            else:
                position = "outside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "equation_value": float(value),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_on_ellipse", e)

    def compute_ellipse_equation(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the equation of an ellipse in standard and general form.

        Args:
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis

        Returns:
            str: JSON string with the ellipse equations
        """
        try:
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Ensure a > b
            if b > a:
                a, b = b, a
                # Adjust orientation if we swapped a and b
                orientation = "y" if orientation.lower() == "x" else "x"

            # Standard form
            if orientation.lower() == "x":
                standard_form = f"(x - {h})²/{a}² + (y - {k})²/{b}² = 1"

                # General form: Ax² + By² + Cx + Dy + E = 0
                A = b**2
                B = a**2
                C = -2 * h * b**2
                D = -2 * k * a**2
                E = (h**2 * b**2) + (k**2 * a**2) - (a**2 * b**2)

                general_form = f"{A}x² + {B}y² + {C}x + {D}y + {E} = 0"
            else:  # orientation == "y"
                standard_form = f"(x - {h})²/{b}² + (y - {k})²/{a}² = 1"

                # General form: Ax² + By² + Cx + Dy + E = 0
                A = a**2
                B = b**2
                C = -2 * h * a**2
                D = -2 * k * b**2
                E = (h**2 * a**2) + (k**2 * b**2) - (a**2 * b**2)

                general_form = f"{A}x² + {B}y² + {C}x + {D}y + {E} = 0"

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                        "center": [h, k],
                        "semi_major": a,
                        "semi_minor": b,
                        "orientation": orientation,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_ellipse_equation", e)

    ### PARABOLA ###

    def compute_parabola_axis_of_symmetry(
        self, vertex_x: float, vertex_y: float, orientation: str
    ) -> str:
        r"""Computes the axis of symmetry of a parabola.

        Args:
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            orientation: direction the parabola opens -
                        "up", "down", "left", or "right"

        Returns:
            str: JSON string with the axis of symmetry equation
        """
        try:
            h = float(vertex_x)
            k = float(vertex_y)

            # Calculate axis of symmetry equation
            if orientation.lower() in ["right", "left"]:
                axis = f"y = {k}"
            else:  # orientation in ["up", "down"]
                axis = f"x = {h}"

            return json.dumps(
                {
                    "result": {
                        "axis_of_symmetry": axis,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_parabola_axis_of_symmetry", e
            )

    def check_point_position_on_parabola(
        self,
        point_x: float,
        point_y: float,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Determines if a point is on, inside, or outside a parabola.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens -
                        "up", "down", "left", or "right"

        Returns:
            str: JSON string with the position ("on", "inside", or "outside")
        """
        try:
            px, py = float(point_x), float(point_y)
            h, k = float(vertex_x), float(vertex_y)
            a = float(coefficient)

            # Evaluate the parabola equation at the point
            if orientation.lower() == "right":
                # y - k = a(x - h)²
                expected_y = k + a * (px - h) ** 2
                if abs(py - expected_y) < 1e-10:
                    position = "on"
                elif (px > h and py > expected_y) or (
                    px > h and py < expected_y
                ):
                    position = "outside"
                else:
                    position = "inside"

            elif orientation.lower() == "left":
                # y - k = a(x - h)²
                expected_y = k + a * (px - h) ** 2
                if abs(py - expected_y) < 1e-10:
                    position = "on"
                elif (px < h and py > expected_y) or (
                    px < h and py < expected_y
                ):
                    position = "outside"
                else:
                    position = "inside"

            elif orientation.lower() == "up":
                # x - h = a(y - k)²
                expected_x = h + a * (py - k) ** 2
                if abs(px - expected_x) < 1e-10:
                    position = "on"
                elif (py > k and px > expected_x) or (
                    py > k and px < expected_x
                ):
                    position = "outside"
                else:
                    position = "inside"

            else:  # orientation == "down"
                # x - h = a(y - k)²
                expected_x = h + a * (py - k) ** 2
                if abs(px - expected_x) < 1e-10:
                    position = "on"
                elif (py < k and px > expected_x) or (
                    py < k and px < expected_x
                ):
                    position = "outside"
                else:
                    position = "inside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("check_point_position_on_parabola", e)

    def compute_parabola_equation(
        self,
        vertex_x: float,
        vertex_y: float,
        coefficient: float,
        orientation: str,
    ) -> str:
        r"""Computes the equation of a parabola in vertex and standard form.

        Args:
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens -
                        "up", "down", "left", or "right"

        Returns:
            str: JSON string with the parabola equations
        """
        try:
            h = float(vertex_x)
            k = float(vertex_y)
            a = float(coefficient)

            # Calculate vertex form
            if orientation.lower() == "right":
                vertex_form = f"y - {k} = {a}(x - {h})²"
                # Expand to standard form: y = ax² + bx + c
                standard_form = f"y = {a}x² + {-2*a*h}x + {a*h**2 + k}"

            elif orientation.lower() == "left":
                vertex_form = f"y - {k} = {a}(x - {h})²"
                # Expand to standard form: y = ax² + bx + c
                standard_form = f"y = {a}x² + {-2*a*h}x + {a*h**2 + k}"

            elif orientation.lower() == "up":
                vertex_form = f"x - {h} = {a}(y - {k})²"
                # Expand to standard form: x = ay² + by + c
                standard_form = f"x = {a}y² + {-2*a*k}y + {a*k**2 + h}"

            else:  # orientation == "down"
                vertex_form = f"x - {h} = {a}(y - {k})²"
                # Expand to standard form: x = ay² + by + c
                standard_form = f"x = {a}y² + {-2*a*k}y + {a*k**2 + h}"

            return json.dumps(
                {
                    "result": {
                        "vertex_form": vertex_form,
                        "standard_form": standard_form,
                        "vertex": [h, k],
                        "coefficient": a,
                        "orientation": orientation,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_parabola_equation", e)

    def compute_parabola_from_focus_directrix(
        self,
        focus_x: float,
        focus_y: float,
        directrix_type: str,
        directrix_value: float,
    ) -> str:
        r"""Computes the equation of a parabola given its focus and directrix.

        Args:
            focus_x: x-coordinate of the focus
            focus_y: y-coordinate of the focus
            directrix_type: "horizontal" for y = k or "vertical" for x = h
            directrix_value: the value k or h in the directrix equation

        Returns:
            str: JSON string with the parabola equation
        """
        try:
            f_x, f_y = float(focus_x), float(focus_y)
            d_val = float(directrix_value)

            # Determine orientation and vertex
            if directrix_type.lower() == "horizontal":
                # Directrix is y = d_val
                # Parabola opens up if focus is above directrix, down if below
                orientation = "up" if f_y > d_val else "down"

                # Vertex is halfway between focus and directrix
                vertex_y = (f_y + d_val) / 2
                vertex_x = f_x

                # Calculate coefficient
                p = abs(f_y - d_val) / 2
                a = 1 / (4 * p)

                if orientation == "down":
                    a = -a

            else:  # directrix_type == "vertical"
                # Directrix is x = d_val
                # Parabola opens right if focus is to the right of directrix,
                # left if to the left
                orientation = "right" if f_x > d_val else "left"

                # Vertex is halfway between focus and directrix
                vertex_x = (f_x + d_val) / 2
                vertex_y = f_y

                # Calculate coefficient
                p = abs(f_x - d_val) / 2
                a = 1 / (4 * p)

                if orientation == "left":
                    a = -a

            # Calculate equation
            if orientation in ["up", "down"]:
                vertex_form = f"x - {vertex_x} = {a}(y - {vertex_y})²"
                # Expand to standard form: x = ay² + by + c
                b = -2 * a * vertex_y
                c = a * vertex_y**2 + vertex_x
                standard_form = f"x = {a}y² + {b}y + {c}"
            else:  # orientation in ["right", "left"]
                vertex_form = f"y - {vertex_y} = {a}(x - {vertex_x})²"
                # Expand to standard form: y = ax² + bx + c
                b = -2 * a * vertex_x
                c = a * vertex_x**2 + vertex_y
                standard_form = f"y = {a}x² + {b}x + {c}"

            return json.dumps(
                {
                    "result": {
                        "vertex_form": vertex_form,
                        "standard_form": standard_form,
                        "vertex": [vertex_x, vertex_y],
                        "coefficient": a,
                        "orientation": orientation,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "compute_parabola_from_focus_directrix", e
            )

    ### HYPERBOLA ###

    def compute_hyperbola_vertices(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        orientation: str,
    ) -> str:
        r"""Computes the vertices of a hyperbola.

        Args:
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            orientation: "x" if transverse axis is along x-axis,
                         "y" if along y-axis

        Returns:
            str: JSON string with the vertex coordinates
        """
        try:
            h, k = float(center_x), float(center_y)
            a = float(semi_major)

            # Calculate vertices
            if orientation.lower() == "x":
                vertex1 = [h + a, k]
                vertex2 = [h - a, k]
            else:  # orientation == "y"
                vertex1 = [h, k + a]
                vertex2 = [h, k - a]

            return json.dumps(
                {
                    "result": {
                        "vertices": [vertex1, vertex2],
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_hyperbola_vertices", e)

    def compute_hyperbola_co_vertices(
        self,
        center_x: float,
        center_y: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the co-vertices of a hyperbola.

        Args:
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                         "y" if along y-axis

        Returns:
            str: JSON string with the co-vertex coordinates
        """
        try:
            h, k = float(center_x), float(center_y)
            b = float(semi_minor)

            # Calculate co-vertices
            if orientation.lower() == "x":
                co_vertex1 = [h, k + b]
                co_vertex2 = [h, k - b]
            else:  # orientation == "y"
                co_vertex1 = [h + b, k]
                co_vertex2 = [h - b, k]

            return json.dumps(
                {
                    "result": {
                        "co_vertices": [co_vertex1, co_vertex2],
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_hyperbola_co_vertices", e)

    def check_point_position_on_hyperbola(
        self,
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Determines if a point is on, inside, or outside a hyperbola.

        Args:
            point_x: x-coordinate of the point
            point_y: y-coordinate of the point
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                         "y" if along y-axis

        Returns:
            str: JSON string with the position ("on", "inside", or "outside")
        """
        try:
            px, py = float(point_x), float(point_y)
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Evaluate the hyperbola equation at the point
            if orientation.lower() == "x":
                # (x-h)²/a² - (y-k)²/b² = 1
                value = ((px - h) ** 2 / a**2) - ((py - k) ** 2 / b**2)
            else:  # orientation == "y"
                # (y-k)²/a² - (x-h)²/b² = 1
                value = ((py - k) ** 2 / a**2) - ((px - h) ** 2 / b**2)

            if abs(value - 1) < 1e-10:  # Account for floating-point precision
                position = "on"
            elif value > 1:
                position = "inside"
            else:
                position = "outside"

            return json.dumps(
                {
                    "result": {
                        "position": position,
                        "equation_value": float(value),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception(
                "check_point_position_on_hyperbola", e
            )

    def compute_hyperbola_equation(
        self,
        center_x: float,
        center_y: float,
        semi_major: float,
        semi_minor: float,
        orientation: str,
    ) -> str:
        r"""Computes the equation of a hyperbola in standard and general form.

        Args:
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                         "y" if along y-axis

        Returns:
            str: JSON string with the hyperbola equations
        """
        try:
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            # Standard form
            if orientation.lower() == "x":
                standard_form = f"(x - {h})²/{a}² - (y - {k})²/{b}² = 1"

                # General form: Ax² + By² + Cx + Dy + E = 0
                A = b**2
                B = -(a**2)
                C = -2 * h * b**2
                D = 2 * k * a**2
                E = (h**2 * b**2) - (k**2 * a**2) - (a**2 * b**2)

                general_form = f"{A}x² + {B}y² + {C}x + {D}y + {E} = 0"
            else:  # orientation == "y"
                standard_form = f"(y - {k})²/{a}² - (x - {h})²/{b}² = 1"

                # General form: Ax² + By² + Cx + Dy + E = 0
                A = -(a**2)
                B = b**2
                C = 2 * h * a**2
                D = -2 * k * b**2
                E = (k**2 * b**2) - (h**2 * a**2) - (a**2 * b**2)

                general_form = f"{A}x² + {B}y² + {C}x + {D}y + {E} = 0"

            return json.dumps(
                {
                    "result": {
                        "standard_form": standard_form,
                        "general_form": general_form,
                        "center": [h, k],
                        "semi_major": a,
                        "semi_minor": b,
                        "orientation": orientation,
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_hyperbola_equation", e)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of available tools in the toolkit.
        """
        return [
            # Core geometric functions
            FunctionTool(self.compute_distance),
            FunctionTool(self.compute_distance_point_to_line),
            FunctionTool(self.compute_vector_operations),
            FunctionTool(self.compute_area_triangle_vertices),
            FunctionTool(self.compute_area_triangle_sides),
            FunctionTool(self.compute_area_polygon),
            FunctionTool(self.compute_midpoint),
            FunctionTool(self.compute_line_bisector),
            FunctionTool(self.check_points_collinear),
            # Conic section helpers
            FunctionTool(self.identify_conic_section_type),
            FunctionTool(self.parse_circle_equation),
            FunctionTool(self.parse_ellipse_equation),
            FunctionTool(self.parse_hyperbola_equation),
            FunctionTool(self.parse_parabola_equation),
            FunctionTool(self.solve_quadratic),
            FunctionTool(self.generate_circle_equation),
            FunctionTool(self.generate_ellipse_equation),
            FunctionTool(self.generate_parabola_equation),
            FunctionTool(self.generate_hyperbola_equation),
            # Conic property calculators
            FunctionTool(self.compute_circle_properties),
            FunctionTool(self.compute_ellipse_properties),
            FunctionTool(self.compute_parabola_properties),
            FunctionTool(self.compute_hyperbola_properties),
            FunctionTool(self.compute_circle_eccentricity),
            FunctionTool(self.compute_ellipse_eccentricity),
            FunctionTool(self.compute_parabola_eccentricity),
            FunctionTool(self.compute_hyperbola_eccentricity),
            FunctionTool(self.compute_circle_foci),
            FunctionTool(self.compute_ellipse_foci),
            FunctionTool(self.compute_parabola_foci),
            FunctionTool(self.compute_hyperbola_foci),
            FunctionTool(self.compute_circle_directrix),
            FunctionTool(self.compute_ellipse_directrices),
            FunctionTool(self.compute_parabola_directrix),
            FunctionTool(self.compute_hyperbola_directrices),
            FunctionTool(self.compute_circle_asymptotes),
            FunctionTool(self.compute_ellipse_asymptotes),
            FunctionTool(self.compute_parabola_asymptotes),
            FunctionTool(self.compute_hyperbola_asymptotes),
            # Geometric operations
            FunctionTool(self.compute_line_circle_intersection),
            FunctionTool(self.compute_line_ellipse_intersection),
            FunctionTool(self.compute_line_parabola_intersection),
            FunctionTool(self.compute_line_hyperbola_intersection),
            FunctionTool(self.check_point_position_circle),
            FunctionTool(self.check_point_position_ellipse),
            FunctionTool(self.check_point_position_parabola),
            FunctionTool(self.check_point_position_hyperbola),
            FunctionTool(self.compute_tangent_line_circle),
            FunctionTool(self.compute_tangent_line_at_point_circle),
            FunctionTool(self.compute_tangent_line_at_point_ellipse),
            FunctionTool(self.compute_tangent_line_at_point_parabola),
            FunctionTool(self.compute_tangent_line_at_point_hyperbola),
            # Circle Solver
            FunctionTool(self.compute_circle_area),
            FunctionTool(self.compute_circle_circumference),
            FunctionTool(self.check_point_position_on_circle),
            FunctionTool(self.compute_circle_line_intersection),
            FunctionTool(self.compute_circle_tangent_from_point),
            FunctionTool(self.compute_circle_equation),
            FunctionTool(self.compute_circle_from_three_points),
            # Ellipse Solver
            FunctionTool(self.compute_ellipse_area),
            FunctionTool(self.compute_ellipse_perimeter_approximation),
            FunctionTool(self.check_point_position_on_ellipse),
            FunctionTool(self.compute_ellipse_equation),
            # Parabola Solver
            FunctionTool(self.compute_parabola_axis_of_symmetry),
            FunctionTool(self.check_point_position_on_parabola),
            FunctionTool(self.compute_parabola_equation),
            FunctionTool(self.compute_parabola_from_focus_directrix),
            # Hyperbola Solver
            FunctionTool(self.compute_hyperbola_vertices),
            FunctionTool(self.compute_hyperbola_co_vertices),
            FunctionTool(self.check_point_position_on_hyperbola),
            FunctionTool(self.compute_hyperbola_equation),
        ]
