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
import asyncio

from camel.verifiers import PhysicsVerifier

verifier = PhysicsVerifier()
asyncio.run(verifier.setup(uv=True))

numpy_test_code = r"""
import numpy as np
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
result = np.dot(a, b)
print(f"{result} ")
"""

basic_test_code = r"""
import sympy as sp
Q = 25000  
T = 373.15 
ΔS = Q / T
result = ΔS
unit="J/K"
print(f"{result} {unit}")
"""

expression_test_code = r"""
import sympy as sp
theta = sp.symbols('theta', real=True, positive=True)
f = sp.cos(theta) * sp.sin(theta)**3
df_dtheta = sp.diff(f, theta)
critical_points = sp.solve(sp.Eq(df_dtheta, 0), theta)
theta_candidates = [cp for cp in critical_points if cp > 0 and cp < sp.pi/2]
result = sp.simplify(theta_candidates[0])
unit="rads"
print(f"{result} {unit}")
"""

scaling_test_code = r"""
import sympy as sp
n, hbar = sp.symbols('n hbar')
m_val = 1.0e-3  # in kg
v_val = 1.0e-2  # in m/s
L_val = 1.0e-2  # in m
hbar_val = 1.054571817e-34  # in J s
n_expr = (m_val * L_val * v_val) / (sp.pi * hbar)
n_numeric = sp.N(n_expr.subs(hbar, hbar_val))
n_coefficient = int(round(n_numeric / 1e26))
result = n_coefficient
unit="10^26"
print(f"{result} {unit}")
"""

conversion_test_code = r"""
import sympy as sp
k = 1.38e-23  # Boltzmann constant in J/K
T = 25 + 273.15  # Temperature in Kelvin
molar_mass_N2 = 28e-3  # Molar mass of N2 in kg/mol
m = molar_mass_N2 / 6.022e23  # Mass of one N2 molecule in kg
mean_speed = sp.sqrt((8 * k * T) / (sp.pi * m))
result = mean_speed.evalf()  # Evaluate to get a numerical result
unit="m/s"
print(f"{result} {unit}")
"""

dollar_enclosed_units_test_code = r"""
import sympy as sp
Q = sp.symbols('Q')
q1 = 6.0e-6   # +6.0 μC at x = 8.0 m
q2 = -4.0e-6  # -4.0 μC at x = 16.0 m
x1 = 8.0
x2 = 16.0
x3 = 24.0
eqn = sp.Eq(q1/x1**2 + q2/x2**2 + Q/x3**2, 0)
solution = sp.solve(eqn, Q)
result = solution[0] * 1e6
unit="$\\mu \\mathrm{C}$"
print(f"{result} {unit}")
"""

# Make sure PhysicsVerifier works for test cases for pythonVerifier
result = asyncio.run(
    verifier.verify(solution=numpy_test_code, reference_answer="32 ")
)
print(f"Result: {result}")  # should pass
result = asyncio.run(
    verifier.verify(solution=numpy_test_code, reference_answer="40")
)
print(f"Result: {result}")  # should fail

# A simple physics test case with same value and unit for solutoin and
# reference answer
result = asyncio.run(
    verifier.verify(solution=basic_test_code, reference_answer="67 J/K")
)
print(f"Result: {result}")

# We have expression "pi" in the solution
result = asyncio.run(
    verifier.verify(
        solution=expression_test_code, reference_answer="pi/3 rads"
    )
)
print(f"Result: {result}")

# There is a 10^26 scaling factor
result = asyncio.run(
    verifier.verify(solution=scaling_test_code, reference_answer="3 10^26")
)
print(f"Result: {result}")

# The code will output answer in m/s, but we expect it to be in km/s.
# The verifier should convert the answer to km/s.
result = asyncio.run(
    verifier.verify(
        solution=conversion_test_code, reference_answer="0.47 km/s"
    )
)
print(f"Result: {result}")

# The units are enclosed by dollar signs with spacing in between
result = asyncio.run(
    verifier.verify(
        solution=dollar_enclosed_units_test_code,
        reference_answer="-45 $\\mu \\mathrm{C}$",
    )
)
print(f"Result: {result}")


asyncio.run(verifier.cleanup())
