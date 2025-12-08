import unittest
from typing import Any, List, Dict, Optional, Union
from camel.utils.mcp_client import MCPClient


class TestMCPTypeBuilder(unittest.TestCase):

    def setUp(self):
        """每个测试前都会运行，初始化转换器实例"""
        self.client = MCPClient({"url": "https://example.com"})

    def test_basic_primitive_types(self):
        client = MCPClient({"url": "https://example.com"})
        cases = [
            ("string", str),
            ("integer", int),
            ("number", float),
            ("boolean", bool),
            ("array", list),
            ("object", dict),
        ]
        for input_type, expected in cases:
            with self.subTest(input_type=input_type):
                result = self.client._build_function_param_type(input_type)
                self.assertEqual(result, expected)

    def test_unknown_type_fallback(self):
        result = self.client._build_function_param_type("unknown_alien_type")
        self.assertEqual(result, Any)

    def test_optional_types(self):
        # ["string", "null"] -> Optional[str]
        result = self.client._build_function_param_type(["string", "null"])
        self.assertEqual(result, Optional[str])

    def test_union_types(self):
        # ["string", "integer"] -> Union[str, int]
        result = self.client._build_function_param_type(["string", "integer"])
        # NOTE：Union[str, int] is eq Union[int, str]
        self.assertEqual(result, Union[str, int])

    def test_complex_union_optional(self):
        # ["string", "integer", "null"] -> Optional[Union[str, int]]
        result = self.client._build_function_param_type(["string", "integer", "null"])
        self.assertEqual(result, Optional[Union[str, int]])

    def test_edge_cases(self):
        # Empty list -> Any
        self.assertEqual(self.client._build_function_param_type([]), Any)
        # Only null in list -> Any
        self.assertEqual(self.client._build_function_param_type(["null"]), Any)
        # include unknow type > Union[str, Any]
        result = self.client._build_function_param_type(["string", "unknown"])
        self.assertEqual(result, Union[str, Any])
        # illegal input -> Any
        self.assertEqual(self.client._build_function_param_type(123), Any)

if __name__ == "__main__":
    unittest.main()
