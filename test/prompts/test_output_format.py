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

import json
import pytest

from camel.prompts.output_format.base import (
    OutputFormat,
    ExtractionResult,
)
from camel.prompts.output_format.prompts import (
    OutputFormatPrompt,
    JsonOutputFormatPrompt,
)
from camel.prompts.output_format.extractors import (
    JsonDirectExtractor,
    JsonCodeBlockExtractor,
)
from camel.prompts.output_format.validators import (
    JsonRequiredKeysValidator,
)
from camel.prompts.output_format.handlers import (
    JsonOutputFormatHandler,
    DefaultOutputFormatHandler,
)
from camel.prompts.output_format.handler_factory import (
    OutputFormatHandlerFactory,
)
from camel.types.enums import OutputFormatType, OutputExtractionErrorType


def test_output_format_initialization():
    """测试OutputFormat类的初始化和属性"""
    # 测试使用字符串初始化
    fmt = OutputFormat("json", "test spec")
    assert fmt.output_format_type == "json"
    assert fmt.output_format_spec == "test spec"
    
    # 测试使用枚举初始化
    fmt = OutputFormat(OutputFormatType.JSON, "test spec")
    assert fmt.output_format_type == "JSON"
    assert fmt.output_format_spec == "test spec"
    
    # 测试属性设置
    fmt.output_format_type = "xml"
    assert fmt.output_format_type == "xml"
    fmt.output_format_spec = "new spec"
    assert fmt.output_format_spec == "new spec"


def test_output_format_prompt_initialization():
    """测试OutputFormatPrompt类的初始化"""
    # 不带格式初始化
    prompt = OutputFormatPrompt("This is a test prompt with {param}")
    assert prompt.output_format.output_format_type is None
    assert prompt.output_format.output_format_spec is None
    assert prompt.key_words == {"param"}
    
    # 带格式初始化
    output_format = OutputFormat(OutputFormatType.JSON, "test spec")
    prompt = OutputFormatPrompt("This is a test prompt", output_format=output_format)
    assert prompt.output_format.output_format_type == "JSON"
    assert prompt.output_format.output_format_spec == "test spec"


def test_output_format_prompt_format():
    """测试OutputFormatPrompt的format方法"""
    prompt = OutputFormatPrompt("Name: {name}, Age: {age}")
    
    # 基本格式化
    formatted = prompt.format(name="John", age=30)
    assert formatted == "Name: John, Age: 30"
    assert isinstance(formatted, OutputFormatPrompt)
    
    # 带新格式的格式化
    new_format = OutputFormat(OutputFormatType.JSON, '{"name": "string", "age": "number"}')
    formatted = prompt.format(name="John", age=30, output_format=new_format)
    assert formatted != 'Name: John, Age: 30'
    assert formatted.output_format.output_format_type == "JSON"
    assert formatted.output_format.output_format_spec == '{"name": "string", "age": "number"}'


def test_json_output_format_prompt():
    """测试JsonOutputFormatPrompt类"""
    # 基本初始化
    prompt = JsonOutputFormatPrompt("Return user data")
    assert prompt.output_format.output_format_type == "JSON"
    assert prompt.output_format.output_format_spec is None
    
    # 带schema初始化
    schema = '{"name": "string", "age": "number"}'
    prompt = JsonOutputFormatPrompt("Return user data", output_format_spec=schema)
    assert prompt.output_format.output_format_type == "JSON"
    assert prompt.output_format.output_format_spec == schema
    
    # 格式化并覆盖schema
    new_schema = '{"email": "string", "address": "string"}'
    formatted = prompt.format(output_format_spec=new_schema)
    assert formatted.output_format.output_format_type == "JSON"
    assert formatted.output_format.output_format_spec == new_schema


def test_json_extractors():
    """测试JSON提取器"""
    # 直接JSON提取器
    direct_extractor = JsonDirectExtractor()
    
    # 成功提取
    valid_json = '{"name": "John", "age": 30}'
    result = direct_extractor.extract(valid_json, None)
    assert result.is_success
    assert result.data == {"name": "John", "age": 30}
    
    # 失败提取 - 无效JSON
    invalid_json = '{"name": "John", "age": 30'
    result = direct_extractor.extract(invalid_json, None)
    assert not result.is_success
    assert "JSON parsing error" in result.error_messages[0]
    
    # JSON代码块提取器
    code_block_extractor = JsonCodeBlockExtractor()
    
    # 从代码块中提取
    json_code_block = '```json\n{"name": "John", "age": 30}\n```'
    output_format = OutputFormat(OutputFormatType.JSON)
    result = code_block_extractor.extract(json_code_block, output_format)
    assert result.is_success
    assert result.data == {"name": "John", "age": 30}


def test_json_validator():
    """测试JSON验证器"""
    # 创建验证器
    validator = JsonRequiredKeysValidator(required_keys={"name", "age"})
    
    # 验证成功
    valid_data = {"name": "John", "age": 30, "email": "john@example.com"}
    result = validator.validate(valid_data)
    assert result.is_success
    assert result.data == valid_data
    
    # 验证失败 - 缺少必要字段
    invalid_data = {"name": "John", "email": "john@example.com"}
    result = validator.validate(invalid_data)
    assert not result.is_success
    assert "Missing required keys" in result.error_messages[0]
    assert result.error_type == OutputExtractionErrorType.VALIDATION


def test_output_format_handlers():
    """测试输出格式处理器"""
    # 默认处理器
    default_handler = DefaultOutputFormatHandler()
    result = default_handler.extract_data("Simple text")
    assert result.is_success
    assert result.data == "Simple text"
    
    # JSON处理器
    json_handler = JsonOutputFormatHandler(required_keys={"name"})
    
    # 成功提取和验证
    valid_json = '{"name": "John", "age": 30}'
    result = json_handler.extract_data(valid_json)
    assert result.is_success
    assert result.data == {"name": "John", "age": 30}
    
    # 失败验证 - 缺少必要字段
    invalid_json = '{"age": 30}'
    result = json_handler.extract_data(invalid_json)
    assert not result.is_success


def test_output_format_factory():
    """测试OutputFormatHandlerFactory"""
    # 创建JSON处理器
    json_format = OutputFormat(OutputFormatType.JSON)
    handler = OutputFormatHandlerFactory.create(json_format)
    assert isinstance(handler, JsonOutputFormatHandler)
    
    # 创建默认处理器
    text_format = OutputFormat(OutputFormatType.TEXT)
    handler = OutputFormatHandlerFactory.create(text_format)
    assert isinstance(handler, DefaultOutputFormatHandler)
    
    # 创建未知类型的处理器(应该返回默认处理器)
    unknown_format = OutputFormat("UNKNOWN")
    handler = OutputFormatHandlerFactory.create(unknown_format)
    assert isinstance(handler, DefaultOutputFormatHandler)


def test_handle_output_format():
    """测试处理输出格式"""
    # 创建JSON提示并提取数据
    prompt = JsonOutputFormatPrompt("Return data", output_format_spec='{"name": "string"}')
    json_text = '{"name": "John", "age": 30}'
    
    # 使用提示处理输出
    result = prompt.handle_output_format(json_text)
    assert isinstance(result, dict)
    assert result["name"] == "John"
    assert result["age"] == 30
    
    # 使用无效JSON测试
    invalid_json = '{"name": "John", "age":'
    with pytest.raises(Exception):
        prompt.handle_output_format(invalid_json) 