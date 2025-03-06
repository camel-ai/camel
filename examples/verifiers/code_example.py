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
from pprint import pprint

from camel.verifiers import CodeVerifier, VerifierInput


async def run_example_1():
    print("\nExample 1: Basic Function Test")
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
def add(a, b): 
    return a + b
    
print(add(1, 2))
print(add(-1, 1))
"""
    verifier_input = VerifierInput(llm_response=code, ground_truth="3\n0")
    result = await verifier.verify(verifier_input)
    pprint(
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        }
    )

    await verifier.cleanup()


async def run_example_2():
    print("\nExample 2: Multiple Solutions")
    verifier = CodeVerifier()
    await verifier.setup()

    codes = [
        """
def factorial(n): 
    return 1 if n <= 1 else n * factorial(n-1)
    
print(factorial(5))
""",
        """
def factorial(n): 
    return n * factorial(n-1) if n > 1 else 1
    
print(factorial(5))
""",
    ]

    for i, code in enumerate(codes):
        verifier_input = VerifierInput(llm_response=code, ground_truth="120")
        result = await verifier.verify(verifier_input)
        print(
            f"Solution {i+1} result:",
            {"status": result.status.value, "result": result.result},
        )

    await verifier.cleanup()


async def run_example_3():
    print("\nExample 3: External Imports")
    verifier = CodeVerifier()
    await verifier.setup()

    code = """
import numpy as np
def process_array():
    arr = np.array([1, 2, 3])
    return arr.mean()
    
print(process_array())
"""
    verifier_input = VerifierInput(llm_response=code, ground_truth="2.0")
    result = await verifier.verify(verifier_input)
    print(
        "Result:",
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        },
    )

    await verifier.cleanup()


async def run_example_4():
    print("\nExample 4: Multi-threaded verification")
    verifier = CodeVerifier(max_parallel=2)
    await verifier.setup()

    codes = [
        """
def square(x):
    return x * x
result = square(4)
print(result)
""",
        """
def cube(x):
    return x * x * x
result = cube(3)
print(result)
""",
        """
def double(x):
    return x + x
result = double(5)
print(result)
""",
        """
def half(x):
    return x / 2
result = half(8)
print(result)
""",
    ]
    expected_outputs = ["16", "27", "10", "4.0"]

    inputs = [
        VerifierInput(llm_response=code, ground_truth=expected)
        for code, expected in zip(codes, expected_outputs)
    ]

    # Use batch verification
    results = await verifier.verify_batch(inputs)

    # Display results
    for i, result in enumerate(results):
        print(
            f"\nFunction {i+1} result:",
            {"status": result.status.value, "result": result.result},
        )

    await verifier.cleanup()


async def run_example_5():
    print("\nExample 5: Syntax Error")
    verifier = CodeVerifier()
    await verifier.setup()

    code = "def broken_function(x: return x"  # Syntax error
    verifier_input = VerifierInput(llm_response=code, ground_truth=None)
    result = await verifier.verify(verifier_input)
    print(
        "Result:",
        {
            "status": result.status.value,
            "result": result.result,
            "error": result.error_message,
        },
    )

    await verifier.cleanup()


async def main():
    await run_example_1()
    await run_example_2()
    await run_example_3()
    await run_example_4()
    await run_example_5()


if __name__ == "__main__":
    asyncio.run(main())

"""
Example 1: Basic Function Test
{'error': None, 'result': '3\n0\n', 'status': 'success'}

Example 2: Multiple Solutions
Solution 1 result: {'status': 'success', 'result': '120\n'}
Solution 2 result: {'status': 'success', 'result': '120\n'}

Example 3: External Imports
Result: {'status': 'success', 'result': '2.0\n', 'error': None}

Example 4: Multi-threaded verification

Function 1 result: {'status': 'success', 'result': '16\n'}

Function 2 result: {'status': 'success', 'result': '27\n'}

Function 3 result: {'status': 'success', 'result': '10\n'}

Function 4 result: {'status': 'success', 'result': '4.0\n'}

Example 5: Syntax Error
======stderr======
File "/var/folders/rt/x73bp_zj6rl9vm2jc06jd5zm0000gn/T/tmp8vjh5z1s.py", line 1
    def broken_function(x: return x
                           ^^^^^^
SyntaxError: invalid syntax

==================
Result: {
    'status': 'success', 
    'result': '(Execution failed with return code 1)', 
    'error': None}
"""
