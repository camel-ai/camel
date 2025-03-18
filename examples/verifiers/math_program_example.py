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

from camel.verifiers import CodeVerifier, VerifierInput


async def test_matrix_operations():
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
import numpy as np

def matrix_multiply(A, B):
    return np.dot(A, B)

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
result = matrix_multiply(A, B)
print(result)
"""

    print("\nTesting Matrix Operations:")
    verifier_input = VerifierInput(
        llm_response=code, ground_truth="[[19 22]\n [43 50]]"
    )

    result = await verifier.verify(verifier_input)
    print(
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        }
    )

    await verifier.cleanup()


async def test_linear_system_solver():
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
import numpy as np

def solve_linear_system(A, b):
    return np.linalg.solve(A, b)

A = np.array([[2, 1], [1, 3]])
b = np.array([4, 5])
result = solve_linear_system(A, b)
print(result)
"""

    print("\nTesting Linear System Solver:")
    verifier_input = VerifierInput(llm_response=code, ground_truth="[1.4 1.2]")

    result = await verifier.verify(verifier_input)
    print(
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        }
    )

    await verifier.cleanup()


async def test_eigenvalue_decomposition():
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
import numpy as np

def compute_eigenvalues(A):
    eigenvalues, _ = np.linalg.eig(A)
    return np.sort(eigenvalues)

A = np.array([[4, 2], [1, 3]])
result = compute_eigenvalues(A)
print(result)
"""

    print("\nTesting Eigenvalue Decomposition:")
    verifier_input = VerifierInput(llm_response=code, ground_truth="[2. 5.]")

    result = await verifier.verify(verifier_input)
    print(
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        }
    )

    await verifier.cleanup()


async def test_svd():
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
import numpy as np

def compute_svd(A):
    U, S, Vt = np.linalg.svd(A)
    return S

A = np.array([[1, 2], [3, 4], [5, 6]])
result = compute_svd(A)
print(result)
"""

    print("\nTesting SVD:")
    verifier_input = VerifierInput(
        llm_response=code, ground_truth="[9.52551809 0.51430058]"
    )

    result = await verifier.verify(verifier_input)
    print(
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        }
    )

    await verifier.cleanup()


async def test_numerical_integration():
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
import numpy as np
from scipy import integrate

def integrate_function(a, b):
    # Integrate sin(x^2) from a to b
    def f(x):
        return np.sin(x**2)

    result, _ = integrate.quad(f, a, b)
    return result

a, b = 0, 1
result = integrate_function(a, b)
print(f"{result:.16f}")
"""

    print("\nTesting Numerical Integration:")
    verifier_input = VerifierInput(
        llm_response=code, ground_truth="0.3102683017233811"
    )

    result = await verifier.verify(verifier_input)
    print(
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        }
    )

    await verifier.cleanup()


async def main():
    await test_matrix_operations()
    await test_linear_system_solver()
    await test_eigenvalue_decomposition()
    await test_svd()
    await test_numerical_integration()


if __name__ == "__main__":
    asyncio.run(main())

"""
Testing Matrix Operations:
{'status': 'success', 'result': '[[19 22]\n [43 50]]\n', 'error': None}

Testing Linear System Solver:
{'status': 'success', 'result': '[1.4 1.2]\n', 'error': None}

Testing Eigenvalue Decomposition:
{'status': 'success', 'result': '[2. 5.]\n', 'error': None}

Testing SVD:
{'status': 'success', 'result': '[9.52551809 0.51430058]\n', 'error': None}

Testing Numerical Integration:
{'status': 'success', 'result': '0.3102683017233811\n', 'error': None}
"""
