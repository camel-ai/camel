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

from camel.verifiers import PythonVerifier

verifier = PythonVerifier(required_packages=["numpy"])
asyncio.run(verifier.setup(uv=True))

numpy_test_code = """
import numpy as np
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
result = np.dot(a, b)
print(result)
"""


# Since the output of the above numpy code evaluates to 32,
# we expect the verification outcome to be a success.
result = asyncio.run(
    verifier.verify(solution=numpy_test_code, reference_answer="32")
)
print(f"Result: {result}")

result = asyncio.run(
    verifier.verify(solution=numpy_test_code, reference_answer="40")
)

# Now we expect the VerificationOutcome to be a failure,
# because the answer is wrong.
print(f"Result: {result}")

asyncio.run(verifier.cleanup())
