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
from typing import List
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from camel.verifiers.programming_verifier import ProgrammingVerifier

# Create a ProgrammingVerifier instance
verifier = ProgrammingVerifier(timeout=30.0)
asyncio.run(verifier.setup())

# Define the solution to the Two Sum problem, where we call it "final_answer"
solution_code = """
from typing import List

def twoSum(nums: List[int], target: int) -> List[int]:
    # HashMap to store number:index pairs
    num_to_index = {}
    
    for i, num in enumerate(nums):
        # Calculate the complement we need to find
        complement = target - num
        
        # If the complement exists in our hash map, we found our pair
        if complement in num_to_index:
            return [num_to_index[complement], i]
        
        # Otherwise, add the current number and its index to the hash map
        num_to_index[num] = i
    
    # If no solution is found, return None
    return None

# Create a wrapper function to match the test case format
def candidate(nums, target):
    return twoSum(nums, target)
"""

# Define the test cases, or we called in "rationale"
test_cases = """def check(candidate):
    assert candidate(nums = [2,7,11,15], target = 9) == [0,1]
    assert candidate(nums = [3,2,4], target = 6) == [1,2]
    assert candidate(nums = [3,3], target = 6) == [0,1]
    assert candidate(nums = [2,4,6,8,10,12,14,16,18,20,22,24,26,28,30], target = 58) == [13, 14]
    assert candidate(nums = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000], target = 1700) == [7, 8]
    assert candidate(nums = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50], target = 100) == None
    assert candidate(nums = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19], target = 38) == None
"""

# Verify the solution against the test cases
result = asyncio.run(
    verifier.verify(solution=solution_code, reference_answer=test_cases)
)
print(f"Verification result (correct solution): {result}")

'''output:
Verification result (correct solution): status=<VerificationOutcome.SUCCESS: 'success'> result='All test cases passed' duration=0.029468059539794922 timestamp=datetime.datetime(2025, 4, 21, 16, 44, 22, 895100) metadata={'stdout': '', 'stderr': '', 'return_code': 0, 'attempt': 1} error_message=None
'''








# Define an incorrect solution to demonstrate failure
incorrect_solution = """
from typing import List

def twoSum(nums: List[int], target: int) -> List[int]:
    # This solution is incorrect - it always returns the first two indices
    return [0, 1]

# Create a wrapper function to match the test case format
def candidate(nums, target):
    return twoSum(nums, target)
"""

# Define the test cases for the incorrect solution (same as before)
incorrect_test_cases = """def check(candidate):
    assert candidate(nums = [2,7,11,15], target = 9) == [0,1]
    assert candidate(nums = [3,2,4], target = 6) == [1,2]
    assert candidate(nums = [3,3], target = 6) == [0,1]
    assert candidate(nums = [2,4,6,8,10,12,14,16,18,20,22,24,26,28,30], target = 58) == [13, 14]
    assert candidate(nums = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000], target = 1700) == [7, 8]
"""

# Verify the incorrect solution
result_incorrect = asyncio.run(
    verifier.verify(solution=incorrect_solution, reference_answer=incorrect_test_cases)
)
print(f"Verification result (incorrect solution): {result_incorrect}")

'''output:
Verification result (incorrect solution): status=<VerificationOutcome.FAILURE: 'failure'> result='' duration=0.0201261043548584 timestamp=datetime.datetime(2025, 4, 21, 16, 44, 22, 916130) metadata={'stdout': '', 'stderr': 'Traceback (most recent call last):\n  File "/tmp/tmps3f4uwpb.py", line 20, in <module>\n    check(candidate)\n  File "/tmp/tmps3f4uwpb.py", line 15, in check\n    assert candidate(nums = [3,2,4], target = 6) == [1,2]\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError\n', 'return_code': 1, 'attempt': 1} error_message='Test cases failed: Traceback (most recent call last):\n  File "/tmp/tmps3f4uwpb.py", line 20, in <module>\n    check(candidate)\n  File "/tmp/tmps3f4uwpb.py", line 15, in check\n    assert candidate(nums = [3,2,4], target = 6) == [1,2]\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError\n'
'''




# Clean up the verifier
asyncio.run(verifier.cleanup())

# Example of using the format_test_cases utility
print("\nExample of formatting test cases from dictionary format:")
test_cases_dict = [
    {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
    {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
    {"input": {"nums": [3, 3], "target": 6}, "expected": [0, 1]}
]

formatted_test_cases = ProgrammingVerifier.format_test_cases(test_cases_dict)
print(formatted_test_cases)

'''output:
Example of formatting test cases from dictionary format:
def check(candidate):
    assert candidate(nums = [2, 7, 11, 15], target = 9) == [0, 1]
    assert candidate(nums = [3, 2, 4], target = 6) == [1, 2]
    assert candidate(nums = [3, 3], target = 6) == [0, 1]
'''