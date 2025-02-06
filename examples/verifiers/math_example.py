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
"""Example usage of math verifier with Gurobi."""

import os
import sys

from camel.verifiers import DomainVerifier

# Add project root to Python path if not installed
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
if project_root not in sys.path:
    sys.path.append(project_root)


def main():
    # Example problems
    data = {
        "question": [
            "Solve: 2x + 3 = 7",
            "Maximize: z = 3x + 4y subject to: x + y <= 10, x >= 0, y >= 0",
        ],
        "solution": ["x = 2", "x = 6, y = 4"],
        "answer": [
            "2",
            "36",  # Optimal objective value
        ],
    }

    verified_data = DomainVerifier.verify(
        domain="math",
        data=data,
        criteria={
            "numerical_tolerance": 1e-8,
            "verify_steps": True,
            "check_feasibility": True,
            "verify_optimality": True,
        },
    )

    # Print detailed results
    for item in verified_data:
        print("\nVerification Results:")
        print("-" * 50)
        print(f"Question: {item['question']}")
        print(f"Solution: {item['solution']}")
        print(f"Expected Answer: {item['answer']}")
        print(f"Correct: {item['correct']}")

        result = item['verification_result']
        print("\nDetails:")
        print(f"Score: {result['score']:.2f}")
        print(f"Passed: {result['passed']}")
        print(f"Feedback: {result['feedback']}")

        if 'details' in result:
            print("\nComponent Scores:")
            for key, value in result['details'].items():
                print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
