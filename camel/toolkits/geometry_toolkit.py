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


class GeometryToolkit(BaseToolkit):
    r"""A toolkit for performing geometric computations using SymPy.
    This includes methods for creating and analyzing geometric objects
    like points, lines, circles, and polygons.
    """

    def __init__(self, log_level=logging.INFO, timeout: int = 180):
        r"""
        Initializes the toolkit with logging.

        Args:
            log_level (int): The logging level (default: logging.INFO).
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

    def handle_exception(self, function_name: str, exception: Exception) -> str:
        """Handles exceptions in a consistent way across the toolkit.

        Args:
            function_name (str): Name of the function where exception occurred
            exception (Exception): The exception that was raised

        Returns:
            str: JSON string with error information
        """
        self.logger.error(
            f"Error in {function_name}: {str(exception)}"
        )
        return json.dumps({"status": "error", "message": str(exception)})

    def compute_inner_product(
        self, vector1: List[float], vector2: List[float]
    ) -> str:
        r"""Computes the inner (dot) product of two vectors.

        Args:
            vector1 (List[float]): The first vector as a list of floats.
            vector2 (List[float]): The second vector as a list of floats.

        Returns:
            str: JSON string containing the inner product in the
                `"result"` field. If an error occurs, the JSON
                string will include an `"error"` field with
                the corresponding error message.

        Raises:
            Exception: If there is an error during the computation process,
                    such as mismatched dimensions.
        """
        try:
            self.logger.info(
                f"Computing inner product of vectors: {vector1} and {vector2}"
            )
            # Convert the lists into sympy Matrix objects (column vectors)
            v1 = sp.Matrix([float(x) for x in vector1])
            v2 = sp.Matrix([float(x) for x in vector2])

            # Check that the vectors have the same dimensions.
            if v1.shape != v2.shape:
                raise ValueError(
                    "Vectors must have the same dimensions to compute"
                    "the inner product."
                )

            # Compute the dot (inner) product.
            inner_product = v1.dot(v2)
            self.logger.info(f"Result of inner product: {inner_product}")

            return json.dumps({"result": str(inner_product)})
        except Exception as e:
            return self.handle_exception("compute_inner_product", e)

    def compute_line_bisectors(self, point1: List[float], point2: List[float]) -> str:
        r"""Computes the perpendicular bisector of a line segment.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the perpendicular bisector. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            line_segment = sp.Segment(p1, p2)
            bisector = line_segment.perpendicular_bisector()
            return json.dumps({"result": str(bisector)})
        except Exception as e:
            return self.handle_exception("compute_line_bisectors", e)

    def compute_centroid(self, point1: List[float], point2: List[float], point3: List[float]) -> str:
        r"""Computes the centroid of a triangle.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.
            point3 (List[float]): Coordinates [x, y] of the third point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the centroid point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            p3 = sp.Point(float(point3[0]), float(point3[1]))
            triangle = sp.Triangle(p1, p2, p3)
            centroid = triangle.centroid
            return json.dumps({"result": str(centroid)})
        except Exception as e:
            return self.handle_exception("compute_centroid", e)

    def compute_orthocenter(self, point1: List[float], point2: List[float], point3: List[float]) -> str:
        r"""Computes the orthocenter of a triangle.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.
            point3 (List[float]): Coordinates [x, y] of the third point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the orthocenter point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            p3 = sp.Point(float(point3[0]), float(point3[1]))
            triangle = sp.Triangle(p1, p2, p3)
            orthocenter = triangle.orthocenter
            return json.dumps({"result": str(orthocenter)})
        except Exception as e:
            return self.handle_exception("compute_orthocenter", e)

    def compute_midpoint_GH(self, point1: List[float], point2: List[float]) -> str:
        r"""Computes the midpoint between two points.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the midpoint. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            midpoint = p1.midpoint(p2)
            return json.dumps({"result": str(midpoint)})
        except Exception as e:
            return self.handle_exception("compute_midpoint_GH", e)

    def compute_point_distance(self, point1: List[float], point2: List[float]) -> str:
        r"""Computes the Euclidean distance between two points.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first point.
            point2 (List[float]): Coordinates [x, y] of the second point.

        Returns:
            str: A JSON string with the "result" field containing the distance.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            distance = p1.distance(p2)
            return json.dumps({"result": str(distance)})
        except Exception as e:
            return self.handle_exception("compute_point_distance", e)

    def check_points_collinear(self, points: List[List[float]]) -> str:
        r"""Checks if a set of points are collinear.

        Args:
            points (List[List[float]]): List of [x, y] coordinates for each point.

        Returns:
            str: A JSON string with the "result" field containing True if
                the points are collinear, False otherwise. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            pts = [sp.Point(float(point[0]), float(point[1])) for point in points]
            collinear = sp.Point.is_collinear(*pts)
            return json.dumps({"result": str(collinear)})
        except Exception as e:
            return self.handle_exception("check_points_collinear", e)

    def compute_angle_between(self, line1_point1: List[float], line1_point2: List[float], 
                             line2_point1: List[float], line2_point2: List[float]) -> str:
        r"""Computes the angle between two lines.

        Args:
            line1_point1 (List[float]): Coordinates [x, y] of the first point of the first line.
            line1_point2 (List[float]): Coordinates [x, y] of the second point of the first line.
            line2_point1 (List[float]): Coordinates [x, y] of the first point of the second line.
            line2_point2 (List[float]): Coordinates [x, y] of the second point of the second line.

        Returns:
            str: A JSON string with the "result" field containing the angle in radians.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            p1 = sp.Point(float(line1_point1[0]), float(line1_point1[1]))
            p2 = sp.Point(float(line1_point2[0]), float(line1_point2[1]))
            p3 = sp.Point(float(line2_point1[0]), float(line2_point1[1]))
            p4 = sp.Point(float(line2_point2[0]), float(line2_point2[1]))
            l1 = sp.Line(p1, p2)
            l2 = sp.Line(p3, p4)
            angle = l1.angle_between(l2)
            return json.dumps({"result": str(angle)})
        except Exception as e:
            return self.handle_exception("compute_angle_between", e)

    def compute_triangle_area_vertices(self, point1: List[float], point2: List[float], point3: List[float]) -> str:
        r"""Computes the area of a triangle given its three vertices.

        Args:
            point1 (List[float]): Coordinates [x, y] of the first vertex.
            point2 (List[float]): Coordinates [x, y] of the second vertex.
            point3 (List[float]): Coordinates [x, y] of the third vertex.

        Returns:
            str: A JSON string with the "result" field containing the area of the triangle.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            p1 = sp.Point(float(point1[0]), float(point1[1]))
            p2 = sp.Point(float(point2[0]), float(point2[1]))
            p3 = sp.Point(float(point3[0]), float(point3[1]))
            triangle = sp.Triangle(p1, p2, p3)
            area = abs(triangle.area)  # Use absolute value to ensure positive area
            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_triangle_area_vertices", e)

    def compute_point_to_line_distance(self, point: List[float], line_point1: List[float], line_point2: List[float]) -> str:
        r"""Computes the shortest distance from a point to a line.

        Args:
            point (List[float]): Coordinates [x, y] of the point.
            line_point1 (List[float]): Coordinates [x, y] of the first point on the line.
            line_point2 (List[float]): Coordinates [x, y] of the second point on the line.

        Returns:
            str: A JSON string with the "result" field containing the shortest distance.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            # Create SymPy Point objects
            p = sp.Point(float(point[0]), float(point[1]))
            p1 = sp.Point(float(line_point1[0]), float(line_point1[1]))
            p2 = sp.Point(float(line_point2[0]), float(line_point2[1]))
            
            # Check if the two points defining the line are the same
            if p1 == p2:
                # If the points are the same, calculate distance to the point
                distance = p.distance(p1)
                return json.dumps({"result": str(distance)})
            
            # Create a line passing through p1 and p2
            line = sp.Line(p1, p2)
            
            # Calculate the distance from point p to the line
            distance = line.distance(p)
            
            return json.dumps({"result": str(distance)})
        except Exception as e:
            return self.handle_exception("compute_point_to_line_distance", e)

    def compute_triangle_area_sides(self, side1: float, side2: float, side3: float) -> str:
        r"""Computes the area of a triangle given the lengths of its three sides using Heron's formula.

        Args:
            side1 (float): Length of the first side of the triangle.
            side2 (float): Length of the second side of the triangle.
            side3 (float): Length of the third side of the triangle.

        Returns:
            str: A JSON string with the "result" field containing the area of the triangle.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            # Convert inputs to float
            a = float(side1)
            b = float(side2)
            c = float(side3)
            
            # Check if the sides can form a triangle (triangle inequality)
            if a + b <= c or a + c <= b or b + c <= a:
                raise ValueError("The given sides cannot form a triangle (triangle inequality violated).")
            
            # Calculate semi-perimeter
            s = (a + b + c) / 2
            
            # Calculate area using Heron's formula
            area = sp.sqrt(s * (s - a) * (s - b) * (s - c))
            
            # Area is already positive due to the square root, but adding abs for consistency
            area = abs(area)
            
            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_triangle_area_sides", e)

    def compute_polygon_area(self, vertices: List[List[float]]) -> str:
        r"""Computes the area of an arbitrary polygon given its vertices.

        This function uses the Shoelace formula (also known as the surveyor's formula or
        Gauss's area formula) to calculate the area of a simple polygon.

        Args:
            vertices (List[List[float]]): A list of points representing the vertices of the polygon.
                Each point should be a list of coordinates [x, y].

        Returns:
            str: A JSON string with the "result" field containing the area of the polygon.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            # Check if we have at least 3 vertices to form a polygon
            if len(vertices) < 3:
                raise ValueError("A polygon must have at least 3 vertices.")
            
            # Convert vertices to SymPy Points
            points = [sp.Point(float(vertex[0]), float(vertex[1])) for vertex in vertices]
            
            # Create a SymPy Polygon
            polygon = sp.Polygon(*points)
            
            # Calculate the area and take absolute value to ensure positive result
            area = abs(polygon.area)
            
            return json.dumps({"result": str(area)})
        except Exception as e:
            return self.handle_exception("compute_polygon_area", e)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of available tools in the toolkit.
        """
        return [
            FunctionTool(self.compute_inner_product),
            FunctionTool(self.compute_line_bisectors),
            FunctionTool(self.compute_centroid),
            FunctionTool(self.compute_orthocenter),
            FunctionTool(self.compute_midpoint_GH),
            FunctionTool(self.compute_point_distance),
            FunctionTool(self.check_points_collinear),
            FunctionTool(self.compute_angle_between),
            FunctionTool(self.compute_triangle_area_vertices),
            FunctionTool(self.compute_point_to_line_distance),
            FunctionTool(self.compute_triangle_area_sides),
            FunctionTool(self.compute_polygon_area),
        ]
