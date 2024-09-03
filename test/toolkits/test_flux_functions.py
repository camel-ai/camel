import base64
import os

import pytest
from PIL import Image

from camel.toolkits import OpenAIFunction
from camel.toolkits.flux_toolkit import FluxToolkit


@pytest.fixture
def flux_toolkit():
    return FluxToolkit()


@pytest.fixture
def test_image_path():
    # 准备测试图像的路径
    test_image_path = 'test_image.png'
    # 创建一个测试图像文件（或者确保该文件存在用于测试）
    with open(test_image_path, 'wb') as f:
        f.write(b'This is a test image placeholder content.')

    # 提供该路径用于测试
    yield test_image_path

    # 测试结束后清理临时文件
    try:
        os.remove(test_image_path)
    except OSError as e:
        print(f"Error: {e.strerror}")


def test_image_to_base64_valid(flux_toolkit, test_image_path):
    # 打开测试图像
    with Image.open(test_image_path) as img:
        # 将图像转换为Base64编码字符串
        base64_encoded_string = flux_toolkit.image_to_base64(img)

    # 将Base64字符串解码为二进制数据以进行验证
    decoded_binary_data = base64.b64decode(base64_encoded_string)
    # 验证解码后的数据与原始图像的二进制内容是否一致
    with open(test_image_path, 'rb') as f:
        original_binary_data = f.read()

    assert (
        decoded_binary_data == original_binary_data
    ), "Base64编码的字符串与原始图像内容不匹配"


def test_image_to_base64_with_invalid_input(flux_toolkit):
    # 有意传递非图像对象来模拟错误情况
    invalid_input = "This is not an image"

    # 期望函数在编码时发生错误时返回空字符串
    result = flux_toolkit.image_to_base64(invalid_input)

    # 断言函数正确地为无效输入返回空字符串
    assert result == "", "对于无效输入，函数应该返回空字符串"


def test_generate_flux_img(flux_toolkit):
    prompt = "A cat holding a sign that says hello world"
    # 调用生成图像的方法
    image_path = flux_toolkit.generate_flux_img(prompt)

    # 验证生成的图像文件是否存在
    assert os.path.exists(image_path), "生成的图像文件未能保存"

    # 验证图像文件是否为PNG格式
    assert image_path.endswith('.png'), "生成的图像文件应为PNG格式"

    # 测试结束后删除生成的图像文件
    try:
        os.remove(image_path)
    except OSError as e:
        print(f"Error: {e.strerror}")
