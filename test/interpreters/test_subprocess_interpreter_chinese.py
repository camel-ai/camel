"""Test subprocess interpreter with Chinese characters and data visualization."""
import os
import tempfile
from pathlib import Path

import pytest

from camel.interpreters import SubprocessInterpreter


@pytest.fixture
def subprocess_interpreter():
    return SubprocessInterpreter(
        require_confirm=False,
        print_stdout=True,
        print_stderr=True,
    )


def test_chinese_data_visualization(subprocess_interpreter):
    """Test executing Python code with Chinese characters and data visualization."""
    # 准备测试代码
    python_code = '''
import pandas as pd
import matplotlib.pyplot as plt

# 数据
data = {
    '指标': ['星标数量', '贡献者数量', '最近活跃度'],
    '数量': [8200, 86, 59]
}

# 创建DataFrame
df = pd.DataFrame(data)

# 临时文件路径
temp_dir = tempfile.gettempdir()
excel_path = os.path.join(temp_dir, 'camel_stats.xlsx')
png_path = os.path.join(temp_dir, 'camel_stats.png')

# 创建Excel表格
df.to_excel(excel_path, index=False)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 生成柱状图
plt.figure(figsize=(10, 6))
plt.bar(df['指标'], df['数量'])
plt.xlabel('指标')
plt.ylabel('数量')
plt.title('CAMEL项目统计数据')
plt.savefig(png_path)
plt.close()  # 关闭图形，避免显示

# 验证文件是否创建成功
print(f"Excel文件路径: {excel_path}")
print(f"Excel文件大小: {os.path.getsize(excel_path)} bytes")
print(f"PNG文件路径: {png_path}")
print(f"PNG文件大小: {os.path.getsize(png_path)} bytes")
'''

    # 运行代码
    result = subprocess_interpreter.run(python_code, "python")
    print(f"执行结果: {result}")

    # 检查输出中是否包含文件信息
    assert "Excel文件路径" in result
    assert "PNG文件路径" in result
    assert "bytes" in result


def test_chinese_file_operations(subprocess_interpreter):
    """Test file operations with Chinese characters."""
    python_code = '''
# 创建一个包含中文的文本文件
with open("测试文件.txt", "w", encoding="utf-8") as f:
    f.write("这是一个测试文件\\n")
    f.write("包含中文字符\\n")
    f.write("测试成功！")

# 读取并打印文件内容
with open("测试文件.txt", "r", encoding="utf-8") as f:
    content = f.read()
print(f"文件内容:\\n{content}")
'''

    # 运行代码
    result = subprocess_interpreter.run(python_code, "python")
    print(f"执行结果: {result}")

    # 检查输出中是否包含中文内容
    assert "这是一个测试文件" in result
    assert "包含中文字符" in result
    assert "测试成功！" in result

    # 清理测试文件
    try:
        os.remove("测试文件.txt")
    except Exception as e:
        print(f"清理文件时出错: {e}")


if __name__ == "__main__":
    # 创建解释器实例
    interpreter = SubprocessInterpreter(
        require_confirm=False,
        print_stdout=True,
        print_stderr=True,
    )
    
    # 运行测试
    print("\n=== 测试1: 数据可视化 ===")
    test_chinese_data_visualization(interpreter)
    
    print("\n=== 测试2: 文件操作 ===")
    test_chinese_file_operations(interpreter)
