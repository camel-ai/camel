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
import datetime
import decimal
import enum
import threading
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import Mock

from pydantic import BaseModel

from camel.utils.mcp import _is_pydantic_serializable, _validate_function_types


class PydanticTestModel(BaseModel):
    name: str
    age: int


class SampleEnum(enum.Enum):
    OPTION_A = "a"
    OPTION_B = "b"


class SampleIntEnum(enum.IntEnum):
    ONE = 1
    TWO = 2


class TestIsPydanticSerializable:
    def test_basic_types_are_serializable(self):
        basic_types = [int, float, str, bool, bytes, type(None)]

        for basic_type in basic_types:
            is_serializable, error_msg = _is_pydantic_serializable(basic_type)
            assert is_serializable, f"{basic_type} should be serializable"
            assert error_msg == ""

    def test_none_type_is_serializable(self):
        is_serializable, error_msg = _is_pydantic_serializable(type(None))
        assert is_serializable
        assert error_msg == ""

    def test_datetime_types_are_serializable(self):
        datetime_types = [
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
        ]

        for datetime_type in datetime_types:
            is_serializable, error_msg = _is_pydantic_serializable(
                datetime_type
            )
            assert is_serializable, f"{datetime_type} should be serializable"
            assert error_msg == ""

    def test_decimal_type_is_serializable(self):
        is_serializable, error_msg = _is_pydantic_serializable(decimal.Decimal)
        assert is_serializable
        assert error_msg == ""

    def test_uuid_type_is_serializable(self):
        is_serializable, error_msg = _is_pydantic_serializable(uuid.UUID)
        assert is_serializable
        assert error_msg == ""

    def test_enum_types_are_serializable(self):
        enum_types = [
            SampleEnum,
            SampleIntEnum,
            enum.Enum,
            enum.IntEnum,
        ]

        for enum_type in enum_types:
            is_serializable, error_msg = _is_pydantic_serializable(enum_type)
            assert is_serializable, f"{enum_type} should be serializable"
            assert error_msg == ""

    def test_list_types_are_serializable(self):
        list_types = [
            List[str],
            List[int],
            List[float],
            List[bool],
            List[Dict[str, int]],
        ]

        for list_type in list_types:
            is_serializable, error_msg = _is_pydantic_serializable(list_type)
            assert is_serializable, f"{list_type} should be serializable"
            assert error_msg == ""

    def test_dict_types_are_serializable(self):
        dict_types = [
            Dict[str, int],
            Dict[str, str],
            Dict[str, Any],
            Dict[str, List[int]],
        ]

        for dict_type in dict_types:
            is_serializable, error_msg = _is_pydantic_serializable(dict_type)
            assert is_serializable, f"{dict_type} should be serializable"
            assert error_msg == ""

    def test_tuple_types_are_serializable(self):
        tuple_types = [
            Tuple[str, int],
            Tuple[int, str, bool],
        ]

        for tuple_type in tuple_types:
            is_serializable, error_msg = _is_pydantic_serializable(tuple_type)
            assert is_serializable, f"{tuple_type} should be serializable"
            assert error_msg == ""

    def test_variable_length_tuple_handling(self):
        # Variable length tuples might not be fully supported by all
        # Pydantic versions. This is a separate test to check the behavior
        is_serializable, error_msg = _is_pydantic_serializable(Tuple[str, ...])
        # We don't assert True here as this might fail depending on
        # Pydantic version. This test documents the behavior
        if not is_serializable:
            assert "not Pydantic serializable" in error_msg

    def test_set_types_are_serializable(self):
        set_types = [
            Set[str],
            Set[int],
        ]

        for set_type in set_types:
            is_serializable, error_msg = _is_pydantic_serializable(set_type)
            assert is_serializable, f"{set_type} should be serializable"
            assert error_msg == ""

    def test_optional_types_are_serializable(self):
        optional_types = [
            Optional[str],
            Optional[int],
            Optional[Dict[str, int]],
            Optional[List[str]],
        ]

        for optional_type in optional_types:
            is_serializable, error_msg = _is_pydantic_serializable(
                optional_type
            )
            assert is_serializable, f"{optional_type} should be serializable"
            assert error_msg == ""

    def test_union_types_are_serializable(self):
        union_types = [
            Union[str, int],
            Union[str, None],
            Union[int, float, str],
        ]

        for union_type in union_types:
            is_serializable, error_msg = _is_pydantic_serializable(union_type)
            assert is_serializable, f"{union_type} should be serializable"
            assert error_msg == ""

    def test_pydantic_models_are_serializable(self):
        is_serializable, error_msg = _is_pydantic_serializable(
            PydanticTestModel
        )
        assert is_serializable
        assert error_msg == ""

    def test_non_serializable_types(self):
        non_serializable_types = [
            threading.Lock,
            Mock,
            threading.Thread,
        ]

        for non_serializable_type in non_serializable_types:
            is_serializable, error_msg = _is_pydantic_serializable(
                non_serializable_type
            )
            assert (
                not is_serializable
            ), f"{non_serializable_type} should not be serializable"
            assert error_msg != ""
            assert "not Pydantic serializable" in error_msg

    def test_union_with_non_serializable_type(self):
        is_serializable, error_msg = _is_pydantic_serializable(
            Union[str, threading.Lock]
        )
        assert not is_serializable
        assert "not Pydantic serializable" in error_msg

    def test_list_with_non_serializable_type(self):
        is_serializable, error_msg = _is_pydantic_serializable(
            List[threading.Lock]
        )
        assert not is_serializable
        assert "not Pydantic serializable" in error_msg

    def test_dict_with_non_serializable_value_type(self):
        is_serializable, error_msg = _is_pydantic_serializable(
            Dict[str, threading.Lock]
        )
        assert not is_serializable
        assert "not Pydantic serializable" in error_msg

    def test_dict_with_non_serializable_key_type(self):
        is_serializable, error_msg = _is_pydantic_serializable(
            Dict[threading.Lock, str]
        )
        assert not is_serializable
        assert "not Pydantic serializable" in error_msg

    def test_nested_generic_types(self):
        nested_types = [
            List[Dict[str, int]],
            Dict[str, List[int]],
            Optional[List[Dict[str, Union[int, str]]]],
        ]

        for nested_type in nested_types:
            is_serializable, error_msg = _is_pydantic_serializable(nested_type)
            assert is_serializable, f"{nested_type} should be serializable"
            assert error_msg == ""

    def test_generic_types_with_pydantic_supported_types(self):
        pydantic_generic_types = [
            List[datetime.datetime],
            Dict[str, decimal.Decimal],
            Optional[uuid.UUID],
            Union[datetime.date, datetime.time],
            List[SampleEnum],
            Dict[str, SampleIntEnum],
        ]

        for generic_type in pydantic_generic_types:
            is_serializable, error_msg = _is_pydantic_serializable(
                generic_type
            )
            assert is_serializable, f"{generic_type} should be serializable"
            assert error_msg == ""

    def test_any_type_is_serializable(self):
        is_serializable, error_msg = _is_pydantic_serializable(Any)
        assert is_serializable
        assert error_msg == ""


class TestValidateFunctionTypes:
    def test_function_with_basic_types(self):
        def simple_func(name: str, age: int) -> str:
            return f"{name} is {age} years old"

        errors = _validate_function_types(simple_func)
        assert errors == []

    def test_function_with_no_annotations(self):
        def no_annotations_func(name, age):
            return f"{name} is {age} years old"

        errors = _validate_function_types(no_annotations_func)
        assert errors == []

    def test_function_with_any_types(self):
        def any_types_func(data: Any) -> Any:
            return data

        errors = _validate_function_types(any_types_func)
        assert errors == []

    def test_function_with_serializable_complex_types(self):
        def complex_func(
            data: Dict[str, List[int]], optional_name: Optional[str] = None
        ) -> List[str]:
            return []

        errors = _validate_function_types(complex_func)
        assert errors == []

    def test_function_with_non_serializable_parameter(self):
        def non_serializable_param_func(lock: threading.Lock) -> str:
            return "test"

        errors = _validate_function_types(non_serializable_param_func)
        assert len(errors) == 1
        assert "Parameter 'lock'" in errors[0]
        assert "not Pydantic serializable" in errors[0]

    def test_function_with_non_serializable_return_type(self):
        def non_serializable_return_func(name: str) -> threading.Lock:
            return threading.Lock()

        errors = _validate_function_types(non_serializable_return_func)
        assert len(errors) == 1
        assert "Return type" in errors[0]
        assert "not Pydantic serializable" in errors[0]

    def test_function_with_multiple_errors(self):
        def multiple_errors_func(
            lock: threading.Lock, thread: threading.Thread
        ) -> Mock:
            return Mock()

        errors = _validate_function_types(multiple_errors_func)
        assert len(errors) == 3  # 2 parameters + 1 return type

        param_errors = [e for e in errors if "Parameter" in e]
        assert len(param_errors) == 2

        return_errors = [e for e in errors if "Return type" in e]
        assert len(return_errors) == 1

    def test_function_with_self_parameter(self):
        class TestClass:
            def method_with_self(self, name: str) -> str:
                return name

        instance = TestClass()
        errors = _validate_function_types(instance.method_with_self)
        assert errors == []

    def test_function_with_pydantic_model_types(self):
        def pydantic_func(model: PydanticTestModel) -> PydanticTestModel:
            return model

        errors = _validate_function_types(pydantic_func)
        assert errors == []

    def test_function_with_union_types(self):
        def union_func(value: Union[str, int]) -> Optional[str]:
            return str(value) if value is not None else None

        errors = _validate_function_types(union_func)
        assert errors == []

    def test_function_with_datetime_types(self):
        def datetime_func(
            dt: datetime.datetime,
            date: datetime.date,
            time: datetime.time,
            delta: datetime.timedelta,
        ) -> datetime.datetime:
            return dt

        errors = _validate_function_types(datetime_func)
        assert errors == []

    def test_function_with_decimal_and_uuid_types(self):
        def decimal_uuid_func(
            amount: decimal.Decimal,
            identifier: uuid.UUID,
        ) -> Optional[decimal.Decimal]:
            return amount

        errors = _validate_function_types(decimal_uuid_func)
        assert errors == []

    def test_function_with_enum_types(self):
        def enum_func(
            option: SampleEnum,
            number: SampleIntEnum,
        ) -> Union[SampleEnum, SampleIntEnum]:
            return option

        errors = _validate_function_types(enum_func)
        assert errors == []

    def test_function_with_nested_non_serializable_types(self):
        def nested_non_serializable_func(
            data: List[threading.Lock],
        ) -> Dict[str, Mock]:
            return {}

        errors = _validate_function_types(nested_non_serializable_func)
        assert len(errors) == 2  # parameter and return type
        assert any("Parameter 'data'" in error for error in errors)
        assert any("Return type" in error for error in errors)

    def test_function_with_missing_type_hints(self):
        # Using a string annotation that doesn't exist to simulate
        # missing type hint resolution
        def func_with_undefined_type(value) -> str:
            return str(value)

        # Manually add a problematic annotation to trigger the NameError path
        func_with_undefined_type.__annotations__ = {"value": "UndefinedType"}

        errors = _validate_function_types(func_with_undefined_type)
        # Should not raise an error, just log warning and return empty list
        assert errors == []
