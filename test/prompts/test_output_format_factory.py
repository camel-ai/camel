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

import pytest

from camel.prompts.output_format.base import (
    OutputFormat,
    OutputFormatHandler,
    ExtractionResult,
)
from camel.prompts.output_format.handler_factory import (
    OutputFormatHandlerFactory,
)
from camel.prompts.output_format.handlers import (
    DefaultOutputFormatHandler,
    JsonOutputFormatHandler,
)
from camel.types.enums import OutputFormatType, OutputExtractionErrorType


def test_default_handlers():
    """测试工厂的默认处理器"""
    # 测试创建JSON处理器
    json_format = OutputFormat(OutputFormatType.JSON)
    handler = OutputFormatHandlerFactory.create(json_format)
    assert isinstance(handler, JsonOutputFormatHandler)
    
    # 测试创建文本处理器
    text_format = OutputFormat(OutputFormatType.TEXT)
    handler = OutputFormatHandlerFactory.create(text_format)
    assert isinstance(handler, DefaultOutputFormatHandler)
    
    # 测试无格式时的默认处理器
    handler = OutputFormatHandlerFactory.create()
    assert isinstance(handler, DefaultOutputFormatHandler)


def test_case_insensitive_format_type():
    """测试格式类型的大小写不敏感性"""
    # 小写格式类型
    json_format = OutputFormat("json")
    handler = OutputFormatHandlerFactory.create(json_format)
    assert isinstance(handler, JsonOutputFormatHandler)
    
    # 混合大小写格式类型
    json_format = OutputFormat("JsOn")
    handler = OutputFormatHandlerFactory.create(json_format)
    assert isinstance(handler, JsonOutputFormatHandler)


def test_unknown_format_type():
    """测试未知格式类型"""
    # 未知格式类型应该返回默认处理器
    unknown_format = OutputFormat("UNKNOWN_TYPE")
    handler = OutputFormatHandlerFactory.create(unknown_format)
    assert isinstance(handler, DefaultOutputFormatHandler)


def test_register_custom_handler():
    """测试注册自定义处理器"""
    # 创建一个自定义格式处理器
    class CustomOutputFormatHandler(OutputFormatHandler):
        def _setup_extractors(self) -> None:
            pass
            
        def _setup_validators(self) -> None:
            pass
            
        def extract_data(self, text: str, validate: bool = True) -> ExtractionResult:
            return ExtractionResult(data=f"CUSTOM: {text}", is_success=True)
    
    # 注册自定义处理器
    OutputFormatHandlerFactory.register_handler("CUSTOM", CustomOutputFormatHandler)
    
    # 测试创建自定义处理器
    custom_format = OutputFormat("CUSTOM")
    handler = OutputFormatHandlerFactory.create(custom_format)
    assert isinstance(handler, CustomOutputFormatHandler)
    
    # 验证自定义处理器功能
    result = handler.extract_data("Test")
    assert result.is_success
    assert result.data == "CUSTOM: Test"
    
    # 测试大小写不敏感性
    custom_format = OutputFormat("custom")
    handler = OutputFormatHandlerFactory.create(custom_format)
    assert isinstance(handler, CustomOutputFormatHandler)


def test_register_handler_with_enum():
    """测试使用枚举注册处理器"""
    # 创建一个简单的自定义处理器
    class SimpleHandler(OutputFormatHandler):
        def _setup_extractors(self) -> None:
            pass
            
        def _setup_validators(self) -> None:
            pass
            
        def extract_data(self, text: str, validate: bool = True) -> ExtractionResult:
            return ExtractionResult(data=f"SIMPLE: {text}", is_success=True)
    
    # 使用枚举注册
    OutputFormatHandlerFactory.register_handler(OutputFormatType.YAML, SimpleHandler)
    
    # 测试创建
    yaml_format = OutputFormat(OutputFormatType.YAML)
    handler = OutputFormatHandlerFactory.create(yaml_format)
    assert isinstance(handler, SimpleHandler)
    
    # 测试字符串形式
    yaml_format = OutputFormat("YAML")
    handler = OutputFormatHandlerFactory.create(yaml_format)
    assert isinstance(handler, SimpleHandler)


def test_factory_additional_parameters():
    """测试工厂中传递额外参数"""
    # 创建JSON处理器并传入required_keys参数
    json_format = OutputFormat(OutputFormatType.JSON)
    handler = OutputFormatHandlerFactory.create(
        json_format, 
        required_keys={"name", "age"}
    )
    
    # 验证处理器是否正确处理了参数
    valid_json = '{"name": "John", "age": 30}'
    result = handler.extract_data(valid_json)
    assert result.is_success
    
    # 缺少必要字段时应该验证失败
    invalid_json = '{"name": "John"}'
    result = handler.extract_data(invalid_json)
    assert not result.is_success 