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

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import EnhancedGeometryToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = """You are a helpful math assistant that can perform advanced 
symbolic computations for 2D geometry questions, including conic sections"""

# Set model config
enhanced_geometry_toolkit = EnhancedGeometryToolkit()
tools = enhanced_geometry_toolkit.get_tools()
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Test cases
test_cases = [
    # Test 1: Basic Triangle Area (same as original toolkit)
    """A triangle has vertices at coordinates (2, 3), (5, 7), and (8, 1).
    Calculate the area of the triangle""",
    # Test 2: Distance Calculation
    """Calculate the distance between the point (3, 4) and the line passing 
    through points (0, 0) and (5, 5)""",
    # Test 3: Vector Operations
    """Find the dot product of vectors [2, 3] and [4, 5]""",
    # Test 4: Midpoint and Perpendicular Bisector
    """Find the midpoint of the line segment from (2, 3) to (8, 9) and the
    equation of its perpendicular bisector""",
    # Test 5: Collinearity Check
    """Determine if the points (1, 1), (2, 2), and (3, 3) are collinear""",
    # Test 6: Conic Section - Circle
    """Find the equation of a circle with center at (3, 4) and radius 5""",
    # Test 7: Conic Section - Ellipse Properties
    """Find the foci of an ellipse with semi-major axis 5 and semi-minor 
    axis 3, centered at the origin""",
    # Test 8: Conic Section - Parabola
    """Find the equation of a parabola with vertex at (2, 3) and focus 
    at (2, 5)""",
    # Test 9: Conic Section - Hyperbola
    """Find the asymptotes of a hyperbola with semi-major axis 4 and 
    semi-minor axis 3, centered at the origin""",
    # Test 10: Complex Problem - Intersection
    """How many points of intersection are there between a circle with 
    center (0, 0) and radius 5, and another circle with center (8, 0) 
    and radius 4?""",
    # Test 11: Polygon Area
    """Calculate the area of a quadrilateral with vertices at (0, 0), 
    (4, 0), (4, 3), and (0, 3)""",
    # Test 12: Tangent Line
    """Find the equation of the tangent line to the circle x² + y² = 25 
    at the point (3, 4)""",
]

# Run tests
for i, test_case in enumerate(test_cases, 1):
    print(f"\n=== Test {i}: {test_case.splitlines()[0]} ===")
    response = camel_agent.step(test_case)
    print("Tool calls:")
    print(response.info['tool_calls'])

print("\n=== All tests completed ===")
