# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import ast
import difflib
from typing import Any, Callable, Dict, List, Mapping, Union


class InterpreterError(ValueError):
    """
    An error raised when the interpreter cannot evaluate a Python expression,
    due to syntax error or unsupported operations.
    """

    pass


class PythonInterpreter():
    r"""

    """

    def __init__(self, action_space: List[str], state: Dict[str, Any],
                 package_white_list: List[str] = []) -> None:
        self.action_space = action_space
        self.state = state
        self.package_white_list = package_white_list

    def execute(self, code: str):
        try:
            expression = ast.parse(code)
        except SyntaxError as e:
            print("Syntax error in generated code", e)
            return

        self._execute_ast(expression)

    def _execute_ast(self, expression: ast.AST):
        if isinstance(expression, ast.Assign):
            # Assignement -> we self._execute the assignement which should
            # update the state. We return the variable assigned as it may
            # be used to determine the final result.
            return self._execute_assign(expression)
        elif isinstance(expression, ast.Call):
            # Function call -> we return the value of the function call
            return self._execute_call(expression)
        elif isinstance(expression, ast.Constant):
            # Constant -> just return the value
            return expression.value
        elif isinstance(expression, ast.Dict):
            # Dict -> self._execute all keys and values
            keys = [self._execute_ast(k) for k in expression.keys]
            values = [self._execute_ast(v) for v in expression.values]
            return dict(zip(keys, values))
        elif isinstance(expression, ast.Expr):
            # Expression -> self._execute the content
            return self._execute_ast(expression.value)
        elif isinstance(expression, ast.FormattedValue):
            # Formatted value (part of f-string) -> self._execute the content
            # and return
            return self._execute_ast(expression.value)
        elif isinstance(expression, ast.If):
            # If -> execute the right branch
            return self._execute_if(expression)
        elif hasattr(ast, "Index") and isinstance(expression, ast.Index):
            return self._execute_ast(expression.value)
        elif isinstance(expression, ast.JoinedStr):
            return "".join(
                [str(self._execute_ast(v)) for v in expression.values])
        elif isinstance(expression, ast.List):
            # List -> self._execute all elements
            return [self._execute_ast(elt) for elt in expression.elts]
        elif isinstance(expression, ast.Name):
            # Name -> pick up the value in the state
            return self._execute_name(expression)
        elif isinstance(expression, ast.Subscript):
            # Subscript -> return the value of the indexing
            return self._execute_subscript(expression)
        else:
            # For now we refuse anything else. Let's add things as we need
            # them.
            raise InterpreterError(
                f"{expression.__class__.__name__} is not supported.")

    def _execute_assign(self, assign: ast.Assign) -> Any:
        var_names = assign.targets
        result = self._execute_ast(assign.value)

        for var_name in var_names:
            if isinstance(var_name, ast.Name):
                self.state[var_name.id] = result
            elif isinstance(var_name, ast.Tuple):
                if len(result) != len(var_name):
                    raise InterpreterError(
                        f"Expected {len(var_name)} values but got"
                        f"{len(result)}.")
                for v, r in zip(var_name.ctx, result):
                    self.state[v.id] = r
            else:
                raise InterpreterError(f"Unsupport variable type. Expected"
                                       f"ast.Name or ast.Tuple, got"
                                       f"{type(var_name)} instead.")
        return result

    def _execute_call(self, call: ast.Call) -> Any:
        callable_func = self._get_func_from_action_space(call.func)

        # Todo deal with args
        args = [self._execute_ast(arg) for arg in call.args]
        kwargs = {
            keyword.arg: self._execute_ast(keyword.value)
            for keyword in call.keywords
        }
        return callable_func(*args, **kwargs)

    def _get_func_from_action_space(
            self, func: Union[ast.Attribute, ast.Name]) -> Callable:

        if not isinstance(func, (ast.Attribute, ast.Name)):
            raise InterpreterError(
                f"It is not permitted to invoke functions than the action "
                f"space (tried to execute {func} of type {type(func)}.")

        access_list = []
        while not isinstance(func, ast.Name):
            access_list = [func.attr] + access_list
            func = func.value
        access_list = [func.id] + access_list

        found_func = None
        func_name = access_list[0]
        if func_name in self.action_space:
            found_func = self.action_space[func_name]
        for name in access_list[1:]:
            if found_func:
                try:
                    found_func = getattr(found_func, name)
                except AttributeError as e:
                    raise InterpreterError(
                        f"AttributeError in generated code ({e}).")
            else:
                func_name += f".{name}"
                if func_name in self.action_space:
                    found_func = self.action_space[func_name]

        if not found_func:
            raise InterpreterError(
                f"It is not permitted to invoke functions than the action"
                f"space (tried to execute {func}).")

        return func

    def _execute_subscript(self, subscript):
        index = self._execute_ast(subscript.slice)
        value = self._execute_ast(subscript.value)
        if isinstance(value, (list, tuple)):
            return value[int(index)]
        if index in value:
            return value[index]
        if isinstance(index, str) and isinstance(value, Mapping):
            close_matches = difflib.get_close_matches(index,
                                                      list(value.keys()))
            if len(close_matches) > 0:
                return value[close_matches[0]]

        raise InterpreterError(f"Could not index {value} with '{index}'.")

    def _execute_name(self, name: ast.Name):
        state = []
        if name.id in state:
            return state[name.id]
        close_matches = difflib.get_close_matches(name.id, list(state.keys()))
        if len(close_matches) > 0:
            return state[close_matches[0]]
        raise InterpreterError(f"The variable `{name.id}` is not defined.")

    def _execute_condition(self, condition):
        if len(condition.ops) > 1:
            raise InterpreterError(
                "Cannot evaluate conditions with multiple operators")

        left = self._execute_ast(condition.left)
        comparator = condition.ops[0]
        right = self._execute_ast(condition.comparators[0])

        if isinstance(comparator, ast.Eq):
            return left == right
        elif isinstance(comparator, ast.NotEq):
            return left != right
        elif isinstance(comparator, ast.Lt):
            return left < right
        elif isinstance(comparator, ast.LtE):
            return left <= right
        elif isinstance(comparator, ast.Gt):
            return left > right
        elif isinstance(comparator, ast.GtE):
            return left >= right
        elif isinstance(comparator, ast.Is):
            return left is right
        elif isinstance(comparator, ast.IsNot):
            return left is not right
        elif isinstance(comparator, ast.In):
            return left in right
        elif isinstance(comparator, ast.NotIn):
            return left not in right
        else:
            raise InterpreterError(f"Operator not supported: {comparator}")

    def _execute_if(self, if_statement):
        result = None
        if self._execute_condition(if_statement.test):
            for line in if_statement.body:
                line_result = self._execute_ast(line)
                if line_result is not None:
                    result = line_result
        else:
            for line in if_statement.orelse:
                line_result = self._execute_ast(line)
                if line_result is not None:
                    result = line_result
        return result
