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

    def __init__(self, log_level=logging.INFO):
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
            v1 = sp.Matrix(vector1)
            v2 = sp.Matrix(vector2)

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

    def create_point(self, x: float, y: float) -> str:
        r"""Creates a Sympy Point with the given x, y coordinates.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            point = sp.Point(x, y)
            return json.dumps({"result": str(point)})
        except Exception as e:
            return self.handle_exception("create_point", e)

    def create_line(self, point1: str, point2: str) -> str:
        r"""Creates a line passing through two points.

        Args:
            point1 (str): First point in the format "Point(x, y)".
            point2 (str): Second point in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Line. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.parse_expr(point1)
            p2 = sp.parse_expr(point2)
            line = sp.Line(p1, p2)
            return json.dumps({"result": str(line)})
        except Exception as e:
            return self.handle_exception("create_line", e)

    def create_segment(self, point1: str, point2: str) -> str:
        r"""Creates a line segment between two points.

        Args:
            point1 (str): First point in the format "Point(x, y)".
            point2 (str): Second point in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Segment. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.parse_expr(point1)
            p2 = sp.parse_expr(point2)
            segment = sp.Segment(p1, p2)
            return json.dumps({"result": str(segment)})
        except Exception as e:
            return self.handle_exception("create_segment", e)

    def create_circle(self, center: str, radius: float) -> str:
        r"""Creates a circle with given center and radius.

        Args:
            center (str): Center point in the format "Point(x, y)".
            radius (float): Radius of the circle.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Circle. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            center_point = sp.parse_expr(center)
            circle = sp.Circle(center_point, radius)
            return json.dumps({"result": str(circle)})
        except Exception as e:
            return self.handle_exception("create_circle", e)

    def create_ellipse(self, center: str, hradius: float, vradius: float) -> str:
        r"""Creates an ellipse with given center and radii.

        Args:
            center (str): Center point in the format "Point(x, y)".
            hradius (float): Horizontal radius of the ellipse.
            vradius (float): Vertical radius of the ellipse.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Ellipse. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            center_point = sp.parse_expr(center)
            ellipse = sp.Ellipse(center_point, hradius, vradius)
            return json.dumps({"result": str(ellipse)})
        except Exception as e:
            return self.handle_exception("create_ellipse", e)

    def create_polygon(self, vertices: List[str]) -> str:
        r"""Creates a polygon from a list of vertices.

        Args:
            vertices (List[str]): List of points in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Polygon. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            vertex_points = [sp.parse_expr(v) for v in vertices]
            polygon = sp.Polygon(*vertex_points)
            return json.dumps({"result": str(polygon)})
        except Exception as e:
            return self.handle_exception("create_polygon", e)

    def create_triangle(self, point1: str, point2: str, point3: str) -> str:
        r"""Creates a triangle from three points.

        Args:
            point1 (str): First point in the format "Point(x, y)".
            point2 (str): Second point in the format "Point(x, y)".
            point3 (str): Third point in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the Triangle. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.parse_expr(point1)
            p2 = sp.parse_expr(point2)
            p3 = sp.parse_expr(point3)
            triangle = sp.Triangle(p1, p2, p3)
            return json.dumps({"result": str(triangle)})
        except Exception as e:
            return self.handle_exception("create_triangle", e)

    def compute_line_bisectors(self, line: str) -> str:
        r"""Computes the perpendicular bisector of a line segment.

        Args:
            line (str): Line segment in the format "Segment(Point(x1, y1), Point(x2, y2))".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the perpendicular bisector. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            line_segment = sp.parse_expr(line)
            bisector = line_segment.perpendicular_bisector()
            return json.dumps({"result": str(bisector)})
        except Exception as e:
            return self.handle_exception("compute_line_bisectors", e)

    def compute_centroid(self, triangle: str) -> str:
        r"""Computes the centroid of a triangle.

        Args:
            triangle (str): Triangle in the format "Triangle(Point(x1, y1), Point(x2, y2), Point(x3, y3))".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the centroid point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            tri = sp.parse_expr(triangle)
            centroid = tri.centroid
            return json.dumps({"result": str(centroid)})
        except Exception as e:
            return self.handle_exception("compute_centroid", e)

    def compute_orthocenter(self, triangle: str) -> str:
        r"""Computes the orthocenter of a triangle.

        Args:
            triangle (str): Triangle in the format "Triangle(Point(x1, y1), Point(x2, y2), Point(x3, y3))".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the orthocenter point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            tri = sp.parse_expr(triangle)
            orthocenter = tri.orthocenter
            return json.dumps({"result": str(orthocenter)})
        except Exception as e:
            return self.handle_exception("compute_orthocenter", e)

    def compute_midpoint_GH(self, point1: str, point2: str) -> str:
        r"""Computes the midpoint between two points.

        Args:
            point1 (str): First point in the format "Point(x, y)".
            point2 (str): Second point in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the midpoint. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.parse_expr(point1)
            p2 = sp.parse_expr(point2)
            midpoint = p1.midpoint(p2)
            return json.dumps({"result": str(midpoint)})
        except Exception as e:
            return self.handle_exception("compute_midpoint_GH", e)

    def compute_point_distance(self, point1: str, point2: str) -> str:
        r"""Computes the Euclidean distance between two points.

        Args:
            point1 (str): First point in the format "Point(x, y)".
            point2 (str): Second point in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing the distance.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            p1 = sp.parse_expr(point1)
            p2 = sp.parse_expr(point2)
            distance = p1.distance(p2)
            return json.dumps({"result": str(distance)})
        except Exception as e:
            return self.handle_exception("compute_point_distance", e)

    def check_points_collinear(self, points: List[str]) -> str:
        r"""Checks if a set of points are collinear.

        Args:
            points (List[str]): List of points in the format "Point(x, y)".

        Returns:
            str: A JSON string with the "result" field containing True if
                the points are collinear, False otherwise. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            pts = [sp.parse_expr(p) for p in points]
            collinear = sp.Point.is_collinear(*pts)
            return json.dumps({"result": str(collinear)})
        except Exception as e:
            return self.handle_exception("check_points_collinear", e)

    def compute_angle_between(self, line1: str, line2: str) -> str:
        r"""Computes the angle between two lines.

        Args:
            line1 (str): First line in the format "Line(Point(x1, y1), Point(x2, y2))".
            line2 (str): Second line in the format "Line(Point(x1, y1), Point(x2, y2))".

        Returns:
            str: A JSON string with the "result" field containing the angle in radians.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            l1 = sp.parse_expr(line1)
            l2 = sp.parse_expr(line2)
            angle = l1.angle_between(l2)
            return json.dumps({"result": str(angle)})
        except Exception as e:
            return self.handle_exception("compute_angle_between", e)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                              the available tools.
        """
        return [
            FunctionTool(self.compute_inner_product),
            FunctionTool(self.create_point),
            FunctionTool(self.create_line),
            FunctionTool(self.create_segment),
            FunctionTool(self.create_circle),
            FunctionTool(self.create_ellipse),
            FunctionTool(self.create_polygon),
            FunctionTool(self.create_triangle),
            FunctionTool(self.compute_line_bisectors),
            FunctionTool(self.compute_centroid),
            FunctionTool(self.compute_orthocenter),
            FunctionTool(self.compute_midpoint_GH),
            FunctionTool(self.compute_point_distance),
            FunctionTool(self.check_points_collinear),
            FunctionTool(self.compute_angle_between),
        ]
