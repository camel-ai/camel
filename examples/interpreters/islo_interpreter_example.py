# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
import textwrap

from camel.interpreters import IsloInterpreter


def main():
    r"""Run Islo interpreter examples."""
    if not os.environ.get("ISLO_API_KEY"):
        print(
            "Skipping Islo interpreter example: set the ISLO_API_KEY "
            "environment variable to run it. Get a key from "
            "https://app.islo.dev/api-keys"
        )
        return

    print("Islo Interpreter Examples")
    print("=" * 40)

    # The sandbox is created lazily on the first execution and deleted
    # by cleanup() since this interpreter creates its own sandbox.
    interpreter = IsloInterpreter(require_confirm=False)

    print("=== Python Example ===")
    code = textwrap.dedent("""
    def calculate(a, b):
        return {
            'sum': a + b,
            'product': a * b,
            'difference': a - b
        }

    result = calculate(10, 5)
    for key, value in result.items():
        print(f"{key}: {value}")
    """)
    print(interpreter.run(code, "python"))
    print()

    print("=== Bash Example ===")
    print(interpreter.run("echo 'Hello from Islo!' && uname -a", "bash"))
    print()

    print("=== Command Example ===")
    print(interpreter.execute_command("python3 --version && node --version"))
    print()

    interpreter.cleanup()
    print("All examples completed!")


if __name__ == "__main__":
    main()
