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
from typing import Any, Dict, List

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

    def compute_distance(
        self,
        object1: Any,
        object2: Any,
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
                p1 = sp.Point(float(object2[0][0]), float(object2[0][1]))
                p2 = sp.Point(float(object2[1][0]), float(object2[1][1]))

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

    def compute_area(self, geometry_type: str, *args) -> str:
        r"""Unified area calculation function for different geometric shapes.

        Args:
            geometry_type: Type of geometry ("triangle_vertices",
                           "triangle_sides", "polygon")
            *args: Arguments specific to the geometry type
                - "triangle_vertices": Three points [[x1,y1], [x2,y2], [x3,y3]]
                - "triangle_sides": Three side lengths [a, b, c]
                - "polygon": List of vertices [[x1,y1], [x2,y2], ..., [xn,yn]]

        Returns:
            str: JSON string with the computed area in the "result" field
        """
        try:
            self.logger.info(f"Computing area of {geometry_type}")

            if geometry_type == "triangle_vertices":
                if len(args) != 3:
                    raise ValueError(
                        "Triangle vertices area calculation requires 3 points"
                    )

                point1, point2, point3 = args
                p1 = sp.Point(float(point1[0]), float(point1[1]))
                p2 = sp.Point(float(point2[0]), float(point2[1]))
                p3 = sp.Point(float(point3[0]), float(point3[1]))

                triangle = sp.Triangle(p1, p2, p3)
                area = abs(triangle.area)

            elif geometry_type == "triangle_sides":
                if len(args) != 3:
                    raise ValueError(
                        "Triangle sides area calculation requires 3 side len"
                    )

                a, b, c = float(args[0]), float(args[1]), float(args[2])

                # Check if the sides can form a triangle (triangle inequality)
                if a + b <= c or a + c <= b or b + c <= a:
                    raise ValueError(
                        "The given sides cannot form a triangle"
                        "(triangle inequality violated)."
                    )

                # Calculate semi-perimeter
                s = (a + b + c) / 2

                # Calculate area using Heron's formula
                area = sp.sqrt(s * (s - a) * (s - b) * (s - c))
                area = abs(area)

            elif geometry_type == "polygon":
                if len(args) < 1 or len(args[0]) < 3:
                    raise ValueError(
                        "A polygon must have at least 3 vertices."
                    )

                vertices = args[0]  # Expecting a list of vertices

                # Convert vertices to SymPy Points
                points = [
                    sp.Point(float(vertex[0]), float(vertex[1]))
                    for vertex in vertices
                ]

                # Create a SymPy Polygon
                polygon = sp.Polygon(*points)

                # Calculate the area
                area = abs(polygon.area)

            else:
                raise ValueError(f"Unsupported geometry type: {geometry_type}")

            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_area", e)

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

    def generate_conic_equation(
        self, conic_type: str, parameters: Dict[str, Any]
    ) -> str:
        r"""Generates the standard form equation for a conic section.

        Args:
            conic_type: Type of conic ("circle", "ellipse", "parabola",
                          "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the standard form equation
        """
        try:
            self.logger.info(f"Generating equation for {conic_type}")
            x, y = sp.symbols('x y')

            def expand_equation(equation):
                return sp.expand(equation)

            if conic_type == "circle":
                h, k = parameters.get("center", [0, 0])
                r = parameters.get("radius", 1)

                equation = (x - h) ** 2 + (y - k) ** 2 - r**2
                standard_form = f"(x - {h})² + (y - {k})² = {r}²"

            elif conic_type == "ellipse":
                h, k = parameters.get("center", [0, 0])
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)
                rotation = parameters.get("rotation", 0)

                if rotation in [0, sp.pi]:
                    equation = (
                        ((x - h) ** 2 / a**2) + ((y - k) ** 2 / b**2) - 1
                    )
                    standard_form = f"(x - {h})²/{a}² + (y - {k})²/{b}² = 1"
                elif rotation in [sp.pi / 2, 3 * sp.pi / 2]:
                    equation = (
                        ((x - h) ** 2 / b**2) + ((y - k) ** 2 / a**2) - 1
                    )
                    standard_form = f"(x - {h})²/{b}² + (y - {k})²/{a}² = 1"
                else:
                    cos_t, sin_t = sp.cos(rotation), sp.sin(rotation)
                    X, Y = (
                        (x - h) * cos_t + (y - k) * sin_t,
                        -(x - h) * sin_t + (y - k) * cos_t,
                    )
                    equation = (X**2 / a**2) + (Y**2 / b**2) - 1
                    standard_form = (
                        f"Rotated ellipse with center ({h},{k}), "
                        f"semi-major {a}, semi-minor {b}, rotation {rotation}"
                    )

            elif conic_type == "parabola":
                h, k = parameters.get("vertex", [0, 0])
                orientation = parameters.get("orientation", "vertical")

                if "focus" in parameters:
                    p, q = parameters["focus"]
                    c = abs(q - k) if orientation == "vertical" else abs(p - h)
                    equation = (
                        (x - h) ** 2 - 4 * c * (y - k)
                        if orientation == "vertical"
                        else (y - k) ** 2 - 4 * c * (x - h)
                    )
                    standard_form = (
                        f"(x - {h})² = 4({c})(y - {k})"
                        if orientation == "vertical"
                        else f"(y - {k})² = 4({c})(x - {h})"
                    )
                elif "coefficient" in parameters:
                    a = parameters["coefficient"]
                    equation = (
                        (y - k) - a * (x - h) ** 2
                        if orientation == "vertical"
                        else (x - h) - a * (y - k) ** 2
                    )
                    standard_form = (
                        f"y - {k} = {a}(x - {h})²"
                        if orientation == "vertical"
                        else f"x - {h} = {a}(y - {k})²"
                    )
                else:
                    raise ValueError(
                        "Insufficient parameters for parabola equation"
                    )

            elif conic_type == "hyperbola":
                h, k = parameters.get("center", [0, 0])
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)
                orientation = parameters.get("orientation", "x")
                rotation = parameters.get("rotation", 0)

                if rotation in [0, sp.pi]:
                    equation = (
                        ((x - h) ** 2 / a**2) - ((y - k) ** 2 / b**2) - 1
                        if orientation == "x"
                        else ((y - k) ** 2 / a**2) - ((x - h) ** 2 / b**2) - 1
                    )
                    standard_form = (
                        f"(x - {h})²/{a}² - (y - {k})²/{b}² = 1"
                        if orientation == "x"
                        else f"(y - {k})²/{a}² - (x - {h})²/{b}² = 1"
                    )
                else:
                    cos_t, sin_t = sp.cos(rotation), sp.sin(rotation)
                    X, Y = (
                        (x - h) * cos_t + (y - k) * sin_t,
                        -(x - h) * sin_t + (y - k) * cos_t,
                    )
                    equation = (
                        (X**2 / a**2) - (Y**2 / b**2) - 1
                        if orientation == "x"
                        else (Y**2 / a**2) - (X**2 / b**2) - 1
                    )
                    standard_form = (
                        f"Rotated hyperbola with center ({h},{k}), "
                        f"semi-major {a}, semi-minor {b}, "
                        f"orientation {orientation}, rotation {rotation}"
                    )

            else:
                raise ValueError(f"Unsupported conic type: {conic_type}")

            general_form = expand_equation(equation)

            return json.dumps(
                {
                    "standard_form": standard_form,
                    "general_form": str(general_form) + " = 0",
                    "coefficients": {
                        "A": float(general_form.coeff(x, 2)),
                        "B": float(general_form.coeff(x, 1).coeff(y, 1)),
                        "C": float(general_form.coeff(y, 2)),
                        "D": float(general_form.coeff(x, 1).subs(y, 0)),
                        "E": float(general_form.coeff(y, 1).subs(x, 0)),
                        "F": float(general_form.subs({x: 0, y: 0})),
                    },
                }
            )
        except Exception as e:
            return self.handle_exception("generate_conic_equation", e)

    # ====================== CONIC PROPERTY CALCULATORS ======================

    def compute_conic_properties(
        self, conic_type: str, parameters: Dict[str, Any], property_name: str
    ) -> str:
        r"""Computes various properties of conic sections.

        Args:
            conic_type: Type of conic ("circle", "ellipse", "parabola"...)
            parameters: Dictionary of parameters specific to the conic type
            property_name: Property to compute ("eccentricity", "foci",
                           "directrix", "asymptotes")

        Returns:
            str: JSON string with the computed property
        """
        try:
            self.logger.info(f"Computing {property_name} for {conic_type}")

            if property_name == "eccentricity":
                return self.compute_eccentricity(conic_type, parameters)
            elif property_name == "foci":
                return self.compute_foci(conic_type, parameters)
            elif property_name == "directrix":
                return self.compute_directrix(conic_type, parameters)
            elif property_name == "asymptotes" and conic_type == "hyperbola":
                return self.compute_asymptotes(parameters)
            else:
                raise ValueError(
                    f"Unsupported property {property_name} for conic type "
                    f"{conic_type}"
                )

        except Exception as e:
            return self.handle_exception("compute_conic_properties", e)

    def compute_eccentricity(
        self, conic_type: str, parameters: Dict[str, Any]
    ) -> str:
        r"""Computes the eccentricity of a conic section.

        Args:
            conic_type: Type of conic ("ellipse", "parabola", "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the eccentricity value
        """
        try:
            self.logger.info(f"Computing eccentricity for {conic_type}")

            if conic_type == "circle":
                eccentricity = 0

            elif conic_type == "ellipse":
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)

                if a <= 0 or b <= 0:
                    raise ValueError(
                        "Semi-major and semi-minor axes must be positive"
                    )

                if a < b:
                    a, b = b, a  # Ensure a is the semi-major axis

                eccentricity = sp.sqrt(1 - (b**2 / a**2))

            elif conic_type == "parabola":
                eccentricity = 1

            elif conic_type == "hyperbola":
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)

                if a <= 0 or b <= 0:
                    raise ValueError(
                        "Semi-major and semi-minor axes must be positive"
                    )

                eccentricity = sp.sqrt(1 + (b**2 / a**2))

            else:
                raise ValueError(f"Unsupported conic type: {conic_type}")

            return json.dumps({"result": float(eccentricity)})
        except Exception as e:
            return self.handle_exception("compute_eccentricity", e)

    def compute_foci(self, conic_type: str, parameters: Dict[str, Any]) -> str:
        r"""Computes the foci of a conic section.

        Args:
            conic_type: Type of conic ("ellipse", "parabola", "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the coordinates of the foci
        """
        try:
            self.logger.info(f"Computing foci for {conic_type}")

            if conic_type == "circle":
                h = parameters.get("center", [0, 0])[0]
                k = parameters.get("center", [0, 0])[1]
                foci = [[h, k]]  # Circle has a single focus at its center

            elif conic_type == "ellipse":
                h = parameters.get("center", [0, 0])[0]
                k = parameters.get("center", [0, 0])[1]
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)
                rotation = parameters.get("rotation", 0)

                if a < b:
                    a, b = b, a  # Ensure a is the semi-major axis
                    rotation = rotation + sp.pi / 2 if rotation == 0 else 0

                c = sp.sqrt(a**2 - b**2)  # Distance from center to focus

                if rotation == 0 or rotation == sp.pi:
                    # Foci along x-axis
                    f1 = [h - c, k]
                    f2 = [h + c, k]
                elif rotation == sp.pi / 2 or rotation == 3 * sp.pi / 2:
                    # Foci along y-axis
                    f1 = [h, k - c]
                    f2 = [h, k + c]
                else:
                    # Rotated ellipse
                    cos_t = sp.cos(rotation)
                    sin_t = sp.sin(rotation)
                    f1 = [h - c * cos_t, k - c * sin_t]
                    f2 = [h + c * cos_t, k + c * sin_t]

                foci = [
                    [float(f1[0]), float(f1[1])],
                    [float(f2[0]), float(f2[1])],
                ]

            elif conic_type == "parabola":
                h = parameters.get("vertex", [0, 0])[0]
                k = parameters.get("vertex", [0, 0])[1]
                orientation = parameters.get("orientation", "vertical")

                if "focus" in parameters:
                    focus = parameters["focus"]
                    foci = [[float(focus[0]), float(focus[1])]]
                elif "coefficient" in parameters:
                    a = parameters["coefficient"]
                    if orientation == "vertical":
                        p = 1 / (4 * a)  # Distance from vertex to focus
                        foci = [[float(h), float(k + p)]]
                    else:
                        p = 1 / (4 * a)  # Distance from vertex to focus
                        foci = [[float(h + p), float(k)]]
                else:
                    raise ValueError(
                        "Insufficient parameters for parabola foci"
                    )

            elif conic_type == "hyperbola":
                h = parameters.get("center", [0, 0])[0]
                k = parameters.get("center", [0, 0])[1]
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)
                orientation = parameters.get("orientation", "x")
                rotation = parameters.get("rotation", 0)

                c = sp.sqrt(a**2 + b**2)  # Distance from center to focus

                if rotation == 0 or rotation == sp.pi:
                    if orientation == "x":
                        # Foci along x-axis
                        f1 = [h - c, k]
                        f2 = [h + c, k]
                    else:
                        # Foci along y-axis
                        f1 = [h, k - c]
                        f2 = [h, k + c]
                else:
                    # Rotated hyperbola
                    cos_t = sp.cos(rotation)
                    sin_t = sp.sin(rotation)

                    if orientation == "x":
                        f1 = [h - c * cos_t, k - c * sin_t]
                        f2 = [h + c * cos_t, k + c * sin_t]
                    else:
                        f1 = [h - c * sin_t, k + c * cos_t]
                        f2 = [h + c * sin_t, k - c * cos_t]

                foci = [
                    [float(f1[0]), float(f1[1])],
                    [float(f2[0]), float(f2[1])],
                ]

            else:
                raise ValueError(f"Unsupported conic type: {conic_type}")

            return json.dumps({"result": foci})
        except Exception as e:
            return self.handle_exception("compute_foci", e)

    def compute_directrix(
        self, conic_type: str, parameters: Dict[str, Any]
    ) -> str:
        r"""Computes the directrix of a conic section.

        Args:
            conic_type: Type of conic ("ellipse", "parabola", "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the equation of the directrix
        """
        try:
            self.logger.info(f"Computing directrix for {conic_type}")
            x, y = sp.symbols('x y')

            if conic_type == "parabola":
                h = parameters.get("vertex", [0, 0])[0]
                k = parameters.get("vertex", [0, 0])[1]
                orientation = parameters.get("orientation", "vertical")

                if "focus" in parameters:
                    focus = parameters["focus"]
                    p = (
                        abs(focus[1] - k)
                        if orientation == "vertical"
                        else abs(focus[0] - h)
                    )

                    if orientation == "vertical":
                        # Directrix is horizontal line
                        _ = f"y = {k - p}"
                    else:
                        # Directrix is vertical line
                        _ = f"x = {h - p}"

                elif "coefficient" in parameters:
                    a = parameters["coefficient"]
                    p = 1 / (4 * a)  # Distance from vertex to focus

                    if orientation == "vertical":
                        # Directrix is horizontal line
                        _ = f"y = {k - p}"
                    else:
                        # Directrix is vertical line
                        _ = f"x = {h - p}"
                else:
                    raise ValueError(
                        "Insufficient parameters for parabola directrix"
                    )

            elif conic_type in ["ellipse", "hyperbola"]:
                h = parameters.get("center", [0, 0])[0]
                k = parameters.get("center", [0, 0])[1]
                a = parameters.get("semi_major", 2)
                b = parameters.get("semi_minor", 1)
                rotation = parameters.get("rotation", 0)

                if conic_type == "ellipse":
                    if a < b:
                        a, b = b, a  # Ensure a is the semi-major axis
                        rotation = rotation + sp.pi / 2 if rotation == 0 else 0

                    c = sp.sqrt(a**2 - b**2)  # Distance from center to focus
                    e = c / a  # Eccentricity
                    d = a / e  # Distance from center to directrix

                else:  # hyperbola
                    c = sp.sqrt(a**2 + b**2)  # Distance from center to focus
                    e = c / a  # Eccentricity
                    d = a / e  # Distance from center to directrix

                    # For simplicity, we'll only handle non-rotated cases fully
                if rotation == 0 or rotation == sp.pi:
                    # Directrices are vertical lines
                    directrix1_eq = x - (h - d)
                    directrix2_eq = x - (h + d)
                    directrix_lines: List[str] = [
                        f"x = {h - d}",
                        f"x = {h + d}",
                    ]
                elif rotation == sp.pi / 2 or rotation == 3 * sp.pi / 2:
                    # Directrices are horizontal lines
                    directrix1_eq = y - (k - d)
                    directrix2_eq = y - (k + d)
                    directrix_lines_horiz: List[str] = [
                        f"y = {k - d}",
                        f"y = {k + d}",
                    ]
                else:
                    # Rotated case - more complex

                    # Parametric form of directrices
                    directrix1_eq = (
                        f"Rotated directrix 1 with center ({h}, {k}), "
                        f"distance {d}, rotation {rotation}"
                    )
                    directrix2_eq = (
                        f"Rotated directrix 2 with center ({h}, {k}), "
                        f"distance {d}, rotation {rotation}"
                    )
                    directrix_lines_rot: List[Any] = [
                        directrix1_eq,
                        directrix2_eq,
                    ]
            else:
                raise ValueError(
                    f"Directrix not defined for conic type: {conic_type}"
                )

            # Format the result based on conic type
            if conic_type == "parabola":
                if rotation == 0 or rotation == sp.pi:
                    result = {
                        "equation": (
                            str(directrix_lines[0]) if directrix_lines else ""
                        )
                    }
                elif rotation == sp.pi / 2 or rotation == 3 * sp.pi / 2:
                    result = {
                        "equation": str(directrix_lines_horiz[0])
                        if directrix_lines_horiz
                        else ""
                    }
                else:
                    result = {
                        "equation": str(directrix_lines_rot[0])
                        if directrix_lines_rot
                        else ""
                    }
            else:
                if rotation == 0 or rotation == sp.pi:
                    result = {
                        "equations": (
                            str([str(eq) for eq in directrix_lines])
                            if directrix_lines
                            else ""
                        )
                    }
                elif rotation == sp.pi / 2 or rotation == 3 * sp.pi / 2:
                    result = {
                        "equations": (
                            str([str(eq) for eq in directrix_lines_horiz])
                            if directrix_lines_horiz
                            else ""
                        )
                    }
                else:
                    result = {
                        "equations": (
                            str([str(eq) for eq in directrix_lines_rot])
                            if directrix_lines_rot
                            else ""
                        )
                    }

            return json.dumps({"result": result})
        except Exception as e:
            return self.handle_exception("compute_directrix", e)

    def compute_asymptotes(self, parameters: Dict[str, Any]) -> str:
        r"""Computes the asymptotes of a hyperbola.

        Args:
            parameters: Dictionary of parameters for the hyperbola

        Returns:
            str: JSON string with the equations of the asymptotes
        """
        try:
            self.logger.info("Computing asymptotes for hyperbola")
            x, y = sp.symbols('x y')

            h = parameters.get("center", [0, 0])[0]
            k = parameters.get("center", [0, 0])[1]
            a = parameters.get("semi_major", 2)
            b = parameters.get("semi_minor", 1)
            orientation = parameters.get("orientation", "x")
            rotation = parameters.get("rotation", 0)

            if rotation == 0 or rotation == sp.pi:
                if orientation == "x":
                    # y = ±(b/a)(x-h) + k
                    slope = b / a
                    asymptote1_line = f"y = {k} + {slope}(x - {h})"
                    asymptote2_line = f"y = {k} - {slope}(x - {h})"
                else:
                    # x = ±(b/a)(y-k) + h
                    slope = b / a
                    asymptote1_line = f"x = {h} + {slope}(y - {k})"
                    asymptote2_line = f"x = {h} - {slope}(y - {k})"
            else:
                # Rotated hyperbola - more complex

                if orientation == "x":
                    # Rotated asymptotes
                    slope = b / a
                    # These are approximate representations for rotated case
                    asymptote1_line_x: str = (
                        f"Rotated asymptote 1: slope={slope}, "
                        f"center=({h}, {k}), "
                        f"rotation={rotation} radians"
                    )
                    asymptote2_line_x: str = (
                        f"Rotated asymptote 2: slope={-slope}, "
                        f"center=({h}, {k}),"
                        f"rotation={rotation} radians"
                    )
                else:
                    slope = a / b
                    asymptote1_line_y: str = (
                        f"Rotated asymptote 1: slope={slope}, "
                        f"center=({h}, {k}),"
                        f"rotation={rotation} radians"
                    )
                    asymptote2_line_y: str = (
                        f"Rotated asymptote 2: slope={-slope}, "
                        f"center=({h}, {k}),"
                        f"rotation={rotation} radians"
                    )

            # Determine which asymptote lines to use based on orientation
            if rotation == 0 or rotation == sp.pi:
                asymptote_lines = [asymptote1_line, asymptote2_line]
            else:
                if orientation == "x":
                    asymptote_lines = [asymptote1_line_x, asymptote2_line_x]
                else:
                    asymptote_lines = [asymptote1_line_y, asymptote2_line_y]

            return json.dumps({"result": {"equations": asymptote_lines}})
        except Exception as e:
            return self.handle_exception("compute_asymptotes", e)

    # ====================== GEOMETRIC OPERATIONS ======================

    def compute_line_conic_intersection(
        self,
        line_points: List[List[float]],
        conic_type: str,
        parameters: Dict[str, Any],
    ) -> str:
        r"""Computes the intersection points of a line and a conic section.

        Args:
            line_points: Two points defining the line [[x1,y1], [x2,y2]]
            conic_type: Type of conic ("circle", "ellipse", "parabola",
                        "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the coordinates of intersection points
        """
        try:
            self.logger.info(
                f"Computing intersection of line and {conic_type}"
            )
            x, y = sp.symbols('x y')

            # Ensure distinct points
            if line_points[0] == line_points[1]:
                raise ValueError("Line points must be distinct")

            x1, y1 = map(float, line_points[0])
            x2, y2 = map(float, line_points[1])

            # Compute line equation coefficients
            a, b, c = y2 - y1, x1 - x2, x2 * y1 - x1 * y2

            # Determine line type
            is_vertical = abs(b) < 1e-10
            is_horizontal = abs(a) < 1e-10

            # Generate conic equation
            conic_result = json.loads(
                self.generate_conic_equation(conic_type, parameters)
            )
            conic_expr = sp.sympify(
                conic_result["general_form"].replace(" = 0", "")
            )

            # Solve for intersection points
            if is_vertical:
                intersection_eq = conic_expr.subs(x, x1)
                solutions = sp.solve(intersection_eq, y)
                intersection_points = [
                    [x1, float(sol)] for sol in solutions if sol.is_real
                ]
            elif is_horizontal:
                intersection_eq = conic_expr.subs(y, y1)
                solutions = sp.solve(intersection_eq, x)
                intersection_points = [
                    [float(sol), y1] for sol in solutions if sol.is_real
                ]
            else:
                m, d = -a / b, -c / b
                intersection_eq = conic_expr.subs(y, m * x + d)
                solutions = sp.solve(intersection_eq, x)
                intersection_points = [
                    [float(sol), float(m * sol + d)]
                    for sol in solutions
                    if sol.is_real
                ]

            return json.dumps({"result": intersection_points})
        except Exception as e:
            return self.handle_exception("compute_line_conic_intersection", e)

    def check_point_position(
        self, point: List[float], conic_type: str, parameters: Dict[str, Any]
    ) -> str:
        r"""Determines if a point is inside, on, or outside a conic section.

        Args:
            point: Coordinates [x,y] of the point
            conic_type: Type of conic ("circle", "ellipse", "parabola",
                          "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the position ("inside", "on", "outside")
        """
        try:
            self.logger.info(
                f"Checking position of point relative to {conic_type}"
            )
            x, y = sp.symbols('x y')

            # Generate conic equation
            conic_result = json.loads(
                self.generate_conic_equation(conic_type, parameters)
            )
            conic_expr = sp.sympify(
                conic_result["general_form"].replace(" = 0", "")
            )

            # Evaluate the expression at the given point
            px, py = map(float, point)
            result_value = float(conic_expr.subs({x: px, y: py}))

            # Define tolerance for floating-point comparisons
            tolerance = 1e-10

            # Determine position based on the value and conic type
            if abs(result_value) < tolerance:
                position = "on"
            elif conic_type in {"circle", "ellipse"}:
                position = "inside" if result_value < 0 else "outside"
            elif conic_type == "hyperbola":
                position = "outside" if result_value > 0 else "inside"
            elif conic_type == "parabola":
                orientation = parameters.get("orientation", "vertical")
                position = (
                    "inside"
                    if (
                        result_value > 0
                        if orientation == "vertical"
                        else result_value > 0
                    )
                    else "outside"
                )
            else:
                raise ValueError(f"Unsupported conic type: {conic_type}")

            return json.dumps({"result": position})
        except Exception as e:
            return self.handle_exception("check_point_position", e)

    def compute_tangent_line(
        self, point: List[float], conic_type: str, parameters: Dict[str, Any]
    ) -> str:
        r"""Computes the tangent line to a conic section at a given point.

        Args:
            point: Coordinates [x,y] of the point
            conic_type: Type of conic ("circle", "ellipse", "parabola",
                        "hyperbola")
            parameters: Dictionary of parameters specific to the conic type

        Returns:
            str: JSON string with the equation of the tangent line
        """
        try:
            self.logger.info(
                f"Computing tangent line to {conic_type} at point {point}"
            )
            x, y = sp.symbols('x y')

            # Check if the point is on the conic
            position_result = json.loads(
                self.check_point_position(point, conic_type, parameters)
            )
            if position_result["result"] != "on":
                raise ValueError(
                    "The point must be on the conic section"
                    "to compute a tangent line"
                )

            # Generate conic equation
            conic_result = json.loads(
                self.generate_conic_equation(conic_type, parameters)
            )
            conic_general_form = conic_result["general_form"].replace(
                " = 0", ""
            )
            conic_expr = sp.sympify(conic_general_form)

            # Get the point coordinates
            px, py = float(point[0]), float(point[1])

            # Compute partial derivatives at the point
            df_dx = sp.diff(conic_expr, x).subs({x: px, y: py})
            df_dy = sp.diff(conic_expr, y).subs({x: px, y: py})

            # Tangent line equation: df_dx*(x-px) + df_dy*(y-py) = 0

            # Convert to standard form: ax + by + c = 0
            a = float(df_dx)
            b = float(df_dy)
            c = -a * px - b * py

            # Format the equation as a string
            if abs(b) < 1e-10:  # Vertical line
                tangent_str = f"x = {px}"
            elif abs(a) < 1e-10:  # Horizontal line
                tangent_str = f"y = {py}"
            else:
                # y = mx + d
                m = -a / b
                d = -c / b
                tangent_str = f"y = {m}x + {d}"

            return json.dumps(
                {
                    "result": {
                        "equation": tangent_str,
                        "coefficients": {"a": a, "b": b, "c": c},
                    }
                }
            )
        except Exception as e:
            return self.handle_exception("compute_tangent_line", e)

    # ====================== PROBLEM SOLVER LAYER ======================

    def solve_conic_problem(
        self, problem_type: str, parameters: Dict[str, Any]
    ) -> str:
        r"""Solves complex conic section problems by orchestrating
            multiple operations.

        Args:
            problem_type: Type of problem to solve
            parameters: Dictionary of parameters specific to the problem

        Returns:
            str: JSON string with the solution
        """
        try:
            self.logger.info(f"Solving conic problem of type: {problem_type}")

            if problem_type == "find_parameter_from_condition":
                conic_type = parameters.get("conic_type")
                condition_type = parameters.get("condition_type")

                if (
                    conic_type == "hyperbola"
                    and condition_type == "asymptote_slope"
                ):
                    slope = parameters.get("slope", 1.0)
                    if slope is None:
                        slope = 1.0
                    center = parameters.get("center", [0, 0])
                    semi_major = parameters.get("semi_major", 1.0)
                    if semi_major is None:
                        semi_major = 1.0

                    semi_minor = abs(float(slope) * float(semi_major))

                    return json.dumps(
                        {
                            "result": {
                                "semi_minor": float(semi_minor),
                                "parameters": {
                                    "center": center,
                                    "semi_major": float(semi_major),
                                    "semi_minor": float(semi_minor),
                                    "orientation": "x",
                                },
                            }
                        }
                    )

                elif (
                    conic_type == "ellipse"
                    and condition_type == "eccentricity"
                ):
                    eccentricity = parameters.get("eccentricity", 0.5)
                    if eccentricity is None:
                        eccentricity = 0.5
                    semi_major = parameters.get("semi_major", 1.0)
                    if semi_major is None:
                        semi_major = 1.0

                    semi_minor = float(semi_major) * sp.sqrt(
                        1 - float(eccentricity) ** 2
                    )

                    return json.dumps(
                        {
                            "result": {
                                "semi_minor": float(semi_minor),
                                "parameters": {
                                    "semi_major": float(semi_major),
                                    "semi_minor": float(semi_minor),
                                    "eccentricity": float(eccentricity),
                                },
                            }
                        }
                    )

                elif (
                    conic_type == "parabola"
                    and condition_type == "focus_distance"
                ):
                    vertex = parameters.get("vertex", [0, 0])
                    focus_distance = parameters.get("focus_distance", 1.0)
                    if focus_distance is None:
                        focus_distance = 1.0
                    orientation = parameters.get("orientation", "vertical")

                    coefficient = 1 / (4 * float(focus_distance))

                    focus_x = (
                        vertex[0]
                        if orientation == "vertical"
                        else vertex[0] + focus_distance
                    )
                    focus_y = (
                        vertex[1] + focus_distance
                        if orientation == "vertical"
                        else vertex[1]
                    )

                    return json.dumps(
                        {
                            "result": {
                                "coefficient": float(coefficient),
                                "parameters": {
                                    "vertex": vertex,
                                    "coefficient": float(coefficient),
                                    "orientation": orientation,
                                    "focus": [focus_x, focus_y],
                                },
                            }
                        }
                    )

            elif problem_type == "find_intersection_count":
                conic1_type = parameters.get("conic1_type")
                conic1_params = parameters.get("conic1_params", {})
                conic2_type = parameters.get("conic2_type")
                conic2_params = parameters.get("conic2_params", {})

                if conic1_type == "circle" and conic2_type == "circle":
                    center1 = conic1_params.get("center", [0, 0])
                    radius1 = conic1_params.get("radius", 1)
                    center2 = conic2_params.get("center", [0, 0])
                    radius2 = conic2_params.get("radius", 1)

                    distance = sp.sqrt(
                        (center1[0] - center2[0]) ** 2
                        + (center1[1] - center2[1]) ** 2
                    )

                    if distance > radius1 + radius2:
                        intersection_count = 0
                    elif abs(distance - (radius1 + radius2)) < 1e-10:
                        intersection_count = 1
                    elif distance < radius1 + radius2 and distance > abs(
                        radius1 - radius2
                    ):
                        intersection_count = 2
                    elif abs(distance - abs(radius1 - radius2)) < 1e-10:
                        intersection_count = 1
                    else:
                        intersection_count = 0

                    return json.dumps(
                        {"result": {"intersection_count": intersection_count}}
                    )
                else:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": (
                                "Intersection count for these conic types "
                                "is not yet implemented"
                            ),
                        }
                    )

            else:
                raise ValueError(f"Unsupported problem type: {problem_type}")

            # Default return if no specific condition is met
            return json.dumps(
                {"status": "error", "message": "No matching condition found"}
            )

        except Exception as e:
            return self.handle_exception("solve_conic_problem", e)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of available tools in the toolkit.
        """
        return [
            # Core geometric functions
            FunctionTool(self.compute_distance),
            FunctionTool(self.compute_vector_operations),
            FunctionTool(self.compute_area),
            FunctionTool(self.compute_midpoint),
            FunctionTool(self.compute_line_bisector),
            FunctionTool(self.check_points_collinear),
            # Conic section helpers
            FunctionTool(self.parse_conic_equation_new),
            FunctionTool(self.parse_conic_equation),
            FunctionTool(self.solve_quadratic),
            FunctionTool(self.generate_conic_equation),
            # Conic property calculators
            FunctionTool(self.compute_conic_properties),
            FunctionTool(self.compute_eccentricity),
            FunctionTool(self.compute_foci),
            FunctionTool(self.compute_directrix),
            FunctionTool(self.compute_asymptotes),
            # Geometric operations
            FunctionTool(self.compute_line_conic_intersection),
            FunctionTool(self.check_point_position),
            FunctionTool(self.compute_tangent_line),
            # Problem solver layer
            FunctionTool(self.solve_conic_problem),
        ]
