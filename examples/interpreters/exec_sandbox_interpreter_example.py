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
"""ExecSandboxInterpreter examples.

Runs code in ephemeral QEMU microVMs with hardware-level isolation
(KVM on Linux, HVF on macOS). Requires ``pip install 'camel-ai[exec-sandbox]'``
and Python >= 3.12.

A single interpreter instance is shared across all examples. The underlying
scheduler reuses VM instances, and each language gets a persistent REPL
session — variables, imports, and functions survive across ``run()`` calls.
"""

import textwrap

from camel.interpreters import ExecSandboxInterpreter


def main():
    print("ExecSandbox Interpreter Examples")
    print("=" * 40)

    # A single interpreter for all examples — the scheduler boots VMs lazily
    # and reuses them across calls. One persistent REPL per language.
    interpreter = ExecSandboxInterpreter(require_confirm=False)

    try:
        # --- 1. Basic Python execution ---
        print("=== Python Example ===")
        code = textwrap.dedent("""\
            def calculate(a, b):
                return {
                    'sum': a + b,
                    'product': a * b,
                    'difference': a - b,
                }

            result = calculate(10, 5)
            for key, value in result.items():
                print(f"{key}: {value}")
        """)
        print(interpreter.run(code, "python"))
        print()

        # --- 2. Session persistence (state survives across calls) ---
        # `calculate` was defined in step 1 and is still available here.
        print("=== Session Persistence ===")
        interpreter.run("x = 42", "python")
        interpreter.run(
            textwrap.dedent("""\
                def greet(name):
                    s = calculate(1, 2)['sum']
                    return f"Hello, {name}! x={x}, sum={s}"
            """),
            "python",
        )
        # Both `x`, `greet`, and `calculate` are still in scope
        print(interpreter.run('print(greet("CAMEL"))', "python"))
        print()

        # --- 3. JavaScript execution (separate REPL from Python) ---
        print("=== JavaScript Example ===")
        code = textwrap.dedent("""\
            const users = [
                {name: 'Alice', age: 30},
                {name: 'Bob', age: 25},
                {name: 'Charlie', age: 35},
            ];

            const total = users.reduce((s, u) => s + u.age, 0);
            const avgAge = total / users.length;
            console.log(`Average age: ${avgAge}`);
            console.log(`Users: ${users.map(u => u.name).join(', ')}`);
        """)
        print(interpreter.run(code, "javascript"))
        print()

        # --- 4. Shell command execution ---
        print("=== Shell Example ===")
        print(interpreter.run("echo 'Hello from microVM' && uname -a", "bash"))
        print()

        # --- 5. CodeExecutionToolkit integration ---
        print("=== CodeExecutionToolkit Example ===")
        from camel.toolkits import CodeExecutionToolkit

        toolkit = CodeExecutionToolkit(
            sandbox="exec_sandbox",
            require_confirm=False,
        )
        print(
            toolkit.execute_code("print('Hello from CodeExecutionToolkit!')")
        )
        print()

    finally:
        interpreter.close()

    print("All examples completed!")


if __name__ == "__main__":
    main()


"""
===============================================================================
=== Python Example ===
sum: 15
product: 50
difference: 5

=== Session Persistence ===
Hello, CAMEL! x=42, sum=3

=== JavaScript Example ===
Average age: 30
Users: Alice, Bob, Charlie

=== Shell Example ===
Hello from microVM
Linux (none) 6.x.x ...

=== CodeExecutionToolkit Example ===
Hello from CodeExecutionToolkit!

All examples completed!
===============================================================================
"""
