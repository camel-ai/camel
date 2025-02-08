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

from typing import Any, Dict, List, Optional, Union

from datasets import Dataset

from camel.interpreters import (
    BaseInterpreter,
    SubprocessInterpreter,
)


class CodeVerifier:
    r"""Verifier for code solutions.

    This verifier checks code solutions by:
    1. Validating syntax
    2. Running test cases
    3. Verifying outputs against expected results
    """

    def __init__(
        self,
        interpreter: str = "subprocess",
        require_confirmation: bool = False,
    ) -> None:
        r"""Initialize the code verifier.

        Args:
            interpreter (str, optional): Type of interpreter to use.
                (default: :obj:`"subprocess"`)
            require_confirmation (bool, optional): Whether to require user
                confirmation before execution. (default: :obj:`False`)
        """
        self.interpreter = self._get_interpreter(
            interpreter, require_confirmation
        )

    def _get_interpreter(
        self,
        interpreter_type: str,
        require_confirmation: bool,
    ) -> BaseInterpreter:
        r"""Initialize appropriate interpreter based on type.

        Args:
            interpreter_type (str): Type of interpreter to use
            require_confirmation (bool): Whether to require confirmation

        Returns:
            BaseInterpreter: Configured interpreter instance

        Raises:
            ValueError: If interpreter type is not supported
        """
        if interpreter_type == "subprocess":
            return SubprocessInterpreter(
                require_confirm=require_confirmation,
                print_stdout=False,
                print_stderr=True,
            )
        raise ValueError(f"Unsupported interpreter type: {interpreter_type}")

    def verify(
        self,
        data: Union[Dataset, Dict[str, Any]],
        criteria: Optional[Dict[str, Any]] = None,
    ) -> Dataset:
        r"""Verify code solutions.

        Args:
            data (Union[Dataset, Dict[str, Any]]): Data containing code to
                verify

            criteria (Optional[Dict[str, Any]], optional): Optional
                verification criteria for this specific call.
                (default: :obj:`None`)

        Returns:
            Dataset: Dataset with verification results added
        """
        if isinstance(data, dict):
            data = Dataset.from_dict(data)

        def verify_single(example: Dict[str, Any]) -> Dict[str, Any]:
            r"""Verify a single code example.

            Args:
                example (Dict[str, Any]): Example containing code to verify

            Returns:
                Dict[str, Any]: Example with verification results added
            """
            code = example.get("code", "")
            language = example.get("language", "python")
            test_cases = example.get("test_cases", [])

            # Check syntax first
            try:
                if language == "python":
                    compile(code, '<string>', 'exec')
            except SyntaxError as e:
                return self._handle_syntax_error(example, e)

            try:
                return self._run_test_cases(
                    example, code, language, test_cases
                )
            except Exception as e:
                return self._handle_execution_error(example, e)

        # For Parallelization
        num_proc = min(4, len(data))

        return data.map(
            verify_single, num_proc=num_proc, desc="Verifying code"
        )

    def _prepare_test_code(
        self,
        code: str,
        test_case: Dict[str, Any],
    ) -> str:
        r"""Prepare code with test case inputs and assertions.

        Args:
            code (str): Original code to test
            test_case (Dict[str, Any]): Test case configuration

        Returns:
            str: Complete test code with assertions
        """
        full_code = [code]

        # Add test case setup
        test_setup = [
            f"{k} = {v!r}" for k, v in test_case.get("inputs", {}).items()
        ]
        if test_setup:
            full_code.extend(test_setup)

        # Add test assertions
        test_assertions = []
        for expr, expected in test_case.get("expected", {}).items():
            test_assertions.append(
                f"""
result = {expr}
if result != {expected!r}:
    raise AssertionError(
        f"Test failed:\\n  Expression: {expr}\\n  "
        f"Expected: {expected!r}\\n  Got: {{result}}"
    )
print(f"Test passed: {{result}}")
"""
            )

        if test_assertions:
            full_code.extend(test_assertions)

        return "\n".join(full_code)

    def _handle_syntax_error(
        self,
        example: Dict[str, Any],
        error: SyntaxError,
    ) -> Dict[str, Any]:
        r"""Handle syntax errors in code verification.

        Args:
            example (Dict[str, Any]): The example being verified
            error (SyntaxError): The syntax error that occurred

        Returns:
            Dict[str, Any]: Updated example with error information
        """
        return {
            **example,
            "verification_result": {
                "passed": False,
                "test_results": [],
                "error": f"Syntax error: {error!s}",
                "details": {
                    "type": "syntax_error",
                    "line": error.lineno,
                    "offset": error.offset,
                    "text": error.text,
                },
            },
        }

    def _handle_execution_error(
        self,
        example: Dict[str, Any],
        error: Exception,
    ) -> Dict[str, Any]:
        r"""Handle execution errors in code verification.

        Args:
            example (Dict[str, Any]): The example being verified
            error (Exception): The execution error that occurred

        Returns:
            Dict[str, Any]: Updated example with error information
        """
        example["verification_result"] = {
            "passed": False,
            "test_results": [],
            "error": str(error),
            "details": {
                "type": "execution_error",
                "message": str(error),
            },
        }
        return example

    def _run_test_cases(
        self,
        example: Dict[str, Any],
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        r"""Run test cases for code verification.

        Args:
            example (Dict[str, Any]): The example being verified
            code (str): The code to test
            language (str): Programming language of the code
            test_cases (List[Dict[str, Any]]): List of test cases to run

        Returns:
            Dict[str, Any]: Updated example with test results
        """
        test_results = []
        test_details = []

        if test_cases:
            for i, test_case in enumerate(test_cases):
                test_code = self._prepare_test_code(code, test_case)
                try:
                    output = self.interpreter.run(test_code, language)
                    test_results.append(True)
                    test_details.append(
                        {
                            "test_case": i + 1,
                            "status": "passed",
                            "output": output,
                        }
                    )
                except Exception as e:
                    test_results.append(False)
                    test_details.append(
                        {
                            "test_case": i + 1,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

        example["verification_result"] = {
            "passed": all(test_results) if test_results else True,
            "test_results": test_results,
            "error": None,
            "details": {
                "test_count": len(test_results),
                "tests": test_details,
            },
        }

        return example
