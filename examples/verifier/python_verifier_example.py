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

from camel.verifiers import PythonVerifier, VerifierInput

verifier = PythonVerifier(required_packages=["numpy", "pandas"])
asyncio.run(verifier._setup())

numpy_test_code = """
import numpy as np
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
result = np.dot(a, b)
print(result)
"""

response = VerifierInput(llm_response=numpy_test_code, ground_truth="40")
result = asyncio.run(verifier._verify_implementation(response))

print(f"Result: {result}")

asyncio.run(verifier.cleanup())
