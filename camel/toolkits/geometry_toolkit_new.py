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
                return json.dumps(
                    {
                        "result": {
                            "distance": str(float(distance)),
                            "note": (
                                "The line is defined by two identical points, "
                                "so this is the distance to that point."
                            ),
                        }
                    }
                )

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

            return json.dumps(
                {
                    "result": {
                        "distance": str(float(distance)),
                        "line_equation": f"{A}x + {B}y + {C} = 0",
                    }
                }
            )
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
        """Computes the area of a triangle given its vertices.

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

            return json.dumps(
                {
                    "result": {
                        "area": str(area),
                        "vertices": [[x1, y1], [x2, y2], [x3, y3]],
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_area_triangle_vertices", e)

    def compute_area_triangle_sides(
        self, side1: float, side2: float, side3: float
    ) -> str:
        """Computes the area of a triangle given its side lengths.

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

            return json.dumps(
                {
                    "result": {
                        "area": str(area),
                        "sides": [a, b, c],
                        "semi_perimeter": str(s),
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_area_triangle_sides", e)

    def compute_area_polygon(self, vertices: List[List[float]]) -> str:
        """Computes the area of a polygon given its vertices.

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

            return json.dumps(
                {
                    "result": {
                        "area": str(area),
                        "vertices": vertices,
                        "vertex_count": len(vertices),
                    }
                }
            )
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

    def parse_conic_equation_new(self, problem_statement: str) -> str:
        r"""Parses a complete conic section problem statement and
            identifies components.

        Args:
            problem_statement: Full problem statement as a string

        Returns:
            str: JSON string with problem type, conic type, parameters,
                and conditions
        """
        try:
            self.logger.info(f"Parsing conic problem: {problem_statement}")

            # Initialize result structure
            result = {
                "problem_type": "",
                "conic_type": "",
                "parameters": {},
                "conditions": [],
                "variables": [],
                "equations": [],
            }

            # Split the problem statement into components
            # Look for common delimiters in math problems
            parts = problem_statement.lower().replace(".", ". ").split(". ")

            # Extract equations from the problem statement
            equations = []
            equation_pattern = r'([^=]+=[^=,;]+)'
            for part in parts:
                import re

                eq_matches = re.findall(equation_pattern, part)
                equations.extend(eq_matches)

            # Identify the main conic equation
            main_equation = ""
            for eq in equations:
                # Look for conic equation patterns
                if ('x²' in eq or 'x^2' in eq or 'x**2' in eq) and (
                    'y²' in eq or 'y^2' in eq or 'y**2' in eq
                ):
                    main_equation = eq
                    break

            # If no clear conic equation found, try the first equation
            if not main_equation and equations:
                main_equation = equations[0]

            # Parse the main conic equation
            if main_equation:
                # Standardize equation format
                main_equation = main_equation.replace('^2', '²').replace(
                    '**2', '²'
                )
                conic_result = json.loads(
                    self.parse_conic_equation(main_equation)
                )
                result["conic_type"] = conic_result["type"]
                result["parameters"] = conic_result["parameters"]
                if isinstance(result["equations"], list):
                    result["equations"].append(
                        {"type": "main_conic", "equation": main_equation}
                    )

            # Identify problem type
            if "find" in problem_statement.lower():
                result["problem_type"] = "find_parameter_from_condition"

                # Extract the variable to find
                find_pattern = r'find\s+([a-zA-Z0-9]+)'
                import re

                find_match = re.search(find_pattern, problem_statement.lower())
                if find_match:
                    variable = find_match.group(1)
                    if isinstance(result["variables"], list):
                        result["variables"].append(
                            {"name": variable, "to_solve": True}
                        )

            # Identify conditions
            condition_keywords = {
                "asymptote": "asymptote_condition",
                "tangent": "tangent_condition",
                "passes through": "point_condition",
                "intersect": "intersection_condition",
                "focus": "focus_condition",
                "directrix": "directrix_condition",
                "eccentricity": "eccentricity_condition",
            }

            for keyword, condition_type in condition_keywords.items():
                if keyword in problem_statement.lower():
                    # Extract the condition details
                    condition = {"type": condition_type}

                    # For asymptotes
                    if condition_type == "asymptote_condition":
                        # Look for asymptote equation
                        for eq in equations:
                            if eq != main_equation and (
                                'x' in eq or 'y' in eq
                            ):
                                # This might be an asymptote equation
                                condition["equation"] = eq

                                # Try to extract slope if it's a line
                                if 'y' in eq and '=' in eq:
                                    try:
                                        # Parse y = mx + b format
                                        right_side = eq.split('=')[1].strip()
                                        if 'x' in right_side:
                                            # Extract coefficient of x as slope
                                            x_term = right_side.split('x')[
                                                0
                                            ].strip()
                                            if x_term:
                                                if x_term == '-':
                                                    slope = -1.0
                                                else:
                                                    slope = float(
                                                        x_term.replace('+', '')
                                                    )
                                                if isinstance(condition, dict):
                                                    condition["slope"] = str(
                                                        slope
                                                    )
                                                # Update problem type
                                                if (
                                                    isinstance(result, dict)
                                                    and "problem_type"
                                                    in result
                                                ):
                                                    result["problem_type"] = (
                                                        "find_parameter_from_"
                                                        "condition"
                                                    )
                                                if (
                                                    isinstance(result, dict)
                                                    and "condition_type"
                                                    in result
                                                ):
                                                    result[
                                                        "condition_type"
                                                    ] = "asymptote_" "slope"
                                    except Exception:
                                        pass
                                break

                    # For points
                    elif condition_type == "point_condition":
                        # Look for point coordinates
                        point_pattern = r'\(([^)]+)\)'
                        import re

                        point_matches = re.findall(
                            point_pattern, problem_statement
                        )
                        if point_matches:
                            try:
                                points = []
                                for point_str in point_matches:
                                    coords = point_str.split(',')
                                    if len(coords) == 2:
                                        x = float(coords[0].strip())
                                        y = float(coords[1].strip())
                                        points.append([x, y])
                                if points and isinstance(condition, dict):
                                    condition["points"] = str(points)
                            except Exception:
                                pass

                    # For eccentricity
                    elif condition_type == "eccentricity_condition":
                        # Look for eccentricity value
                        ecc_pattern = r'eccentricity\s+(?:is|=)\s+([0-9.]+)'
                        import re

                        ecc_match = re.search(
                            ecc_pattern, problem_statement.lower()
                        )
                        if ecc_match:
                            try:
                                eccentricity = float(ecc_match.group(1))
                                if isinstance(condition, dict):
                                    condition["eccentricity"] = str(
                                        eccentricity
                                    )
                                if (
                                    isinstance(result, dict)
                                    and "problem_type" in result
                                ):
                                    result["problem_type"] = (
                                        "find_parameter_from_condition"
                                    )
                                if (
                                    isinstance(result, dict)
                                    and "condition_type" in result
                                ):
                                    result["condition_type"] = "eccentricity"
                            except Exception:
                                pass

                    # For focus
                    elif condition_type == "focus_condition":
                        # Look for focus coordinates or distance
                        focus_pattern = r'focus\s+(?:at|is)\s+\(([^)]+)\)'
                        import re

                        focus_match = re.search(
                            focus_pattern, problem_statement.lower()
                        )
                        if focus_match:
                            try:
                                coords = focus_match.group(1).split(',')
                                if len(coords) == 2:
                                    x = float(coords[0].strip())
                                    y = float(coords[1].strip())
                                    if isinstance(condition, dict):
                                        condition["focus"] = str([x, y])
                            except Exception:
                                pass

                        # Look for focus distance
                        distance_pattern = (
                            r'focus\s+(?:is|at)\s+([0-9.]+)\s+(?:units|unit)'
                        )
                        distance_match = re.search(
                            distance_pattern, problem_statement.lower()
                        )
                        if distance_match:
                            try:
                                distance = float(distance_match.group(1))
                                if isinstance(condition, dict):
                                    condition["focus_distance"] = str(distance)
                                if (
                                    isinstance(result, dict)
                                    and "problem_type" in result
                                ):
                                    result["problem_type"] = (
                                        "find_parameter_from_condition"
                                    )
                                if (
                                    isinstance(result, dict)
                                    and "condition_type" in result
                                ):
                                    result["condition_type"] = "focus_distance"
                            except Exception:
                                pass

                    # For directrix
                    elif condition_type == "directrix_condition":
                        # Look for directrix equation
                        for eq in equations:
                            if eq != main_equation and (
                                'x' in eq or 'y' in eq
                            ):
                                # This might be a directrix equation
                                if 'x =' in eq or 'x=' in eq:
                                    # Vertical directrix
                                    try:
                                        x_val = float(eq.split('=')[1].strip())
                                        if isinstance(condition, dict):
                                            condition["directrix"] = str(
                                                {
                                                    "type": "vertical",
                                                    "x": x_val,
                                                }
                                            )
                                    except ValueError:
                                        if isinstance(condition, dict):
                                            condition["directrix_equation"] = (
                                                eq
                                            )
                                    except TypeError:
                                        if isinstance(condition, dict):
                                            condition["directrix_equation"] = (
                                                eq
                                            )
                                    except Exception as e:
                                        if isinstance(condition, dict):
                                            condition["directrix_equation"] = (
                                                eq
                                            )
                                        self.logger.warning(
                                            f"Unexpected error parsing"
                                            f"directrix:{e}"
                                        )
                                elif 'y =' in eq or 'y=' in eq:
                                    # Horizontal directrix
                                    try:
                                        y_val = float(eq.split('=')[1].strip())
                                        if isinstance(condition, dict):
                                            condition["directrix"] = str(
                                                {
                                                    "type": "horizontal",
                                                    "y": y_val,
                                                }
                                            )
                                    except Exception:
                                        if isinstance(condition, dict):
                                            condition["directrix_equation"] = (
                                                eq
                                            )
                                break

                    # For tangent lines
                    elif condition_type == "tangent_condition":
                        # Look for tangent point or equation
                        point_pattern = (
                            r'tangent\s+(?:at|through)\s+\(([^)]+)\)'
                        )
                        import re

                        point_match = re.search(
                            point_pattern, problem_statement.lower()
                        )
                        if point_match:
                            try:
                                coords = point_match.group(1).split(',')
                                if len(coords) == 2:
                                    x = float(coords[0].strip())
                                    y = float(coords[1].strip())
                                    if isinstance(condition, dict):
                                        condition["tangent_point"] = str(
                                            [x, y]
                                        )
                            except Exception:
                                pass

                        # Look for tangent equation
                        for eq in equations:
                            if eq != main_equation and (
                                'x' in eq or 'y' in eq
                            ):
                                # This might be a tangent line equation
                                if (
                                    'tangent' in problem_statement.lower()
                                    and eq
                                    not in [
                                        c.get("equation", "")
                                        if isinstance(c, dict)
                                        else ""
                                        for c in result["conditions"]
                                        if isinstance(
                                            result["conditions"], list
                                        )
                                    ]
                                ):
                                    if isinstance(condition, dict):
                                        condition["tangent_equation"] = eq
                                    break

                    # For intersection conditions
                    elif condition_type == "intersection_condition":
                        # Look for the second curve equation
                        for eq in equations:
                            if eq != main_equation and eq not in [
                                c.get("equation", "")
                                if isinstance(c, dict)
                                else ""
                                for c in (
                                    result.get("conditions", [])
                                    if isinstance(result, dict)
                                    else []
                                )
                            ]:
                                # This might be the second curve
                                if isinstance(condition, dict):
                                    condition["second_curve_equation"] = eq

                                # Try to determine the type of the second curve
                                if ('x²' in eq or 'x^2' in eq) and (
                                    'y²' in eq or 'y^2' in eq
                                ):
                                    if isinstance(condition, dict):
                                        condition["second_curve_type"] = (
                                            "conic"
                                        )
                                elif ('x²' in eq or 'x^2' in eq) or (
                                    'y²' in eq or 'y^2' in eq
                                ):
                                    if isinstance(condition, dict):
                                        condition["second_curve_type"] = (
                                            "parabola"
                                        )
                                elif 'x' in eq and 'y' in eq:
                                    if isinstance(condition, dict):
                                        condition["second_curve_type"] = "line"

                                # Look for intersection count
                                count_pattern = (
                                    r'intersect\s+(?:at|in)\s+([0-9]+)\s+point'
                                )
                                import re

                                count_match = re.search(
                                    count_pattern, problem_statement.lower()
                                )
                                if count_match:
                                    try:
                                        count = int(count_match.group(1))
                                        if isinstance(condition, dict):
                                            condition["intersection_count"] = (
                                                str(count)
                                            )
                                        if (
                                            isinstance(result, dict)
                                            and "problem_type" in result
                                        ):
                                            result["problem_type"] = (
                                                "find_parameter_from_condition"
                                            )
                                        if (
                                            isinstance(result, dict)
                                            and "condition_type" in result
                                        ):
                                            result["condition_type"] = (
                                                "intersection_count"
                                            )
                                    except Exception:
                                        pass
                                break

                    if isinstance(result["conditions"], list) and isinstance(
                        condition, dict
                    ):
                        result["conditions"].append(condition)

            # Check for variables in the conic equation parameters
            if isinstance(result["parameters"], dict):
                for param_name, param_value in result["parameters"].items():
                    if isinstance(param_value, str) and param_value.isalpha():
                        # This parameter contains a variable
                        if isinstance(result["variables"], list):
                            result["variables"].append(
                                {
                                    "name": param_value,
                                    "parameter": param_name,
                                    "to_solve": True,
                                }
                            )

            # If we have a hyperbola with an asymptote condition and a variable
            if (
                result["conic_type"] == "hyperbola"
                and any(
                    c["type"] == "asymptote_condition"
                    if isinstance(c, dict)
                    else False
                    for c in result["conditions"]
                    if isinstance(result["conditions"], list)
                )
                and result["variables"]
            ):
                result["problem_type"] = "find_parameter_from_condition"
                result["condition_type"] = "asymptote_slope"

            # If we have an ellipse with eccentricity condition and variable
            elif (
                result["conic_type"] == "ellipse"
                and any(
                    c["type"] == "eccentricity_condition"
                    if isinstance(c, dict)
                    else False
                    for c in result["conditions"]
                    if isinstance(result["conditions"], list)
                )
                and result["variables"]
            ):
                result["problem_type"] = "find_parameter_from_condition"
                if isinstance(result, dict) and "condition_type" in result:
                    result["condition_type"] = "eccentricity"

            # If we have parabola with a focus condition and a variable
            elif (
                result["conic_type"] == "parabola"
                and any(
                    c["type"] == "focus_condition"
                    if isinstance(c, dict)
                    else False
                    for c in result["conditions"]
                    if isinstance(result["conditions"], list)
                )
                and result["variables"]
            ):
                result["problem_type"] = "find_parameter_from_condition"
                if isinstance(result, dict) and "condition_type" in result:
                    result["condition_type"] = "focus_distance"

            # If we have any conic with a point condition and a variable
            elif (
                any(
                    c["type"] == "point_condition"
                    if isinstance(c, dict)
                    else False
                    for c in result["conditions"]
                    if isinstance(result["conditions"], list)
                )
                and result["variables"]
            ):
                result["problem_type"] = "find_parameter_from_condition"
                if isinstance(result["condition_type"], str):
                    result["condition_type"] = "point_on_curve"

            # If we have any conic with intersection condition and variable
            elif (
                any(
                    c["type"] == "intersection_condition"
                    if isinstance(c, dict)
                    else False
                    for c in result["conditions"]
                    if isinstance(result["conditions"], list)
                )
                and result["variables"]
            ):
                result["problem_type"] = "find_parameter_from_condition"
                if isinstance(result["condition_type"], str):
                    result["condition_type"] = "intersection_count"

            return json.dumps(result)
        except Exception as e:
            return self.handle_exception("parse_conic_problem", e)

    def parse_conic_equation(self, equation: str) -> str:
        r"""Parses a conic section equation and identifies
            its type and parameters.

        Args:
            equation: String representation of the conic equation

        Returns:
            str: JSON string with conic type and parameters
        """
        try:
            self.logger.info(f"Parsing conic equation: {equation}")

            # Convert the equation string to a SymPy expression
            x, y = sp.symbols('x y')

            # Remove any "= 0" or "= C" part and
            # move everything to the left side
            if '=' in equation:
                left_side, right_side = equation.split('=', 1)
                equation = f"({left_side}) - ({right_side})"

            expr = sp.sympify(equation)

            # Expand the expression to get the general form
            expr = sp.expand(expr)

            # Extract coefficients of the general form:
            # Ax² + Bxy + Cy² + Dx + Ey + F = 0
            coeff_x2 = expr.coeff(x, 2)
            coeff_xy = expr.coeff(x, 1).coeff(y, 1)
            coeff_y2 = expr.coeff(y, 2)
            coeff_x = expr.coeff(x, 1).subs(y, 0)
            coeff_y = expr.coeff(y, 1).subs(x, 0)
            coeff_const = expr.subs({x: 0, y: 0})

            # Determine the type of conic section based on the coefficients
            A, B, C = coeff_x2, coeff_xy, coeff_y2
            D, E, F = coeff_x, coeff_y, coeff_const

            # Calculate the discriminant
            discriminant = B**2 - 4 * A * C

            # Determine conic type based on discriminant
            conic_type = ""
            parameters = {}

            if discriminant.is_zero:
                # Parabola or degenerate cases
                if (
                    (A.is_zero and C.is_zero)
                    or (A.is_zero and B.is_zero)
                    or (B.is_zero and C.is_zero)
                ):
                    if not (A.is_zero and C.is_zero):
                        conic_type = "parabola"
                    else:
                        conic_type = "degenerate"
                else:
                    conic_type = "parabola"
            elif discriminant > 0:
                # Hyperbola
                conic_type = "hyperbola"
            else:  # discriminant < 0
                # Ellipse or circle
                if A == C and B.is_zero:
                    conic_type = "circle"
                else:
                    conic_type = "ellipse"

            # Store the coefficients in the parameters
            parameters = {
                "A": float(A) if not A.is_symbol else str(A),
                "B": float(B) if not B.is_symbol else str(B),
                "C": float(C) if not C.is_symbol else str(C),
                "D": float(D) if not D.is_symbol else str(D),
                "E": float(E) if not E.is_symbol else str(E),
                "F": float(F) if not F.is_symbol else str(F),
                "discriminant": float(discriminant)
                if not discriminant.is_symbol
                else str(discriminant),
            }

            # For standard forms, extract additional parameters
            if conic_type == "circle":
                # For a circle: (x-h)² + (y-k)² = r²
                # Rewrite as: x² + y² - 2hx - 2ky + (h² + k² - r²) = 0
                # So: A=1, C=1, D=-2h, E=-2k, F=h²+k²-r²
                h = -D / (2 * A)
                k = -E / (2 * C)
                r_squared = (D**2 + E**2) / (4 * A) - F
                r = sp.sqrt(r_squared) if r_squared >= 0 else None

                parameters.update(
                    {
                        "center": str([float(h), float(k)]),
                        "radius": str(float(r)) if r is not None else "",
                    }
                )

            elif conic_type == "ellipse":
                # Convert to standard form and extract parameters
                # We'll need to handle rotation if B ≠ 0
                if B.is_zero:
                    # Standard form: x²/a² + y²/b² = 1
                    # Rewrite as: (b²)x² + (a²)y² - (a²b²) = 0
                    # So: A=b², C=a², F=-a²b²
                    h = -D / (2 * A)
                    k = -E / (2 * C)
                    a_squared = -F / C + (E**2) / (4 * C**2)
                    b_squared = -F / A + (D**2) / (4 * A**2)
                    a = sp.sqrt(a_squared) if a_squared > 0 else None
                    b = sp.sqrt(b_squared) if b_squared > 0 else None

                    parameters.update(
                        {
                            "center": str([float(h), float(k)]),
                            "semi_major": str(float(max(a, b)))
                            if a is not None and b is not None
                            else "",
                            "semi_minor": str(float(min(a, b)))
                            if a is not None and b is not None
                            else "",
                            "rotation": str(0) if A <= C else str(sp.pi / 2),
                        }
                    )
                else:
                    # Rotated ellipse - we need to find the principal axes
                    parameters.update({"rotated": True})

            elif conic_type == "hyperbola":
                # Similar to ellipse, but with different sign pattern
                if B.is_zero:
                    h = -D / (2 * A)
                    k = -E / (2 * C)

                    # Determine orientation
                    # (x²/a² - y²/b² = 1 or y²/a² - x²/b² = 1)
                    if A > 0 and C < 0:  # x²/a² - y²/b² = 1
                        a_squared = -F / A + (D**2) / (4 * A**2)
                        b_squared = F / C - (E**2) / (4 * C**2)
                        orientation = "x"
                    else:  # y²/a² - x²/b² = 1
                        a_squared = -F / C + (E**2) / (4 * C**2)
                        b_squared = F / A - (D**2) / (4 * A**2)
                        orientation = "y"

                    a = sp.sqrt(a_squared) if a_squared > 0 else None
                    b = sp.sqrt(b_squared) if b_squared > 0 else None

                    parameters.update(
                        {
                            "center": str([float(h), float(k)]),
                            "semi_major": (
                                str(float(a)) if a is not None else ""
                            ),
                            "semi_minor": (
                                str(float(b)) if b is not None else ""
                            ),
                            "orientation": orientation,
                            "rotation": str(0),
                        }
                    )
                else:
                    # Rotated hyperbola
                    parameters.update({"rotated": True})

            elif conic_type == "parabola":
                # For a parabola, we need to determine orientation and vertex
                # This is a simplified approach for non-rotated parabolas
                if A.is_zero and B.is_zero:  # y = ax² + bx + c form
                    a = C
                    b = E
                    c = F
                    h = -b / (2 * a)
                    k = c - b**2 / (4 * a)
                    parameters.update(
                        {
                            "vertex": str([float(h), float(k)]),
                            "orientation": "vertical",
                            "coefficient": str(float(a)),
                        }
                    )
                elif C.is_zero and B.is_zero:  # x = ay² + by + c form
                    a = A
                    b = D
                    c = F
                    k = -b / (2 * a)
                    h = c - b**2 / (4 * a)
                    parameters.update(
                        {
                            "vertex": str([float(h), float(k)]),
                            "orientation": "horizontal",
                            "coefficient": str(float(a)),
                        }
                    )
                else:
                    # More complex parabola, possibly rotated
                    parameters.update({"complex_form": True})

            return json.dumps(
                {
                    "type": conic_type,
                    "parameters": parameters,
                    "equation": str(expr) + " = 0",
                }
            )
        except Exception as e:
            return self.handle_exception("parse_conic_equation", e)

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
        """Generates the equation of a circle.

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
        """Generates the equation of an ellipse.

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
        """Generates the equation of a parabola.

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
        """Generates the equation of a hyperbola.

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
        """Computes properties of a circle.

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
        """Computes properties of an ellipse.

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
        """Computes properties of a parabola.

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
        """Computes properties of a hyperbola.

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
        """Computes the eccentricity of a circle.

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
        """Computes the eccentricity of an ellipse.

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
        """Computes the eccentricity of a parabola.

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
        """Computes the eccentricity of a hyperbola.

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
        """Computes the focus/foci of a circle.

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
        """Computes the foci of an ellipse.

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
        """Computes the focus of a parabola.

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
        """Computes the foci of a hyperbola.

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
        """Computes the directrix/directrices of a circle.

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
        """Computes the directrices of an ellipse.

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
        """Computes the directrix of a parabola.

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
        """Computes the directrices of a hyperbola.

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
        """Computes the asymptotes of a circle.

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
        """Computes the asymptotes of an ellipse.

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
        """Computes the asymptotes of a parabola.

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
        """Computes the asymptotes of a hyperbola.

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
        """Computes the intersection points of a line and a circle.

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
        """Computes the intersection points of a line and an ellipse.

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
        """Computes the intersection points of a line and a parabola.

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
        """Computes the intersection points of a line and a hyperbola.

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
        """Checks the position of a point relative to a circle.

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
        """Checks the position of a point relative to an ellipse.

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
        """Checks the position of a point relative to a parabola.

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
        """Checks the position of a point relative to a hyperbola.

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
        """Computes the tangent line(s) to a circle from a point.

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
        """Computes the tangent line to a circle at a specific point
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
        """Computes the tangent line to an ellipse at a specific point
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
        """Computes the tangent line to a parabola at a specific point
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
        """Computes the tangent line to a hyperbola at a specific point
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

    def solve_circle_problem(
        self,
        problem_type: str,
        center_x: float = 0,
        center_y: float = 0,
        radius: float = 0,
        point_x: float = 0,
        point_y: float = 0,
        line_slope: float = 0,
        line_y_intercept: float = 0,
    ) -> str:
        """Solves a specific type of circle problem.

        Args:
            problem_type: Type of problem to solve
                        ("area", "circumference", "contains_point",
                         "tangent_lines", etc.)
            center_x: x-coordinate of the circle center
            center_y: y-coordinate of the circle center
            radius: radius of the circle
            point_x: x-coordinate of a point (if applicable)
            point_y: y-coordinate of a point (if applicable)
            line_slope: slope of a line (if applicable)
            line_y_intercept: y-intercept of a line (if applicable)

        Returns:
            str: JSON string with the solution
        """
        try:
            h, k = float(center_x), float(center_y)
            r = float(radius)

            if problem_type == "area":
                area = sp.pi * r**2
                return json.dumps(
                    {
                        "result": {
                            "area": str(area),
                            "steps": [
                                "The area of a circle is given by the formula:"
                                "A = πr²",
                                f"Substituting r = {r}",
                                f"A = π * ({r})² = {area!s}",
                            ],
                        }
                    }
                )

            elif problem_type == "circumference":
                circumference = 2 * sp.pi * r
                return json.dumps(
                    {
                        "result": {
                            "circumference": str(circumference),
                            "steps": [
                                "The circumference of a circle is given by"
                                "the formula: C = 2πr",
                                f"Substituting r = {r}",
                                f"C = 2π * {r} = {circumference!s}",
                            ],
                        }
                    }
                )

            elif problem_type == "contains_point":
                p_x, p_y = float(point_x), float(point_y)
                distance = sp.sqrt((p_x - h) ** 2 + (p_y - k) ** 2)

                if distance < r:
                    result = "inside"
                elif abs(distance - r) < 1e-10:
                    result = "on"
                else:
                    result = "outside"

                return json.dumps(
                    {
                        "result": {
                            "position": result,
                            "distance_from_center": str(distance),
                            "steps": [
                                f"Calculate the distance from the point"
                                f"({p_x}, {p_y}) to the center ({h}, {k})",
                                f"Distance = √[(x₂ - x₁)² + (y₂ - y₁)²] ="
                                f"√[({p_x} - {h})² + ({p_y} - {k})²] = "
                                f"{distance!s}",
                                f"Compare with radius r = {r}",
                                f"Since distance {result} radius, the point is"
                                f"{result} the circle",
                            ],
                        }
                    }
                )

            elif problem_type == "line_intersection":
                m, b = float(line_slope), float(line_y_intercept)

                # Solve the system of equations:
                # Circle: (x - h)² + (y - k)² = r²
                # Line: y = mx + b

                # Substitute line equation into circle equation:
                # (x - h)² + (mx + b - k)² = r²

                # Expand:
                # x² - 2hx + h² + m²x² + 2mx(b-k) + (b-k)² - r² = 0
                # (1 + m²)x² + 2(m(b-k) - h)x + (h² + (b-k)² - r²) = 0

                A = 1 + m**2
                B = 2 * (m * (b - k) - h)
                C = h**2 + (b - k) ** 2 - r**2

                # Use the quadratic formula
                discriminant = B**2 - 4 * A * C

                if discriminant < 0:
                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [],
                                "count": 0,
                                "steps": [
                                    f"The line y = {m}x + {b} does not"
                                    f"intersect the circle "
                                    f"(x - {h})² + (y - {k})² = {r}²",
                                    (
                                        f"Discriminant = {discriminant} < 0, "
                                        f"so there are no real solutions"
                                    ),
                                ],
                            }
                        }
                    )

                x1 = (-B + sp.sqrt(discriminant)) / (2 * A)
                x2 = (-B - sp.sqrt(discriminant)) / (2 * A)

                y1 = m * x1 + b
                y2 = m * x2 + b

                if abs(discriminant) < 1e-10:  # Tangent case
                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [
                                    [float(x1), float(y1)]
                                ],
                                "count": 1,
                                "steps": [
                                    f"The line y = {m}x + {b} is tangent to"
                                    f"circle (x - {h})² + (y - {k})² = {r}²",
                                    (
                                        f"Discriminant = {discriminant} ≈ 0, "
                                        f"so there is one solution"
                                    ),
                                    (
                                        f"Intersection point: "
                                        f"({float(x1)}, {float(y1)})"
                                    ),
                                ],
                            }
                        }
                    )

                return json.dumps(
                    {
                        "result": {
                            "intersection_points": [
                                [float(x1), float(y1)],
                                [float(x2), float(y2)],
                            ],
                            "count": 2,
                            "steps": [
                                f"The line y = {m}x + {b} intersects circle"
                                f"(x - {h})² + (y - {k})² = {r}²",
                                f"Discriminant = {discriminant} > 0,"
                                f"so there are two solutions",
                                f"Intersection points:"
                                f"({float(x1)}, {float(y1)}) and"
                                f"({float(x2)}, {float(y2)})",
                            ],
                        }
                    }
                )

            else:
                return json.dumps(
                    {
                        "result": {
                            "message": f"Problem type '{problem_type}'"
                            f"not supported for circles."
                        }
                    }
                )

        except Exception as e:
            return self.handle_exception("solve_circle_problem", e)

    def solve_ellipse_problem(
        self,
        problem_type: str,
        center_x: float = 0,
        center_y: float = 0,
        semi_major: float = 0,
        semi_minor: float = 0,
        orientation: str = "x",
        point_x: float = 0,
        point_y: float = 0,
    ) -> str:
        """Solves a specific type of ellipse problem.

        Args:
            problem_type: Type of problem to solve
                        ("area", "perimeter", "contains_point",
                         "eccentricity", etc.)
            center_x: x-coordinate of the ellipse center
            center_y: y-coordinate of the ellipse center
            semi_major: length of the semi-major axis
            semi_minor: length of the semi-minor axis
            orientation: "x" if major axis is along x-axis, "y" if along y-axis
            point_x: x-coordinate of a point (if applicable)
            point_y: y-coordinate of a point (if applicable)

        Returns:
            str: JSON string with the solution
        """
        try:
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            if problem_type == "area":
                area = sp.pi * a * b
                return json.dumps(
                    {
                        "result": {
                            "area": str(area),
                            "steps": [
                                "The area of ellipse is given by the formula:"
                                "A = πab",
                                f"Substituting a = {a} and b = {b}",
                                f"A = π * {a} * {b} = {area!s}",
                            ],
                        }
                    }
                )

            elif problem_type == "perimeter":
                # Ramanujan's approximation for the perimeter
                h = ((a - b) / (a + b)) ** 2
                perimeter = (
                    sp.pi * (a + b) * (1 + 3 * h / (10 + sp.sqrt(4 - 3 * h)))
                )

                return json.dumps(
                    {
                        "result": {
                            "perimeter": str(perimeter),
                            "note": "This is an approximation",
                            "steps": [
                                "The perimeter of an ellipse is approximated"
                                "using Ramanujan's formula:",
                                "P ≈ π(a + b)(1 + 3h/(10 + √(4 - 3h))) where"
                                "h = ((a - b)/(a + b))²",
                                f"Substituting a = {a} and b = {b}",
                                f"h = (({a} - {b})/({a} + {b}))² = {float(h)}",
                            ],
                        }
                    }
                )

            elif problem_type == "eccentricity":
                # Ensure a > b
                if b > a:
                    a, b = b, a

                eccentricity = sp.sqrt(1 - (b**2 / a**2))

                return json.dumps(
                    {
                        "result": {
                            "eccentricity": str(eccentricity),
                            "steps": [
                                "The eccentricity of an ellipse is given by "
                                "the formula: e = √(1 - (b²/a²))",
                                f"Substituting a = {a} and b = {b}",
                                f"e = √(1 - ({b}²/{a}²)) = {eccentricity!s}",
                            ],
                        }
                    }
                )

            elif problem_type == "contains_point":
                p_x, p_y = float(point_x), float(point_y)

                # Evaluate the ellipse equation at the point
                if orientation.lower() == "x":
                    # (x-h)²/a² + (y-k)²/b² = 1
                    value = (p_x - h) ** 2 / a**2 + (p_y - k) ** 2 / b**2
                else:  # orientation == "y"
                    # (x-h)²/b² + (y-k)²/a² = 1
                    value = (p_x - h) ** 2 / b**2 + (p_y - k) ** 2 / a**2

                if abs(value - 1) < 1e-10:
                    result = "on"
                elif value < 1:
                    result = "inside"
                else:
                    result = "outside"

                return json.dumps(
                    {
                        "result": {
                            "position": result,
                            "equation_value": str(value),
                            "steps": [
                                f"Evaluate the ellipse equation at the point "
                                f"({p_x}, {p_y})",
                                f"For orientation '{orientation}',the equation"
                                f"Substituting x = {p_x}, y = {p_y}, h = {h},"
                                f"k = {k}, a = {a}, b = {b}",
                                f"Value = {value!s}",
                                f"Since value {result} 1, the point is"
                                f"{result} the ellipse",
                            ],
                        }
                    }
                )

            else:
                return json.dumps(
                    {
                        "result": {
                            "message": f"Problem type '{problem_type}'"
                            f"not supported for ellipses."
                        }
                    }
                )

        except Exception as e:
            return self.handle_exception("solve_ellipse_problem", e)

    def solve_parabola_problem(
        self,
        problem_type: str,
        vertex_x: float = 0,
        vertex_y: float = 0,
        coefficient: float = 0,
        orientation: str = "up",
        point_x: float = 0,
        point_y: float = 0,
        line_slope: float = 0,
        line_y_intercept: float = 0,
    ) -> str:
        """Solves a specific type of parabola problem.

        Args:
            problem_type: Type of problem to solve
                        ("focus", "directrix", "contains_point",
                        "axis_of_symmetry", etc.)
            vertex_x: x-coordinate of the parabola vertex
            vertex_y: y-coordinate of the parabola vertex
            coefficient: coefficient of the squared term
            orientation: direction the parabola opens - "up", "down",
                "left", or "right"
            point_x: x-coordinate of a point (if applicable)
            point_y: y-coordinate of a point (if applicable)
            line_slope: slope of a line (if applicable)
            line_y_intercept: y-intercept of a line (if applicable)

        Returns:
            str: JSON string with the solution
        """
        try:
            h, k = float(vertex_x), float(vertex_y)
            a = float(coefficient)

            if problem_type == "focus":
                # Calculate focal distance
                p = 1 / (4 * abs(a))

                # Calculate focus position
                if orientation.lower() == "right":
                    focus = [h + p, k]
                elif orientation.lower() == "left":
                    focus = [h - p, k]
                elif orientation.lower() == "up":
                    focus = [h, k + p]
                else:  # orientation == "down"
                    focus = [h, k - p]

                return json.dumps(
                    {
                        "result": {
                            "focus": focus,
                            "steps": [
                                "The focal distance of a parabola is given"
                                "by p = 1/(4|a|) where a is the coefficient",
                                f"Substituting a = {a}",
                                f"p = 1/(4*|{a}|) = {p}",
                                f"For a parabola opening {orientation},"
                                f"the focus is at ({focus[0]}, {focus[1]})",
                            ],
                        }
                    }
                )

            elif problem_type == "directrix":
                # Calculate focal distance
                p = 1 / (4 * abs(a))

                # Define directrix
                if orientation.lower() == "right":
                    directrix = f"x = {h - p}"
                elif orientation.lower() == "left":
                    directrix = f"x = {h + p}"
                elif orientation.lower() == "up":
                    directrix = f"y = {k - p}"
                else:  # orientation == "down"
                    directrix = f"y = {k + p}"

                return json.dumps(
                    {
                        "result": {
                            "directrix": directrix,
                            "steps": [
                                "The focal distance of a parabola is given by"
                                "p = 1/(4|a|) where a is the coefficient",
                                f"Substituting a = {a}",
                                f"p = 1/(4*|{a}|) = {p}",
                                f"For a parabola opening {orientation}, "
                                f"the directrix is {directrix}",
                            ],
                        }
                    }
                )

            elif problem_type == "axis_of_symmetry":
                # Define axis of symmetry
                if orientation.lower() in ["right", "left"]:
                    axis = f"y = {k}"
                else:  # orientation in ["up", "down"]
                    axis = f"x = {h}"

                return json.dumps(
                    {
                        "result": {
                            "axis_of_symmetry": axis,
                            "steps": [
                                f"For a parabola with vertex at ({h}, {k}) "
                                f"opening {orientation}",
                                f"The axis of symmetry is {axis}",
                            ],
                        }
                    }
                )

            elif problem_type == "contains_point":
                p_x, p_y = float(point_x), float(point_y)

                # Evaluate the parabola equation at the point
                if orientation.lower() == "right":
                    # y - k = a(x - h)²
                    expected_y = k + a * (p_x - h) ** 2
                    value = p_y - expected_y
                elif orientation.lower() == "left":
                    # y - k = a(x - h)²
                    expected_y = k + a * (p_x - h) ** 2
                    value = p_y - expected_y
                elif orientation.lower() == "up":
                    # x - h = a(y - k)²
                    expected_x = h + a * (p_y - k) ** 2
                    value = p_x - expected_x
                else:  # orientation == "down"
                    # x - h = a(y - k)²
                    expected_x = h + a * (p_y - k) ** 2
                    value = p_x - expected_x

                if abs(value) < 1e-10:
                    result = "on"
                else:
                    # For parabolas, "inside" and "outside" depend
                    # on the orientation
                    if orientation.lower() == "right":
                        result = "inside" if value < 0 else "outside"
                    elif orientation.lower() == "left":
                        result = "inside" if value > 0 else "outside"
                    elif orientation.lower() == "up":
                        result = "inside" if value < 0 else "outside"
                    else:  # orientation == "down"
                        result = "inside" if value > 0 else "outside"

                return json.dumps(
                    {
                        "result": {
                            "position": result,
                            "equation_value": str(value),
                            "steps": [
                                f"Evaluate the parabola equation at the point "
                                f"({p_x}, {p_y})",
                                f"For orientation '{orientation}',the equation"
                                f"Substituting x = {p_x}, y = {p_y}, h = {h},"
                                f"k = {k}, a = {a}",
                                f"Value = {value!s}",
                                f"Since value {result} 0, the point is "
                                f"{result} the parabola",
                            ],
                        }
                    }
                )

            elif problem_type == "line_intersection":
                m, b = float(line_slope), float(line_y_intercept)

                # Solve the system of equations
                if orientation.lower() == "right":
                    # Parabola: y - k = a(x - h)²
                    # Line: y = mx + b
                    # Substitute: mx + b - k = a(x - h)²
                    # Rearrange: a(x - h)² - mx - b + k = 0
                    # Expand: ax² - 2ahx + ah² - mx - b + k = 0
                    # Simplify: ax² - (2ah + m)x + (ah² - b + k) = 0

                    A = a
                    B = -(2 * a * h + m)
                    C = a * h**2 - b + k

                elif orientation.lower() == "left":
                    # Same as "right" case
                    A = a
                    B = -(2 * a * h + m)
                    C = a * h**2 - b + k

                elif orientation.lower() == "up":
                    # Parabola: x - h = a(y - k)²
                    # Line: y = mx + b
                    # Substitute: x - h = a(mx + b - k)²
                    # Expand: x - h = a(m²x² + 2mx(b-k) + (b-k)²)
                    # Simplify: x - h = am²x² + 2am(b-k)x + a(b-k)²
                    # Rearrange: am²x² + 2am(b-k)x + a(b-k)² - x + h = 0

                    A = a * m**2
                    B = 2 * a * m * (b - k) - 1
                    C = a * (b - k) ** 2 + h

                else:  # orientation == "down"
                    # Same as "up" case
                    A = a * m**2
                    B = 2 * a * m * (b - k) - 1
                    C = a * (b - k) ** 2 + h

                # Use the quadratic formula
                discriminant = B**2 - 4 * A * C

                if abs(discriminant) < 1e-10:  # One solution (tangent)
                    x1 = -B / (2 * A)
                    y1 = m * x1 + b

                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [
                                    [float(x1), float(y1)]
                                ],
                                "count": 1,
                                "steps": [
                                    f"The line y = {m}x + {b} is "
                                    f"tangent to the parabola",
                                    (
                                        f"Discriminant = {discriminant} ≈ 0, "
                                        f"so there is one solution"
                                    ),
                                    (
                                        f"Intersection point: "
                                        f"({float(x1)}, {float(y1)})"
                                    ),
                                ],
                            }
                        }
                    )

                elif discriminant < 0:  # No real solutions
                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [],
                                "count": 0,
                                "steps": [
                                    f"The line y = {m}x + {b} does"
                                    f"not intersect the parabola",
                                    (
                                        f"Discriminant = {discriminant} < 0, "
                                        f"so there are no real solutions"
                                    ),
                                ],
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
                                "steps": [
                                    f"The line y = {m}x + {b} intersects"
                                    f"the parabola",
                                    (
                                        f"Discriminant = {discriminant} > 0, "
                                        f"so there are two solutions"
                                    ),
                                    (
                                        f"Intersection points: "
                                        f"({float(x1)}, {float(y1)}) and "
                                        f"({float(x2)}, {float(y2)})"
                                    ),
                                ],
                            }
                        }
                    )

            else:
                return json.dumps(
                    {
                        "result": {
                            "message": f"Problem type '{problem_type}' not"
                            f"supported for parabolas."
                        }
                    }
                )

        except Exception as e:
            return self.handle_exception("solve_parabola_problem", e)

    def solve_hyperbola_problem(
        self,
        problem_type: str,
        center_x: float = 0,
        center_y: float = 0,
        semi_major: float = 0,
        semi_minor: float = 0,
        orientation: str = "x",
        point_x: float = 0,
        point_y: float = 0,
        line_slope: float = 0,
        line_y_intercept: float = 0,
    ) -> str:
        """Solves a specific type of hyperbola problem.

        Args:
            problem_type: Type of problem to solve
                        ("foci", "asymptotes", "eccentricity",
                        "contains_point", etc.)
            center_x: x-coordinate of the hyperbola center
            center_y: y-coordinate of the hyperbola center
            semi_major: length of the semi-major axis (transverse axis)
            semi_minor: length of the semi-minor axis (conjugate axis)
            orientation: "x" if transverse axis is along x-axis,
                "y" if along y-axis
            point_x: x-coordinate of a point (if applicable)
            point_y: y-coordinate of a point (if applicable)
            line_slope: slope of a line (if applicable)
            line_y_intercept: y-intercept of a line (if applicable)

        Returns:
            str: JSON string with the solution
        """
        try:
            h, k = float(center_x), float(center_y)
            a = float(semi_major)
            b = float(semi_minor)

            if problem_type == "foci":
                # Calculate focal distance
                c = sp.sqrt(a**2 + b**2)

                # Calculate foci positions
                if orientation.lower() == "x":
                    focus1 = [h + c, k]
                    focus2 = [h - c, k]
                else:  # orientation == "y"
                    focus1 = [h, k + c]
                    focus2 = [h, k - c]

                return json.dumps(
                    {
                        "result": {
                            "foci": [focus1, focus2],
                            "steps": [
                                "The focal distance of a hyperbola is"
                                "given by c = √(a² + b²)",
                                f"Substituting a = {a} and b = {b}",
                                f"c = √({a}² + {b}²) = {float(c)}",
                                (
                                    f"For a hyperbola with orientation"
                                    f"'{orientation}', "
                                    f"the foci are at "
                                    f"({focus1[0]}, {focus1[1]})"
                                    f" and "
                                    f"({focus2[0]}, {focus2[1]})"
                                ),
                            ],
                        }
                    }
                )

            elif problem_type == "asymptotes":
                # Calculate asymptotes
                if orientation.lower() == "x":
                    slope = b / a
                    asymptote1 = f"y = {k} + {float(slope)}(x - {h})"
                    asymptote2 = f"y = {k} - {float(slope)}(x - {h})"

                    # Alternative form
                    asymptote1_alt = (
                        f"y = {float(slope)}x + {float(k - slope*h)}"
                    )
                    asymptote2_alt = (
                        f"y = -{float(slope)}x + {float(k + slope*h)}"
                    )
                else:  # orientation == "y"
                    slope = a / b
                    asymptote1 = f"y = {k} + {float(slope)}(x - {h})"
                    asymptote2 = f"y = {k} - {float(slope)}(x - {h})"

                    # Alternative form
                    asymptote1_alt = (
                        f"y = {float(slope)}x + {float(k - slope*h)}"
                    )
                    asymptote2_alt = (
                        f"y = -{float(slope)}x + {float(k + slope*h)}"
                    )

                return json.dumps(
                    {
                        "result": {
                            "asymptotes": [asymptote1, asymptote2],
                            "alternative_form": [
                                asymptote1_alt,
                                asymptote2_alt,
                            ],
                            "steps": [
                                (
                                    f"For a hyperbola with orientation "
                                    f"'{orientation}', "
                                    f"the asymptotes have slopes "
                                    f"± b/a if orientation.lower() == 'x'"
                                    f"else a/b"
                                ),
                                f"The equations of the asymptotes are "
                                f"{asymptote1} and {asymptote2}",
                                f"In slope-intercept form: "
                                f"{asymptote1_alt} and {asymptote2_alt}",
                            ],
                        }
                    }
                )

            elif problem_type == "eccentricity":
                # Calculate eccentricity
                c = sp.sqrt(a**2 + b**2)
                eccentricity = c / a

                return json.dumps(
                    {
                        "result": {
                            "eccentricity": str(eccentricity),
                            "steps": [
                                "The eccentricity of a hyperbola is given by"
                                "e = c/a "
                                "where c = √(a² + b²)",
                                f"Substituting a = {a} and b = {b}",
                                f"c = √({a}² + {b}²) = {float(c)}",
                                f"e = {float(c)}/{a} = {float(eccentricity)}",
                            ],
                        }
                    }
                )

            elif problem_type == "contains_point":
                p_x, p_y = float(point_x), float(point_y)

                # Evaluate the hyperbola equation at the point
                if orientation.lower() == "x":
                    # (x-h)²/a² - (y-k)²/b² = 1
                    value = (p_x - h) ** 2 / a**2 - (p_y - k) ** 2 / b**2
                else:  # orientation == "y"
                    # (y-k)²/a² - (x-h)²/b² = 1
                    value = (p_y - k) ** 2 / a**2 - (p_x - h) ** 2 / b**2

                if abs(value - 1) < 1e-10:
                    result = "on"
                else:
                    # For hyperbolas, there's no clear "inside" or "outside"
                    # We'll use "between branches" for points where the
                    # equation value < 1 and "on branch side" for points
                    # where the equation value > 1
                    result = (
                        "between branches" if value < 1 else "on branch side"
                    )

                return json.dumps(
                    {
                        "result": {
                            "position": result,
                            "equation_value": str(value),
                            "steps": [
                                f"Evaluate the hyperbola equation at the point"
                                f"({p_x}, {p_y})",
                                f"For orientation '{orientation}', "
                                f"the equation is "
                                + (
                                    "(x-h)²/a² - (y-k)²/b² = 1"
                                    if orientation.lower() == "x"
                                    else "(y-k)²/a² - (x-h)²/b² = 1"
                                ),
                                f"Substituting x = {p_x}, y = {p_y}, h = {h}, "
                                f"k = {k}, a = {a}, b = {b}",
                                f"Value = {value!s}",
                                "Since value "
                                + (
                                    "= 1 (approximately)"
                                    if result == "on"
                                    else "< 1"
                                    if result == "between branches"
                                    else "> 1"
                                )
                                + f", the point is {result}",
                            ],
                        }
                    }
                )

            elif problem_type == "line_intersection":
                m, b_line = float(line_slope), float(line_y_intercept)

                # Solve the system of equations
                if orientation.lower() == "x":
                    # Hyperbola: (x-h)²/a² - (y-k)²/b² = 1
                    # Line: y = mx + b_line
                    # Substitute: (x-h)²/a² - (mx + b_line - k)²/b² = 1
                    # Multiply by a²b²: b²(x-h)² - a²(mx + b_line - k)² = a²b²
                    # Expand: b²x² - 2b²hx + b²h² - a²m²x² - 2a²mx(b_line-k)
                    #                - a²(b_line-k)² = a²b²
                    # Rearrange: (b² - a²m²)x² - (2b²h + 2a²m(b_line-k))x +
                    #            (b²h² - a²(b_line-k)² - a²b²) = 0

                    A = b**2 - a**2 * m**2
                    B = -2 * b**2 * h - 2 * a**2 * m * (b_line - k)
                    C = b**2 * h**2 - a**2 * (b_line - k) ** 2 - a**2 * b**2

                else:  # orientation == "y"
                    # Hyperbola: (y-k)²/a² - (x-h)²/b² = 1
                    # Line: y = mx + b_line
                    # Substitute: (mx + b_line - k)²/a² - (x-h)²/b² = 1
                    # Multiply by a²b²: b²(mx + b_line - k)² - a²(x-h)² = a²b²
                    # Expand: b²m²x² + 2b²mx(b_line-k) + b²(b_line-k)² - a²x²
                    #         + 2a²hx - a²h² = a²b²
                    # Rearrange: (b²m² - a²)x² + (2b²m(b_line-k) + 2a²h)x +
                    #            (b²(b_line-k)² - a²h² - a²b²) = 0

                    A = b**2 * m**2 - a**2
                    B = 2 * b**2 * m * (b_line - k) + 2 * a**2 * h
                    C = b**2 * (b_line - k) ** 2 - a**2 * h**2 - a**2 * b**2

                # Use the quadratic formula
                discriminant = B**2 - 4 * A * C

                if abs(discriminant) < 1e-10:  # One solution (tangent)
                    x1 = -B / (2 * A)
                    y1 = m * x1 + b_line

                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [
                                    [float(x1), float(y1)]
                                ],
                                "count": 1,
                                "steps": [
                                    (
                                        f"The line y = {m}x + {b_line} "
                                        f"is tangent to the hyperbola"
                                    ),
                                    (
                                        f"Discriminant = {discriminant} ≈ 0, "
                                        f"so there is one solution"
                                    ),
                                    (
                                        f"Intersection point: "
                                        f"({float(x1)}, {float(y1)})"
                                    ),
                                ],
                            }
                        }
                    )

                elif discriminant < 0:  # No real solutions
                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [],
                                "count": 0,
                                "steps": [
                                    (
                                        f"The line y = {m}x + {b_line} "
                                        f"does not intersect the hyperbola"
                                    ),
                                    (
                                        f"Discriminant = {discriminant} < 0, "
                                        f"so there are no real solutions"
                                    ),
                                ],
                            }
                        }
                    )

                else:  # Two solutions
                    x1 = (-B + sp.sqrt(discriminant)) / (2 * A)
                    x2 = (-B - sp.sqrt(discriminant)) / (2 * A)

                    y1 = m * x1 + b_line
                    y2 = m * x2 + b_line

                    return json.dumps(
                        {
                            "result": {
                                "intersection_points": [
                                    [float(x1), float(y1)],
                                    [float(x2), float(y2)],
                                ],
                                "count": 2,
                                "steps": [
                                    (
                                        f"The line y = {m}x + {b_line} "
                                        f"intersects the hyperbola"
                                    ),
                                    (
                                        f"Discriminant = {discriminant} > 0, "
                                        f"so there are two solutions"
                                    ),
                                    (
                                        f"Intersection points: "
                                        f"({float(x1)}, {float(y1)}) and "
                                        f"({float(x2)}, {float(y2)})"
                                    ),
                                ],
                            }
                        }
                    )

            elif problem_type == "vertices":
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
                            "steps": [
                                (
                                    f"For a hyperbola with orientation "
                                    f"'{orientation}', "
                                    f"the vertices are at a distance "
                                    f"of {a} from the center"
                                ),
                                (
                                    f"The vertices are at "
                                    f"({vertex1[0]}, {vertex1[1]}) "
                                    f"and ({vertex2[0]}, {vertex2[1]})"
                                ),
                            ],
                        }
                    }
                )

            elif problem_type == "co_vertices":
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
                            "steps": [
                                (
                                    f"For a hyperbola with orientation "
                                    f"'{orientation}', "
                                    f"the co-vertices are at a distance "
                                    f"of {b} from the center"
                                ),
                                (
                                    f"The co-vertices are at "
                                    f"({co_vertex1[0]}, {co_vertex1[1]}) "
                                    f"and ({co_vertex2[0]}, {co_vertex2[1]})"
                                ),
                            ],
                        }
                    }
                )

            else:
                return json.dumps(
                    {
                        "result": {
                            "message": (
                                f"Problem type '{problem_type}' not supported "
                                "for hyperbolas."
                            )
                        }
                    }
                )

        except Exception as e:
            return self.handle_exception("solve_hyperbola_problem", e)

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
            FunctionTool(self.parse_conic_equation_new),
            FunctionTool(self.parse_conic_equation),
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
            # Problem solver layer
            FunctionTool(self.solve_circle_problem),
            FunctionTool(self.solve_ellipse_problem),
            FunctionTool(self.solve_parabola_problem),
            FunctionTool(self.solve_hyperbola_problem),
        ]
