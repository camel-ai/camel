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
import textwrap

from camel.interpreters import MicrosandboxInterpreter


def test_python_example():
    """Test Python code execution."""
    print("=== Python Example ===")
    interpreter = MicrosandboxInterpreter(
        require_confirm=False,
        server_url="http://127.0.0.1:5555",
        namespace="default",
        sandbox_name="python-test",
    )

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

    result = interpreter.run(code, "python")
    print(result)
    print()


def test_javascript_example():
    """Test JavaScript code execution."""
    print("=== JavaScript Example ===")
    interpreter = MicrosandboxInterpreter(
        require_confirm=False,
        server_url="http://127.0.0.1:5555",
        namespace="default",
        sandbox_name="js-test",
    )

    code = textwrap.dedent("""
    const users = [
        {name: 'Alice', age: 30},
        {name: 'Bob', age: 25},
        {name: 'Charlie', age: 35}
    ];
    
    const avgAge = users.reduce((sum, user) => sum + user.age, 0) / 
                   users.length;
    console.log(`Average age: ${avgAge}`);
    console.log(`Users: ${users.map(u => u.name).join(', ')}`);
    """)

    result = interpreter.run(code, "javascript")
    print(result)
    print()


def test_shell_example():
    """Test shell commands."""
    print("=== Shell Example ===")
    interpreter = MicrosandboxInterpreter(
        require_confirm=False,
        server_url="http://127.0.0.1:5555",
        namespace="default",
        sandbox_name="shell-test",
    )

    # Test directory operations
    interpreter.run("mkdir -p /tmp/mydir", "bash")
    interpreter.run("echo 'Hello World' > /tmp/mydir/hello.txt", "bash")

    result = interpreter.execute_command("ls -la /tmp/mydir")
    print("Directory listing:", result)

    result = interpreter.execute_command("cat /tmp/mydir/hello.txt")
    print("File content:", result)
    print()


def test_package_example():
    """Test what's available without pip installation."""
    print("=== Available Packages Test ===")
    interpreter = MicrosandboxInterpreter(
        require_confirm=False,
        server_url="http://127.0.0.1:5555",
        namespace="default",
        sandbox_name="package-test",
    )

    # Just test what's already available
    code = """
# Test standard library
import json, os, sys
print('Standard library works!')

# Test what packages are pre-installed
packages = ['requests', 'urllib3', 'certifi', 'chardet']
for pkg in packages:
    try:
        module = __import__(pkg)
        print(f'✓ {pkg} available')
    except ImportError:
        print(f'✗ {pkg} not available')
"""

    result = interpreter.run(code, "python")
    print(result)
    print()


def main():
    """Run example tests."""
    print("Microsandbox Interpreter Examples")
    print("=" * 40)

    test_python_example()
    test_javascript_example()
    test_shell_example()
    test_package_example()

    print("All examples completed!")


if __name__ == "__main__":
    main()


"""
========================================
=== Python Example ===
sum: 15
product: 50
difference: 5

=== JavaScript Example ===
Average age: 30
Users: Alice, Bob, Charlie

=== Shell Example ===
Directory listing: total 4
-rw-r--r-- 1 root root 12 Aug 27 15:04 hello.txt
File content: Hello World

=== Available Packages Test ===
Standard library works!
✓ requests available
✓ urllib3 available
✓ certifi available
✗ chardet not available

All examples completed!

"""
