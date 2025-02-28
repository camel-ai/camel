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
from typing import List, Optional, Tuple

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
        self, vector1: Tuple[float, float], vector2: Tuple[float, float]
    ) -> str:
        r"""Computes the inner (dot) product of two vectors.

        Args:
            vector1 (Tuple[float, float]): The first vector as a tuple of floats.
            vector2 (Tuple[float, float]): The second vector as a tuple of floats.

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
            # Convert the tuples into sympy Matrix objects (column vectors)
            v1 = sp.Matrix([vector1[0], vector1[1]])
            v2 = sp.Matrix([vector2[0], vector2[1]])

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

    def compute_line_bisectors(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> str:
        r"""Computes the perpendicular bisector of a line segment.

        Args:
            point1 (Tuple[float, float]): Coordinates (x, y) of the first point.
            point2 (Tuple[float, float]): Coordinates (x, y) of the second point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the perpendicular bisector. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(point1[0], point1[1])
            p2 = sp.Point(point2[0], point2[1])
            line_segment = sp.Segment(p1, p2)
            bisector = line_segment.perpendicular_bisector()
            return json.dumps({"result": str(bisector)})
        except Exception as e:
            return self.handle_exception("compute_line_bisectors", e)

    def compute_centroid(self, point1: Tuple[float, float], point2: Tuple[float, float], point3: Tuple[float, float]) -> str:
        r"""Computes the centroid of a triangle.

        Args:
            point1 (Tuple[float, float]): Coordinates (x, y) of the first point.
            point2 (Tuple[float, float]): Coordinates (x, y) of the second point.
            point3 (Tuple[float, float]): Coordinates (x, y) of the third point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the centroid point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(point1[0], point1[1])
            p2 = sp.Point(point2[0], point2[1])
            p3 = sp.Point(point3[0], point3[1])
            triangle = sp.Triangle(p1, p2, p3)
            centroid = triangle.centroid
            return json.dumps({"result": str(centroid)})
        except Exception as e:
            return self.handle_exception("compute_centroid", e)

    def compute_orthocenter(self, point1: Tuple[float, float], point2: Tuple[float, float], point3: Tuple[float, float]) -> str:
        r"""Computes the orthocenter of a triangle.

        Args:
            point1 (Tuple[float, float]): Coordinates (x, y) of the first point.
            point2 (Tuple[float, float]): Coordinates (x, y) of the second point.
            point3 (Tuple[float, float]): Coordinates (x, y) of the third point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the orthocenter point. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(point1[0], point1[1])
            p2 = sp.Point(point2[0], point2[1])
            p3 = sp.Point(point3[0], point3[1])
            triangle = sp.Triangle(p1, p2, p3)
            orthocenter = triangle.orthocenter
            return json.dumps({"result": str(orthocenter)})
        except Exception as e:
            return self.handle_exception("compute_orthocenter", e)

    def compute_midpoint_GH(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> str:
        r"""Computes the midpoint between two points.

        Args:
            point1 (Tuple[float, float]): Coordinates (x, y) of the first point.
            point2 (Tuple[float, float]): Coordinates (x, y) of the second point.

        Returns:
            str: A JSON string with the "result" field containing the string
                representation of the midpoint. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            p1 = sp.Point(point1[0], point1[1])
            p2 = sp.Point(point2[0], point2[1])
            midpoint = p1.midpoint(p2)
            return json.dumps({"result": str(midpoint)})
        except Exception as e:
            return self.handle_exception("compute_midpoint_GH", e)

    def compute_point_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> str:
        r"""Computes the Euclidean distance between two points.

        Args:
            point1 (Tuple[float, float]): Coordinates (x, y) of the first point.
            point2 (Tuple[float, float]): Coordinates (x, y) of the second point.

        Returns:
            str: A JSON string with the "result" field containing the distance.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            p1 = sp.Point(point1[0], point1[1])
            p2 = sp.Point(point2[0], point2[1])
            distance = p1.distance(p2)
            return json.dumps({"result": str(distance)})
        except Exception as e:
            return self.handle_exception("compute_point_distance", e)

    def check_points_collinear(self, points: List[Tuple[float, float]]) -> str:
        r"""Checks if a set of points are collinear.

        Args:
            points (List[Tuple[float, float]]): List of (x, y) coordinates for each point.

        Returns:
            str: A JSON string with the "result" field containing True if
                the points are collinear, False otherwise. If an error occurs,
                the JSON string will include an "error" field with
                the corresponding error message.
        """
        try:
            pts = [sp.Point(point[0], point[1]) for point in points]
            collinear = sp.Point.is_collinear(*pts)
            return json.dumps({"result": str(collinear)})
        except Exception as e:
            return self.handle_exception("check_points_collinear", e)

    def compute_angle_between(self, line1_point1: Tuple[float, float], line1_point2: Tuple[float, float], 
                             line2_point1: Tuple[float, float], line2_point2: Tuple[float, float]) -> str:
        r"""Computes the angle between two lines.

        Args:
            line1_point1 (Tuple[float, float]): Coordinates (x, y) of the first point of the first line.
            line1_point2 (Tuple[float, float]): Coordinates (x, y) of the second point of the first line.
            line2_point1 (Tuple[float, float]): Coordinates (x, y) of the first point of the second line.
            line2_point2 (Tuple[float, float]): Coordinates (x, y) of the second point of the second line.

        Returns:
            str: A JSON string with the "result" field containing the angle in radians.
                If an error occurs, the JSON string will include an "error"
                field with the corresponding error message.
        """
        try:
            p1 = sp.Point(line1_point1[0], line1_point1[1])
            p2 = sp.Point(line1_point2[0], line1_point2[1])
            p3 = sp.Point(line2_point1[0], line2_point1[1])
            p4 = sp.Point(line2_point2[0], line2_point2[1])
            l1 = sp.Line(p1, p2)
            l2 = sp.Line(p3, p4)
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
            FunctionTool(self.compute_line_bisectors),
            FunctionTool(self.compute_centroid),
            FunctionTool(self.compute_orthocenter),
            FunctionTool(self.compute_midpoint_GH),
            FunctionTool(self.compute_point_distance),
            FunctionTool(self.check_points_collinear),
            FunctionTool(self.compute_angle_between),
        ]
